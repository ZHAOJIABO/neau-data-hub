import asyncio
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any, NamedTuple

import joblib
import numpy as np
import rasterio
import torch

from config.env import IrrigationConfig
from exceptions.exception import ServiceException
from module_irrigation.model.irrigation_models import LSTMModel, SACActor


class DailyWeather(NamedTuple):
    irrad: torch.Tensor
    tmax: torch.Tensor
    tmin: torch.Tensor
    vap: torch.Tensor
    wind: torch.Tensor
    rain: torch.Tensor
    et0: torch.Tensor


class DailyForecast(NamedTuple):
    future_min: torch.Tensor
    future_mean: torch.Tensor
    future_rain: torch.Tensor


class DailyState(NamedTuple):
    sm: torch.Tensor
    tagp: torch.Tensor
    history_scaled: torch.Tensor
    last_irrigation_day: torch.Tensor


class OutputPaths(NamedTuple):
    output_dir: str
    irr_dir: str
    sm_dir: str


class WeatherLoadResult(NamedTuple):
    weather_data: dict[int, dict[str, np.ndarray]]
    profile: dict
    valid_idx: np.ndarray
    shape: tuple[int, int]


class SimulationContext(NamedTuple):
    sim_start: datetime
    weather_tensor: torch.Tensor
    rain_cumsum: torch.Tensor
    sm_threshold: float
    n_pixels: int
    valid_idx: np.ndarray
    shape: tuple[int, int]
    profile: dict
    output_paths: OutputPaths


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
    SCALE_EPSILON = 1e-8
    WEATHER_FILL_THRESHOLD = -1e30
    FILENAME_PART_COUNT = 2
    SM_BIAS = -0.04  # LSTM 预测系统性偏高约 0.04，校正使 sm 落在合理区间
    VAR_ORDER = ('irrad', 'tmax', 'tmin', 'vap', 'wind', 'rain', 'et0')
    FEATURE_DIM = 10

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

        proxy = LSTMModel().to(device)
        proxy.load_state_dict(torch.load(os.path.join(model_dir, 'model.pth'), map_location=device))
        proxy.eval()
        cls._proxy = proxy

        scaler_x = joblib.load(os.path.join(model_dir, 'scaler_x.pkl'))
        scaler_y = joblib.load(os.path.join(model_dir, 'scaler_y.pkl'))
        if np.any(scaler_x.scale_ == 0):
            scaler_x.scale_[scaler_x.scale_ == 0] = cls.SCALE_EPSILON
        if np.any(scaler_y.scale_ == 0):
            scaler_y.scale_[scaler_y.scale_ == 0] = cls.SCALE_EPSILON
        cls._scaler_x = scaler_x
        cls._scaler_y = scaler_y

        cls._x_mean = torch.tensor(scaler_x.mean_, dtype=torch.float32, device=device)
        cls._x_scale = torch.tensor(scaler_x.scale_, dtype=torch.float32, device=device)
        cls._y_mean = torch.tensor(scaler_y.mean_, dtype=torch.float32, device=device)
        cls._y_scale = torch.tensor(scaler_y.scale_, dtype=torch.float32, device=device)

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
        output_paths = cls._create_output_dirs(start_date)

        try:
            weather_result = cls._load_weather_tensors(uploaded_files, sim_start)
            weather_tensor, rain_cumsum = cls._build_weather_tensor(
                weather_result.weather_data,
                weather_result.valid_idx,
            )
            state = cls._initialize_daily_state(weather_tensor, initial_sm)
            n_pixels = weather_result.shape[0] * weather_result.shape[1]

            context = SimulationContext(
                sim_start=sim_start,
                weather_tensor=weather_tensor,
                rain_cumsum=rain_cumsum,
                sm_threshold=sm_threshold,
                n_pixels=n_pixels,
                valid_idx=weather_result.valid_idx,
                shape=weather_result.shape,
                profile=weather_result.profile,
                output_paths=output_paths,
            )

            for day_idx in range(weather_tensor.shape[0]):
                state = cls._simulate_single_day(
                    day_idx=day_idx,
                    state=state,
                    context=context,
                )

            return cls._finalize_prediction(output_paths.output_dir, start_date)

        except ValueError as exc:
            cls._cleanup_output_dir(output_paths.output_dir)
            raise ServiceException(message=str(exc)) from exc
        except Exception:
            cls._cleanup_output_dir(output_paths.output_dir)
            raise

    @classmethod
    def _create_output_dirs(cls, start_date: str) -> OutputPaths:
        prediction_id = f'pred_{start_date.replace("-", "")}_{uuid.uuid4().hex[:8]}'
        output_dir = os.path.join(IrrigationConfig.irrigation_output_dir, prediction_id)
        irr_dir = os.path.join(output_dir, 'irrigation')
        sm_dir = os.path.join(output_dir, 'soil_moisture')
        os.makedirs(irr_dir, exist_ok=True)
        os.makedirs(sm_dir, exist_ok=True)
        return OutputPaths(output_dir=output_dir, irr_dir=irr_dir, sm_dir=sm_dir)

    @classmethod
    def _build_weather_tensor(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        valid_idx: np.ndarray,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        weather_np_list = []
        for date_idx in range(len(weather_data)):
            day_data = weather_data[date_idx]
            weather_np_list.append(
                np.stack([day_data[var].flatten()[valid_idx] for var in cls.VAR_ORDER], axis=0)
            )

        weather_tensor = torch.from_numpy(np.stack(weather_np_list, axis=0)).float()
        weather_tensor = torch.where(
            weather_tensor < cls.WEATHER_FILL_THRESHOLD,
            torch.zeros_like(weather_tensor),
            weather_tensor,
        )
        weather_tensor = weather_tensor.to(cls._device)
        rain_cumsum = torch.cumsum(weather_tensor[:, 5, :], dim=0)
        return weather_tensor, rain_cumsum

    @classmethod
    def _initialize_daily_state(cls, weather_tensor: torch.Tensor, initial_sm: float) -> DailyState:
        n_valid = weather_tensor.shape[2]
        n_days = weather_tensor.shape[0]
        sm = torch.full((n_valid,), initial_sm, dtype=torch.float32, device=cls._device)
        tagp = torch.full((n_valid,), 45.0, dtype=torch.float32, device=cls._device)
        history = cls._build_initial_history(weather_tensor[0], sm, n_valid, n_days)
        history_scaled = (history - cls._x_mean) / cls._x_scale
        last_irrigation_day = torch.full(
            (n_valid,),
            -cls.MIN_IRRIGATION_INTERVAL,
            dtype=torch.int,
            device=cls._device,
        )
        return DailyState(
            sm=sm,
            tagp=tagp,
            history_scaled=history_scaled,
            last_irrigation_day=last_irrigation_day,
        )

    @classmethod
    def _build_initial_history(
        cls,
        first_weather: torch.Tensor,
        sm: torch.Tensor,
        n_valid: int,
        n_days: int,
    ) -> torch.Tensor:
        history = torch.zeros(
            n_valid,
            cls.HIST_LEN,
            cls.FEATURE_DIM,
            dtype=torch.float32,
            device=cls._device,
        )
        for t in range(cls.HIST_LEN):
            history[:, t, 0] = 0.0 / n_days
            history[:, t, 1] = sm
            history[:, t, 2] = first_weather[0]
            history[:, t, 3] = first_weather[1]
            history[:, t, 4] = first_weather[2]
            history[:, t, 5] = first_weather[3]
            history[:, t, 6] = first_weather[4]
            history[:, t, 7] = first_weather[5]
            history[:, t, 8] = first_weather[6]
            history[:, t, 9] = 0.0
        return history

    @classmethod
    def _simulate_single_day(
        cls,
        day_idx: int,
        state: DailyState,
        context: SimulationContext,
    ) -> DailyState:
        cur_date = context.sim_start + timedelta(days=day_idx)
        day_weather = cls._get_daily_weather(context.weather_tensor, day_idx)
        sm_before = state.sm.clone()
        forecast = cls._forecast_future_weather(
            day_idx=day_idx,
            weather_tensor=context.weather_tensor,
            history_scaled=state.history_scaled,
            sm=state.sm,
            rain_cumsum=context.rain_cumsum,
        )
        irr_valid, decision_mask, can_irrigate, irr_raw, state = cls._compute_daily_irrigation(
            day_idx=day_idx,
            state=state,
            day_weather=day_weather,
            weather_tensor=context.weather_tensor,
            forecast=forecast,
            sm_threshold=context.sm_threshold,
        )
        cls._log_daily_decision(
            day_idx=day_idx,
            cur_date=cur_date,
            sm=state.sm,
            sm_threshold=context.sm_threshold,
            decision_mask=decision_mask,
            can_irrigate=can_irrigate,
            irr_valid=irr_valid,
            irr_raw=irr_raw,
            last_irrigation_day=state.last_irrigation_day,
        )
        next_state = cls._advance_daily_state(
            day_idx=day_idx,
            n_days=context.weather_tensor.shape[0],
            state=state,
            day_weather=day_weather,
            irr_valid=irr_valid,
        )
        cls._save_daily_rasters(
            cur_date=cur_date,
            irr_valid=irr_valid,
            sm_before=sm_before,
            n_pixels=context.n_pixels,
            valid_idx=context.valid_idx,
            shape=context.shape,
            profile=context.profile,
            output_paths=context.output_paths,
        )
        return next_state

    @classmethod
    def _get_daily_weather(cls, weather_tensor: torch.Tensor, day_idx: int) -> DailyWeather:
        return DailyWeather(
            irrad=weather_tensor[day_idx, 0, :],
            tmax=weather_tensor[day_idx, 1, :],
            tmin=weather_tensor[day_idx, 2, :],
            vap=weather_tensor[day_idx, 3, :],
            wind=weather_tensor[day_idx, 4, :],
            rain=weather_tensor[day_idx, 5, :],
            et0=weather_tensor[day_idx, 6, :],
        )

    @classmethod
    def _forecast_future_weather(
        cls,
        day_idx: int,
        weather_tensor: torch.Tensor,
        history_scaled: torch.Tensor,
        sm: torch.Tensor,
        rain_cumsum: torch.Tensor,
    ) -> DailyForecast:
        n_days = weather_tensor.shape[0]
        future_hist = history_scaled.clone()
        future_sm = sm.clone()
        future_min = torch.full_like(future_sm, float('inf'))
        future_sum = torch.zeros_like(future_sm)

        for k in range(min(cls.ROLL_HORIZON, n_days - day_idx)):
            future_hist, future_sm = cls._forecast_single_future_step(
                future_hist=future_hist,
                future_sm=future_sm,
                future_weather=weather_tensor[day_idx + k],
                normalized_day=(day_idx + k) / n_days,
            )
            future_min = torch.minimum(future_min, future_sm)
            future_sum += future_sm

        end_idx = min(day_idx + cls.ROLL_HORIZON - 1, n_days - 1)
        future_rain = cls._compute_future_rain(day_idx, end_idx, rain_cumsum)
        return DailyForecast(
            future_min=future_min,
            future_mean=future_sum / cls.ROLL_HORIZON,
            future_rain=future_rain,
        )

    @classmethod
    def _forecast_single_future_step(
        cls,
        future_hist: torch.Tensor,
        future_sm: torch.Tensor,
        future_weather: torch.Tensor,
        normalized_day: float,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        new_step = torch.stack(
            [
                torch.full_like(future_sm, normalized_day),
                future_sm,
                future_weather[0],
                future_weather[1],
                future_weather[2],
                future_weather[3],
                future_weather[4],
                future_weather[5],
                future_weather[6],
                torch.zeros_like(future_sm),
            ],
            dim=1,
        )
        new_step_scaled = (new_step - cls._x_mean) / cls._x_scale
        future_hist = torch.cat([future_hist[:, 1:, :], new_step_scaled.unsqueeze(1)], dim=1)
        pred = cls._lstm_predict(future_hist)
        return future_hist, pred[:, 0] + cls.SM_BIAS

    @classmethod
    def _compute_future_rain(
        cls,
        day_idx: int,
        end_idx: int,
        rain_cumsum: torch.Tensor,
    ) -> torch.Tensor:
        if day_idx == 0:
            return rain_cumsum[end_idx]
        return rain_cumsum[end_idx] - rain_cumsum[day_idx - 1]

    @classmethod
    def _compute_daily_irrigation(
        cls,
        day_idx: int,
        state: DailyState,
        day_weather: DailyWeather,
        weather_tensor: torch.Tensor,
        forecast: DailyForecast,
        sm_threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, DailyState]:
        irr_raw = torch.zeros_like(state.sm)
        states = cls._build_states(
            state.sm,
            state.tagp,
            day_weather,
            forecast,
        )
        decision_mask = state.sm < sm_threshold
        if decision_mask.any():
            acts = cls._rl_policy.predict_batch(states[decision_mask], deterministic=True)
            irr_raw[decision_mask] = (acts[:, 0] + 1) * 1.0 + 2.0

        days_since_last = day_idx - state.last_irrigation_day
        can_irrigate = days_since_last >= cls.MIN_IRRIGATION_INTERVAL
        irr_valid = torch.where(
            (state.sm < sm_threshold) & can_irrigate,
            irr_raw,
            torch.zeros_like(irr_raw),
        )

        irrigated_today = irr_valid > 0
        last_irrigation_day = state.last_irrigation_day.clone()
        last_irrigation_day[irrigated_today] = day_idx
        state = DailyState(
            sm=state.sm,
            tagp=state.tagp,
            history_scaled=state.history_scaled,
            last_irrigation_day=last_irrigation_day,
        )
        irr_valid = cls._adjust_irrigation_by_rain(
            irr_valid,
            day_idx,
            weather_tensor,
            low=cls.IRRIGATION_LOW,
            high=cls.IRRIGATION_HIGH,
            noise_scale=cls.NOISE_SCALE,
        )
        return irr_valid, decision_mask, can_irrigate, irr_raw, state

    @classmethod
    def _log_daily_decision(
        cls,
        day_idx: int,
        cur_date: datetime,
        sm: torch.Tensor,
        sm_threshold: float,
        decision_mask: torch.Tensor,
        can_irrigate: torch.Tensor,
        irr_valid: torch.Tensor,
        irr_raw: torch.Tensor,
        last_irrigation_day: torch.Tensor,
    ) -> None:
        irr_nonzero = irr_valid[irr_valid > 0]
        irr_mean_str = f'{irr_nonzero.mean().item():.4f}' if irr_nonzero.numel() > 0 else 'N/A'
        irr_raw_nonzero = irr_raw[decision_mask]
        rl_mean_str = f'{irr_raw_nonzero.mean().item():.4f}' if irr_raw_nonzero.numel() > 0 else 'N/A'
        rl_min_str = f'{irr_raw_nonzero.min().item():.4f}' if irr_raw_nonzero.numel() > 0 else 'N/A'
        rl_max_str = f'{irr_raw_nonzero.max().item():.4f}' if irr_raw_nonzero.numel() > 0 else 'N/A'
        print(
            f'[DEBUG Day {day_idx} {cur_date.strftime("%Y-%m-%d")}] '
            f'sm_mean={sm.mean().item():.4f} '
            f'sm<{sm_threshold} count={decision_mask.sum().item()}/{sm.numel()} '
            f'can_irrigate count={can_irrigate.sum().item()}/{sm.numel()} '
            f'irr>0 count={(irr_valid > 0).sum().item()} '
            f'irr_mean={irr_mean_str} '
            f'rl_action: mean={rl_mean_str} min={rl_min_str} max={rl_max_str} '
            f'last_irr_day min={last_irrigation_day.min().item()} '
            f'days_since_last range=[{(day_idx - last_irrigation_day).min().item()}, {(day_idx - last_irrigation_day).max().item()}]'
        )

    @classmethod
    def _advance_daily_state(
        cls,
        day_idx: int,
        n_days: int,
        state: DailyState,
        day_weather: DailyWeather,
        irr_valid: torch.Tensor,
    ) -> DailyState:
        today_step = torch.stack(
            [
                torch.full((state.sm.shape[0],), day_idx / n_days, device=cls._device),
                state.sm,
                day_weather.irrad,
                day_weather.tmax,
                day_weather.tmin,
                day_weather.vap,
                day_weather.wind,
                day_weather.rain,
                day_weather.et0,
                irr_valid,
            ],
            dim=1,
        )
        today_scaled = (today_step - cls._x_mean) / cls._x_scale
        history_scaled = torch.cat([state.history_scaled[:, 1:, :], today_scaled.unsqueeze(1)], dim=1)
        pred_next = cls._lstm_predict(history_scaled)
        return DailyState(
            sm=pred_next[:, 0] + cls.SM_BIAS,
            tagp=state.tagp + pred_next[:, 1],
            history_scaled=history_scaled,
            last_irrigation_day=state.last_irrigation_day,
        )

    @classmethod
    def _save_daily_rasters(
        cls,
        cur_date: datetime,
        irr_valid: torch.Tensor,
        sm_before: torch.Tensor,
        n_pixels: int,
        valid_idx: np.ndarray,
        shape: tuple[int, int],
        profile: dict,
        output_paths: OutputPaths,
    ) -> None:
        irr_cpu = irr_valid.cpu().numpy()
        sm_cpu = sm_before.cpu().numpy()
        irr_full = np.full(n_pixels, np.nan, dtype=np.float32)
        irr_full[valid_idx] = irr_cpu
        sm_full = np.full(n_pixels, np.nan, dtype=np.float32)
        sm_full[valid_idx] = sm_cpu

        date_str = cur_date.strftime('%Y-%m-%d')
        irr_path = os.path.join(output_paths.irr_dir, f'Irrigation_{date_str}.tif')
        sm_path = os.path.join(output_paths.sm_dir, f'SM_{date_str}.tif')
        cls._save_raster(irr_full.reshape(shape), profile, irr_path)
        cls._save_raster(sm_full.reshape(shape), profile, sm_path)

    @classmethod
    def _finalize_prediction(cls, output_dir: str, start_date: str) -> tuple[str, str]:
        zip_filename = f'irrigation_prediction_{start_date}.zip'
        zip_path = os.path.join(IrrigationConfig.irrigation_output_dir, zip_filename)
        cls._build_prediction_zip(output_dir, zip_path)
        shutil.rmtree(output_dir)
        return zip_path, zip_filename

    @staticmethod
    def _cleanup_output_dir(output_dir: str) -> None:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)

    @classmethod
    def _load_weather_tensors(
        cls,
        uploaded_files: dict[str, list[tuple[str, bytes]]],
        sim_start: datetime,
    ) -> WeatherLoadResult:
        """
        解析上传的 TIF 文件，构建日期索引的天气数据字典。
        返回 (weather_data, profile, valid_idx, shape)
        """
        weather_files = uploaded_files.get('weather_files', [])
        if not weather_files:
            raise ValueError('未上传气象数据文件，请通过 weather_files 一次性上传 15×7 个 TIF 文件；如果来自浏览器前端，请检查不要手动设置 Content-Type，让浏览器自动附带 multipart boundary')

        weather_data, profile, invalid_name_files = cls._parse_weather_files(weather_files, sim_start)
        cls._validate_weather_parse_result(weather_data, weather_files, invalid_name_files, sim_start)
        cls._validate_weather_file_count(weather_data, weather_files)
        cls._fill_missing_days(weather_data, sim_start)
        cls._fill_missing_variables(weather_data, sim_start)
        cls._validate_weather_shapes(weather_data)
        valid_idx, ref_shape = cls._compute_valid_pixels(weather_data, profile)
        return WeatherLoadResult(
            weather_data=weather_data,
            profile=profile,
            valid_idx=valid_idx,
            shape=ref_shape,
        )

    @classmethod
    def _parse_weather_files(
        cls,
        weather_files: list[tuple[str, bytes]],
        sim_start: datetime,
    ) -> tuple[dict[int, dict[str, np.ndarray]], dict | None, list[str]]:
        weather_data: dict[int, dict[str, np.ndarray]] = {}
        profile = None
        invalid_name_files: list[str] = []
        required_vars = set(cls.VAR_ORDER)

        for filename, file_bytes in weather_files:
            parsed = cls._parse_weather_filename(filename, required_vars, sim_start)
            if parsed is None:
                invalid_name_files.append(filename)
                continue
            day_offset, var_name = parsed
            cls._store_weather_raster(weather_data, day_offset, var_name, file_bytes)
            if profile is None:
                profile = cls._read_raster_profile(file_bytes)

        return weather_data, profile, invalid_name_files

    @classmethod
    def _parse_weather_filename(
        cls,
        filename: str,
        required_vars: set[str],
        sim_start: datetime,
    ) -> tuple[int, str] | None:
        stem = filename.rsplit('.', 1)[0]
        parts = stem.rsplit('_', 1)
        if len(parts) < cls.FILENAME_PART_COUNT:
            return None

        var_name = parts[0].lower()
        date_str = parts[1]
        if var_name not in required_vars:
            return None
        try:
            file_date = datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            return None

        day_offset = (file_date - sim_start).days
        if day_offset < 0:
            return None
        return day_offset, var_name

    @classmethod
    def _store_weather_raster(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        day_offset: int,
        var_name: str,
        file_bytes: bytes,
    ) -> None:
        data, _ = cls._read_raster_bytes(file_bytes)
        weather_data.setdefault(day_offset, {})[var_name] = data

    @classmethod
    def _read_raster_profile(cls, file_bytes: bytes) -> dict:
        _, profile = cls._read_raster_bytes(file_bytes)
        return profile

    @classmethod
    def _read_raster_bytes(cls, file_bytes: bytes) -> tuple[np.ndarray, dict]:
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            with rasterio.open(tmp_path) as src:
                return src.read(1), src.profile.copy()
        finally:
            os.unlink(tmp_path)

    @classmethod
    def _validate_weather_parse_result(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        weather_files: list[tuple[str, bytes]],
        invalid_name_files: list[str],
        sim_start: datetime,
    ) -> None:
        if weather_data:
            return

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

    @classmethod
    def _validate_weather_file_count(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        weather_files: list[tuple[str, bytes]],
    ) -> None:
        max_offset = max(weather_data.keys())
        if max_offset + 1 < cls.ROLL_HORIZON:
            raise ValueError(f'气象数据文件数量不足，需要至少 {cls.ROLL_HORIZON} 天数据，当前仅有 {max_offset + 1} 天')

        expected_count = cls.ROLL_HORIZON * len(cls.VAR_ORDER)
        uploaded_weather_count = len(weather_files)
        if uploaded_weather_count < expected_count:
            raise ValueError(f'气象数据文件数量不足，需要至少 {expected_count} 个文件，当前仅上传 {uploaded_weather_count} 个')

    @classmethod
    def _fill_missing_days(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        sim_start: datetime,
    ) -> None:
        max_offset = max(weather_data.keys())
        for day_idx in range(max_offset + 1):
            if day_idx not in weather_data:
                if day_idx == 0:
                    raise ValueError(f'缺少第一天 {sim_start.strftime("%Y-%m-%d")} 的气象数据')
                weather_data[day_idx] = weather_data.get(day_idx - 1, {}).copy()

    @classmethod
    def _fill_missing_variables(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        sim_start: datetime,
    ) -> None:
        max_offset = max(weather_data.keys())
        missing_var_messages: list[str] = []

        for day_idx in range(max_offset + 1):
            day_dict = weather_data[day_idx]
            missing_vars = [var for var in cls.VAR_ORDER if var not in day_dict]
            if not missing_vars:
                continue
            if day_idx == 0:
                raise ValueError(
                    f'缺少第一天 {sim_start.strftime("%Y-%m-%d")} 的气象变量：{", ".join(v.upper() for v in missing_vars)}'
                )
            unresolved_vars = cls._copy_missing_vars_from_previous_day(weather_data, day_idx, missing_vars)
            if unresolved_vars:
                missing_var_messages.append(
                    f'{(sim_start + timedelta(days=day_idx)).strftime("%Y-%m-%d")}: {", ".join(v.upper() for v in unresolved_vars)}'
                )

        if missing_var_messages:
            raise ValueError('气象数据存在缺失变量，且无法用前一天数据补齐：' + '；'.join(missing_var_messages[:5]))

    @classmethod
    def _copy_missing_vars_from_previous_day(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        day_idx: int,
        missing_vars: list[str],
    ) -> list[str]:
        prev_day_dict = weather_data[day_idx - 1]
        unresolved_vars: list[str] = []
        for var in missing_vars:
            prev_value = prev_day_dict.get(var)
            if prev_value is None:
                unresolved_vars.append(var)
                continue
            weather_data[day_idx][var] = prev_value
        return unresolved_vars

    @classmethod
    def _validate_weather_shapes(cls, weather_data: dict[int, dict[str, np.ndarray]]) -> None:
        max_offset = max(weather_data.keys())
        shape = None
        for day_idx in range(max_offset + 1):
            for var in cls.VAR_ORDER:
                arr = weather_data[day_idx].get(var)
                if arr is None:
                    continue
                if shape is None:
                    shape = arr.shape
                elif arr.shape != shape:
                    raise ValueError(f'栅格尺寸不匹配：变量 {var} 第 {day_idx} 天形状 {arr.shape} 与参考 {shape} 不一致')

    @classmethod
    def _compute_valid_pixels(
        cls,
        weather_data: dict[int, dict[str, np.ndarray]],
        profile: dict | None,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        if profile is None:
            raise ValueError('无法读取栅格元数据')
        nodata = profile.get('nodata', -3.402823e38)
        first_day = weather_data[0]
        ref_arr = cls._get_reference_array(first_day)
        ref_shape = ref_arr.shape
        joint_valid = np.ones(ref_shape[0] * ref_shape[1], dtype=bool)
        for var in cls.VAR_ORDER:
            arr = first_day.get(var)
            if arr is None:
                continue
            flat = arr.flatten()
            joint_valid &= (flat != nodata) & np.isfinite(flat)
        valid_idx = np.where(joint_valid)[0]
        if len(valid_idx) == 0:
            raise ValueError('无有效像元')
        return valid_idx, ref_shape

    @classmethod
    def _get_reference_array(cls, first_day: dict[str, np.ndarray]) -> np.ndarray:
        ref_arr = first_day.get('rain') or first_day.get('et0')
        if ref_arr is None:
            for var in cls.VAR_ORDER:
                if var in first_day:
                    ref_arr = first_day[var]
                    break
        if ref_arr is None:
            raise ValueError('无法确定栅格参考形状')
        return ref_arr

    @classmethod
    def _lstm_predict(cls, history: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            out = cls._proxy(history)
            last = out[:, -1, :]
            return last * cls._y_scale + cls._y_mean

    @classmethod
    def _build_states(
        cls,
        sm: torch.Tensor,
        tagp: torch.Tensor,
        day_weather: DailyWeather,
        forecast: DailyForecast,
    ) -> torch.Tensor:
        return torch.stack(
            [
                sm,
                tagp / 20000,
                day_weather.irrad / 3e7,
                day_weather.tmax / 50,
                day_weather.tmin / 50,
                day_weather.vap / 50,
                day_weather.wind / 20,
                day_weather.rain / 100,
                day_weather.et0 / 20,
                forecast.future_min,
                forecast.future_mean,
                forecast.future_rain / 100,
            ],
            dim=1,
        )

    @classmethod
    def _adjust_irrigation_by_rain(
        cls,
        irr_valid: torch.Tensor,
        day_idx: int,
        weather_tensor: torch.Tensor,
        low: float = 2.0,
        high: float = 4.0,
        noise_scale: float = 0.15,
    ) -> torch.Tensor:
        irrigated_mask = irr_valid > 0
        if irrigated_mask.sum() == 0:
            return irr_valid

        rain_day_idx = max(0, day_idx - 1)
        rain_all = weather_tensor[rain_day_idx, 5, :]
        rain_irr = rain_all[irrigated_mask]
        rain_min = rain_irr.min()
        rain_max = rain_irr.max()

        if rain_max - rain_min < cls.SCALE_EPSILON:
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
        new_val = low + (high - low) * (norm - norm.min()) / (norm.max() - norm.min() + cls.SCALE_EPSILON)
        new_val = low + (high - low) * (new_val - new_val.min()) / (
            new_val.max() - new_val.min() + cls.SCALE_EPSILON
        )

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
