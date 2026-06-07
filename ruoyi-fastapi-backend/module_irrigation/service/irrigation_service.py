import asyncio
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any

import joblib
import numpy as np
import rasterio
import torch

from config.env import IrrigationConfig
from exceptions.exception import ServiceException
from module_irrigation.model.irrigation_models import LSTMModel, SACActor


class IrrigationService:
    """灌溉决策服务：封装 LSTM 代理模型 + SAC 强化学习模型推理逻辑"""

    ROLL_HORIZON = 15
    SM_THRESHOLD = 0.30  # 阈值调高，减少触发频率
    HIST_LEN = 15
    MIN_IRRIGATION_INTERVAL = 4  # 间隔拉长至 5 天，15 天约 2-3 次灌溉
    IRRIGATION_LOW = 2.0
    IRRIGATION_HIGH = 4.0
    NOISE_SCALE = 0.15
    RL_POLICY_DATA_FILENAME = 'policy.pth'
    SM_BIAS = -0.04  # LSTM 预测系统性偏高约 0.04，校正使 sm 落在合理区间

    # 模型单例（由 load_models_inference_mode 调用时填充）
    _proxy: LSTMModel | None = None
    _rl_policy: SACActor | None = None
    _scaler_x: Any | None = None
    _scaler_y: Any | None = None
    _device: torch.device | None = None
    _x_mean: torch.Tensor | None = None
    _x_scale: torch.Tensor | None = None
    _y_mean: torch.Tensor | None = None
    _y_scale: torch.Tensor | None = None

    @classmethod
    def load_models_inference_mode(cls) -> None:
        """
        在服务启动时调用，加载 LSTM 和 RL 模型到 CPU，
        全局仅加载一次，结果保存在类属性中。
        """
        if cls._proxy is not None:
            return

        model_dir = IrrigationConfig.irrigation_model_dir
        rl_path = IrrigationConfig.irrigation_rl_model_path
        device = torch.device(IrrigationConfig.irrigation_device)
        cls._device = device

        # LSTM 代理模型
        proxy = LSTMModel().to(device)
        proxy.load_state_dict(torch.load(os.path.join(model_dir, 'model.pth'), map_location=device))
        proxy.eval()
        cls._proxy = proxy

        # Scaler
        scaler_x = joblib.load(os.path.join(model_dir, 'scaler_x.pkl'))
        scaler_y = joblib.load(os.path.join(model_dir, 'scaler_y.pkl'))
        if np.any(scaler_x.scale_ == 0):
            scaler_x.scale_[scaler_x.scale_ == 0] = 1e-8
        if np.any(scaler_y.scale_ == 0):
            scaler_y.scale_[scaler_y.scale_ == 0] = 1e-8
        cls._scaler_x = scaler_x
        cls._scaler_y = scaler_y

        cls._x_mean = torch.tensor(scaler_x.mean_, dtype=torch.float32, device=device)
        cls._x_scale = torch.tensor(scaler_x.scale_, dtype=torch.float32, device=device)
        cls._y_mean = torch.tensor(scaler_y.mean_, dtype=torch.float32, device=device)
        cls._y_scale = torch.tensor(scaler_y.scale_, dtype=torch.float32, device=device)

        # SAC Actor
        policy_state_dict = torch.load(
            os.path.join(rl_path, cls.RL_POLICY_DATA_FILENAME),
            map_location=device,
        )

        actor_state_dict = {}
        for key, value in policy_state_dict.items():
            if key.startswith('actor.'):
                actor_state_dict[key[6:]] = value

        rl_policy = SACActor().to(device)
        rl_policy.load_state_dict(actor_state_dict)
        rl_policy.eval()
        cls._rl_policy = rl_policy

    @classmethod
    async def run_prediction(cls, **kwargs) -> tuple[str, str]:
        """
        异步入口：将同步推理运行在线程池中，不阻塞 FastAPI 事件循环。
        """
        return await asyncio.to_thread(cls.predict_irrigation, **kwargs)

    @classmethod
    def predict_irrigation(
        cls,
        uploaded_files: dict[str, list[tuple[str, bytes]]],
        start_date: str,
        initial_sm: float = 0.29,
        sm_threshold: float = 0.32,
    ) -> tuple[str, str]:
        """
        执行灌溉决策预测。

        :param uploaded_files: 上传文件字典，key 为变量名如 'irrad', 'tmax' 等，
                               value 为 [(filename, bytes), ...]
        :param start_date: 预测起始日期字符串，格式 YYYY-MM-DD
        :param initial_sm: 初始土壤含水量，默认 0.29
        :param sm_threshold: 土壤水分阈值，默认 0.32
        :return: (zip 文件路径, zip 文件名)
        """
        sim_start = datetime.strptime(start_date, '%Y-%m-%d')

        # 1. 创建输出目录
        prediction_id = f'pred_{start_date.replace("-", "")}_{uuid.uuid4().hex[:8]}'
        output_dir = os.path.join(IrrigationConfig.irrigation_output_dir, prediction_id)
        irr_dir = os.path.join(output_dir, 'irrigation')
        sm_dir = os.path.join(output_dir, 'soil_moisture')
        os.makedirs(irr_dir, exist_ok=True)
        os.makedirs(sm_dir, exist_ok=True)

        try:
            # 2. 读取并解析上传的 TIF 文件
            weather_data, profile, valid_idx, shape = cls._load_weather_tensors(
                uploaded_files, sim_start
            )
            n_pixels = shape[0] * shape[1]
            n_valid = len(valid_idx)

            # 3. 构建天气张量
            var_order = ['irrad', 'tmax', 'tmin', 'vap', 'wind', 'rain', 'et0']
            weather_np_list = []
            for date_idx in range(len(weather_data)):
                day_data = weather_data[date_idx]
                weather_np_list.append(
                    np.stack([day_data[v].flatten()[valid_idx] for v in var_order], axis=0)
                )

            weather_tensor = torch.from_numpy(np.stack(weather_np_list, axis=0)).float()
            weather_tensor = torch.where(
                weather_tensor < -1e30, torch.zeros_like(weather_tensor), weather_tensor
            )
            weather_tensor = weather_tensor.to(cls._device)

            rain = weather_tensor[:, 5, :]
            rain_cumsum = torch.cumsum(rain, dim=0)

            # 4. 初始化状态
            n_days = weather_tensor.shape[0]
            sm = torch.full((n_valid,), initial_sm, dtype=torch.float32, device=cls._device)
            tagp = torch.full((n_valid,), 45.0, dtype=torch.float32, device=cls._device)

            # 历史窗口初始化
            history = torch.zeros(n_valid, cls.HIST_LEN, 10, dtype=torch.float32, device=cls._device)
            first_w = weather_tensor[0]
            for t in range(cls.HIST_LEN):
                history[:, t, 0] = 0.0 / n_days
                history[:, t, 1] = sm
                history[:, t, 2] = first_w[0]
                history[:, t, 3] = first_w[1]
                history[:, t, 4] = first_w[2]
                history[:, t, 5] = first_w[3]
                history[:, t, 6] = first_w[4]
                history[:, t, 7] = first_w[5]
                history[:, t, 8] = first_w[6]
                history[:, t, 9] = 0.0

            history_scaled = (history - cls._x_mean) / cls._x_scale

            last_irrigation_day = torch.full(
                (n_valid,), -cls.MIN_IRRIGATION_INTERVAL, dtype=torch.int, device=cls._device
            )

            # 5. 逐日模拟
            results: list[dict[str, str]] = []
            sm_results: list[dict[str, str]] = []

            for day_idx in range(n_days):
                cur_date = sim_start + timedelta(days=day_idx)

                irrad = weather_tensor[day_idx, 0, :]
                tmax = weather_tensor[day_idx, 1, :]
                tmin = weather_tensor[day_idx, 2, :]
                vap = weather_tensor[day_idx, 3, :]
                wind = weather_tensor[day_idx, 4, :]
                rain_today = weather_tensor[day_idx, 5, :]
                et0 = weather_tensor[day_idx, 6, :]

                sm_before = sm.clone()

                # 未来滚动预测
                future_hist = history_scaled.clone()
                future_sm = sm.clone()
                future_min = torch.full_like(future_sm, float('inf'))
                future_sum = torch.zeros_like(future_sm)

                for k in range(min(cls.ROLL_HORIZON, n_days - day_idx)):
                    fw = weather_tensor[day_idx + k]
                    day_norm = (day_idx + k) / n_days
                    new_step = torch.stack([
                        torch.full_like(future_sm, day_norm),
                        future_sm,
                        fw[0], fw[1], fw[2], fw[3], fw[4], fw[5], fw[6],
                        torch.zeros_like(future_sm),
                    ], dim=1)
                    new_step_scaled = (new_step - cls._x_mean) / cls._x_scale
                    future_hist = torch.cat(
                        [future_hist[:, 1:, :], new_step_scaled.unsqueeze(1)], dim=1
                    )
                    pred = cls._lstm_predict(future_hist)
                    future_sm = pred[:, 0] + cls.SM_BIAS
                    future_min = torch.minimum(future_min, future_sm)
                    future_sum += future_sm

                future_mean = future_sum / cls.ROLL_HORIZON
                end_idx = min(day_idx + cls.ROLL_HORIZON - 1, n_days - 1)
                future_rain = rain_cumsum[end_idx] if day_idx == 0 else rain_cumsum[end_idx] - rain_cumsum[day_idx - 1]

                # RL 决策
                irr_raw = torch.zeros(n_valid, device=cls._device)
                states = cls._build_states(
                    sm, tagp, irrad, tmax, tmin, vap, wind, rain_today, et0,
                    future_min, future_mean, future_rain,
                )
                decision_mask = sm < sm_threshold
                if decision_mask.any():
                    acts = cls._rl_policy.predict_batch(states[decision_mask], deterministic=True)
                    irr_raw[decision_mask] = (acts[:, 0] + 1) * 1.0 + 2.0

                # 灌溉间隔约束
                days_since_last = day_idx - last_irrigation_day
                can_irrigate = days_since_last >= cls.MIN_IRRIGATION_INTERVAL
                irr_valid = torch.where(
                    (sm < sm_threshold) & can_irrigate,
                    irr_raw,
                    torch.zeros_like(irr_raw),
                )

                irrigated_today = irr_valid > 0
                last_irrigation_day[irrigated_today] = day_idx

                # 降雨空间重分配（仅调整当日已决策灌溉像元的灌溉量，不改变间隔判定）
                irr_valid = cls._adjust_irrigation_by_rain(
                    irr_valid, day_idx, weather_tensor,
                    low=cls.IRRIGATION_LOW, high=cls.IRRIGATION_HIGH,
                    noise_scale=cls.NOISE_SCALE,
                )

                # DEBUG 日志：输出每日关键决策变量
                irr_nonzero = irr_valid[irr_valid > 0]
                irr_mean_str = f"{irr_nonzero.mean().item():.4f}" if irr_nonzero.numel() > 0 else "N/A"
                irr_raw_nonzero = irr_raw[decision_mask]
                rl_mean_str = f"{irr_raw_nonzero.mean().item():.4f}" if irr_raw_nonzero.numel() > 0 else "N/A"
                rl_min_str = f"{irr_raw_nonzero.min().item():.4f}" if irr_raw_nonzero.numel() > 0 else "N/A"
                rl_max_str = f"{irr_raw_nonzero.max().item():.4f}" if irr_raw_nonzero.numel() > 0 else "N/A"
                print(
                    f"[DEBUG Day {day_idx} {cur_date.strftime('%Y-%m-%d')}] "
                    f"sm_mean={sm.mean().item():.4f} "
                    f"sm<{sm_threshold} count={decision_mask.sum().item()}/{n_valid} "
                    f"can_irrigate count={can_irrigate.sum().item()}/{n_valid} "
                    f"irr>0 count={(irr_valid > 0).sum().item()} "
                    f"irr_mean={irr_mean_str} "
                    f"rl_action: mean={rl_mean_str} min={rl_min_str} max={rl_max_str} "
                    f"last_irr_day min={last_irrigation_day.min().item()} "
                    f"days_since_last range=[{(day_idx - last_irrigation_day).min().item()}, {(day_idx - last_irrigation_day).max().item()}]"
                )

                # 更新历史与状态
                today_step = torch.stack([
                    torch.full((n_valid,), day_idx / n_days, device=cls._device),
                    sm,
                    irrad, tmax, tmin, vap, wind, rain_today, et0,
                    irr_valid,
                ], dim=1)
                today_scaled = (today_step - cls._x_mean) / cls._x_scale
                history_scaled = torch.cat(
                    [history_scaled[:, 1:, :], today_scaled.unsqueeze(1)], dim=1
                )
                pred_next = cls._lstm_predict(history_scaled)
                sm = pred_next[:, 0] + cls.SM_BIAS
                tagp = tagp + pred_next[:, 1]

                # 保存栅格
                irr_cpu = irr_valid.cpu().numpy()
                sm_cpu = sm_before.cpu().numpy()

                irr_full = np.full(n_pixels, np.nan, dtype=np.float32)
                irr_full[valid_idx] = irr_cpu
                sm_full = np.full(n_pixels, np.nan, dtype=np.float32)
                sm_full[valid_idx] = sm_cpu

                date_str = cur_date.strftime('%Y-%m-%d')
                irr_path = os.path.join(irr_dir, f'Irrigation_{date_str}.tif')
                sm_path = os.path.join(sm_dir, f'SM_{date_str}.tif')

                cls._save_raster(irr_full.reshape(shape), profile, irr_path)
                cls._save_raster(sm_full.reshape(shape), profile, sm_path)

            zip_filename = f'irrigation_prediction_{start_date}.zip'
            zip_path = os.path.join(IrrigationConfig.irrigation_output_dir, zip_filename)
            cls._build_prediction_zip(output_dir, zip_path)
            shutil.rmtree(output_dir)
            return zip_path, zip_filename

        except ValueError as exc:
            # 清理失败的输出目录
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
            raise ServiceException(message=str(exc)) from exc
        except Exception:
            # 清理失败的输出目录
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
            raise

    @classmethod
    def _load_weather_tensors(
        cls,
        uploaded_files: dict[str, list[tuple[str, bytes]]],
        sim_start: datetime,
    ) -> tuple[dict[int, dict[str, np.ndarray]], dict, np.ndarray, tuple]:
        """
        解析上传的 TIF 文件，构建日期索引的天气数据字典。
        返回 (weather_data, profile, valid_idx, shape)
        """
        import tempfile

        weather_data: dict[int, dict[str, np.ndarray]] = {}
        profile = None
        invalid_name_files: list[str] = []
        required_vars = {'irrad', 'tmax', 'tmin', 'vap', 'wind', 'rain', 'et0'}

        weather_files = uploaded_files.get('weather_files', [])
        if not weather_files:
            raise ValueError('未上传气象数据文件，请通过 weather_files 一次性上传 15×7 个 TIF 文件；如果来自浏览器前端，请检查不要手动设置 Content-Type，让浏览器自动附带 multipart boundary')

        for filename, file_bytes in weather_files:
            stem = filename.rsplit('.', 1)[0]
            parts = stem.rsplit('_', 1)
            if len(parts) < 2:
                invalid_name_files.append(filename)
                continue

            var_name = parts[0].lower()
            date_str = parts[1]
            if var_name not in required_vars:
                invalid_name_files.append(filename)
                continue
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                invalid_name_files.append(filename)
                continue

            day_offset = (file_date - sim_start).days
            if day_offset < 0:
                continue

            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                with rasterio.open(tmp_path) as src:
                    data = src.read(1)
                    if profile is None:
                        profile = src.profile.copy()
                    if day_offset not in weather_data:
                        weather_data[day_offset] = {}
                    weather_data[day_offset][var_name] = data
            finally:
                os.unlink(tmp_path)

        if not weather_data:
            sample_uploaded_names = '，'.join(filename for filename, _ in weather_files[:5])
            if invalid_name_files:
                sample_names = '，'.join(invalid_name_files[:3])
                raise ValueError(
                    f'未找到有效的气象数据文件：文件名需使用 VAR_YYYYMMDD.tif 格式，且 VAR 只能是 IRRAD/TMAX/TMIN/VAP/WIND/RAIN/ET0；当前无效示例：{sample_names}'
                )
            raise ValueError(
                f'未找到有效的气象数据文件：请确认上传文件名日期与 start_date={sim_start.strftime("%Y-%m-%d")} 对齐，且文件名格式为 '
                f'IRRAD/TMAX/TMIN/VAP/WIND/RAIN/ET0_YYYYMMDD.tif；当前收到示例：{sample_uploaded_names}'
            )

        max_offset = max(weather_data.keys())
        if max_offset + 1 < cls.ROLL_HORIZON:
            raise ValueError(f'气象数据文件数量不足，需要至少 {cls.ROLL_HORIZON} 天数据，当前仅有 {max_offset + 1} 天')

        var_order = ['irrad', 'tmax', 'tmin', 'vap', 'wind', 'rain', 'et0']
        expected_count = cls.ROLL_HORIZON * len(var_order)
        uploaded_weather_count = len(weather_files)
        if uploaded_weather_count < expected_count:
            raise ValueError(f'气象数据文件数量不足，需要至少 {expected_count} 个文件，当前仅上传 {uploaded_weather_count} 个')

        # 补齐缺失日期（使用前一天数据）
        for day_idx in range(max_offset + 1):
            if day_idx not in weather_data:
                if day_idx == 0:
                    raise ValueError(f'缺少第一天 {sim_start.strftime("%Y-%m-%d")} 的气象数据')
                weather_data[day_idx] = weather_data.get(day_idx - 1, {}).copy()

        missing_var_messages: list[str] = []

        # 补齐缺失变量（使用前一天同变量数据）
        for day_idx in range(max_offset + 1):
            day_dict = weather_data[day_idx]
            missing_vars = [var for var in var_order if var not in day_dict]
            if not missing_vars:
                continue
            if day_idx == 0:
                raise ValueError(
                    f'缺少第一天 {sim_start.strftime("%Y-%m-%d")} 的气象变量：{", ".join(v.upper() for v in missing_vars)}'
                )
            prev_day_dict = weather_data[day_idx - 1]
            unresolved_vars: list[str] = []
            for var in missing_vars:
                prev_value = prev_day_dict.get(var)
                if prev_value is None:
                    unresolved_vars.append(var)
                    continue
                day_dict[var] = prev_value
            if unresolved_vars:
                missing_var_messages.append(
                    f'{(sim_start + timedelta(days=day_idx)).strftime("%Y-%m-%d")}: {", ".join(v.upper() for v in unresolved_vars)}'
                )

        if missing_var_messages:
            raise ValueError(
                '气象数据存在缺失变量，且无法用前一天数据补齐：' + '；'.join(missing_var_messages[:5])
            )

        shape = None

        # 验证所有变量的栅格尺寸
        for day_idx in range(max_offset + 1):
            for var in var_order:
                arr = weather_data[day_idx].get(var)
                if arr is not None:
                    if shape is None:
                        shape = arr.shape
                    elif arr.shape != shape:
                        raise ValueError(f'栅格尺寸不匹配：变量 {var} 第 {day_idx} 天形状 {arr.shape} 与参考 {shape} 不一致')

        # 计算有效像元
        nodata = profile.get('nodata', -3.402823e38)
        first_day = weather_data[0]
        ref_arr = first_day.get('rain')
        if ref_arr is None:
            ref_arr = first_day.get('et0')
        if ref_arr is None:
            for var in var_order:
                if var in first_day:
                    ref_arr = first_day[var]
                    break
        if ref_arr is None:
            raise ValueError('无法确定栅格参考形状')

        ref_shape = ref_arr.shape
        n_pixels = ref_shape[0] * ref_shape[1]
        joint_valid = np.ones(n_pixels, dtype=bool)
        for var in var_order:
            arr = weather_data[0].get(var)
            if arr is not None:
                flat = arr.flatten()
                joint_valid &= (flat != nodata) & np.isfinite(flat)
        valid_idx = np.where(joint_valid)[0]

        if len(valid_idx) == 0:
            raise ValueError('无有效像元')

        return weather_data, profile, valid_idx, ref_shape

    @classmethod
    def _lstm_predict(cls, history: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            out = cls._proxy(history)
            last = out[:, -1, :]
            return last * cls._y_scale + cls._y_mean

    @classmethod
    def _rl_policy(cls, states: torch.Tensor, deterministic: bool = True) -> torch.Tensor:
        return cls._rl_policy.predict_batch(states, deterministic=deterministic)

    @classmethod
    def _build_states(cls, sm, tagp, irrad, tmax, tmin, vap, wind, rain, et0,
                      f_min_sm, f_mean_sm, f_rain_sum) -> torch.Tensor:
        return torch.stack([
            sm,
            tagp / 20000,
            irrad / 3e7,
            tmax / 50,
            tmin / 50,
            vap / 50,
            wind / 20,
            rain / 100,
            et0 / 20,
            f_min_sm,
            f_mean_sm,
            f_rain_sum / 100,
        ], dim=1)

    @classmethod
    def _adjust_irrigation_by_rain(cls, irr_valid, day_idx, weather_tensor,
                                    low=2.0, high=4.0, noise_scale=0.15) -> torch.Tensor:
        irrigated_mask = irr_valid > 0
        if irrigated_mask.sum() == 0:
            return irr_valid

        rain_day_idx = max(0, day_idx - 1)
        rain_all = weather_tensor[rain_day_idx, 5, :]
        rain_irr = rain_all[irrigated_mask]
        rain_min = rain_irr.min()
        rain_max = rain_irr.max()

        if rain_max - rain_min < 1e-8:
            irr_valid = irr_valid.clone()
            irr_valid[irrigated_mask] = high
            return irr_valid

        base_weight = rain_max - rain_irr
        randn = torch.randn_like(base_weight) * noise_scale * (rain_max - rain_min)
        weight = base_weight + randn
        weight = torch.clamp(weight, min=0.0)

        if weight.sum() == 0:
            irr_valid = irr_valid.clone()
            irr_valid[irrigated_mask] = high
            return irr_valid

        norm = weight / weight.sum()
        new_val = low + (high - low) * (norm - norm.min()) / (norm.max() - norm.min() + 1e-8)
        new_val = low + (high - low) * (new_val - new_val.min()) / (new_val.max() - new_val.min() + 1e-8)

        irr_valid = irr_valid.clone()
        irr_valid[irrigated_mask] = new_val
        return irr_valid

    @staticmethod
    def _save_raster(data: np.ndarray, profile: dict, path: str) -> None:
        p = profile.copy()
        p.update(dtype=rasterio.float32, count=1, compress='lzw', nodata=-9999)
        p.pop('blockxsize', None)
        p.pop('blockysize', None)
        out = data.copy()
        out[~np.isfinite(out)] = -9999
        with rasterio.open(path, 'w', **p) as dst:
            dst.write(out.astype(np.float32), 1)

    @staticmethod
    def _build_prediction_zip(source_dir: str, zip_path: str) -> None:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for file_name in files:
                    abs_path = os.path.join(root, file_name)
                    arcname = os.path.relpath(abs_path, source_dir)
                    zf.write(abs_path, arcname)
