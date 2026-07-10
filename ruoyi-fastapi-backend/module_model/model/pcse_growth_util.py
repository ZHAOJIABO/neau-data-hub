from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any

import yaml

from module_model.model.custom_wofost import CustomWofost72WlpFd


class CropGrowthSimulationError(Exception):
    """
    作物生长模拟业务异常。
    """


class PcseGrowthUtil:
    """
    PCSE/WOFOST 水稻生长模拟工具。
    """

    OUTPUT_VARS = (
        'DVS',
        'LAI',
        'TAGP',
        'TWSO',
        'TWLV',
        'TWST',
        'TWRT',
        'TRA',
        'RD',
        'SM',
        'WWLOW',
        'RFTRA',
        'RIRR',
        'TOTIRR',
    )

    @classmethod
    def default_rice_model_dir(cls) -> str:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(backend_dir, 'models', 'crop_growth', 'rice')

    @classmethod
    def run_rice_growth_simulation(
        cls,
        *,
        longitude: float,
        latitude: float,
        simulation_start_date: str,
        plant_start_date: str,
        plant_end_date: str,
        irrigation_end_date: str,
        soil_moisture_threshold: float,
        irrigation_efficiency: float,
        single_irrigation_amount: float,
        site_params: dict[str, Any],
        variety_name: str = 'Rice_IR72_WS',
        model_dir: str | None = None,
    ) -> dict[str, Any]:
        cls._ensure_pcse_available()
        dates = cls._validate_dates(
            simulation_start_date=simulation_start_date,
            plant_start_date=plant_start_date,
            plant_end_date=plant_end_date,
            irrigation_end_date=irrigation_end_date,
        )
        crop_file, soil_file = cls._resolve_parameter_files(model_dir)

        from pcse.base import ParameterProvider
        from pcse.input import CABOFileReader, NASAPowerWeatherDataProvider, WOFOST72SiteDataProvider

        try:
            cropdata = cls._load_yaml_crop_parameters(crop_file, variety_name)
            soildata = CABOFileReader(soil_file)
        except Exception as exc:
            raise CropGrowthSimulationError(f'读取水稻参数文件失败: {exc}') from exc

        try:
            sitedata = WOFOST72SiteDataProvider(
                IFUNRN=float(site_params.get('ifunrn', 0)),
                NOTINF=float(site_params.get('notinf', 0.0)),
                SSI=float(site_params.get('ssi', 0.0)),
                SSMAX=float(site_params.get('ssmax', 0.0)),
                WAV=float(site_params.get('wav', 20.0)),
                SMLIM=float(site_params.get('smlim', 0.4)),
            )
            parameters = ParameterProvider(cropdata=cropdata, soildata=soildata, sitedata=sitedata)
        except Exception as exc:
            raise CropGrowthSimulationError(f'构造 WOFOST 参数失败: {exc}') from exc

        try:
            weather_provider = NASAPowerWeatherDataProvider(latitude, longitude)
        except Exception as exc:
            raise CropGrowthSimulationError(f'从 NASA POWER 获取气象数据失败: {exc}') from exc

        agromanagement = cls._build_agromanagement(
            simulation_start_date=simulation_start_date,
            plant_start_date=plant_start_date,
            plant_end_date=plant_end_date,
            irrigation_end_date=irrigation_end_date,
            max_duration=max((dates['plant_end_date'] - dates['plant_start_date']).days, 1),
            soil_moisture_threshold=soil_moisture_threshold,
            irrigation_efficiency=irrigation_efficiency,
            single_irrigation_amount=single_irrigation_amount,
            variety_name=variety_name,
        )

        try:
            simulation = CustomWofost72WlpFd(parameters, weather_provider, agromanagement)
            simulation.run_till_terminate()
            output = simulation.get_output()
        except Exception as exc:
            raise CropGrowthSimulationError(f'水稻 WOFOST 模拟失败: {exc}') from exc

        daily_results = cls._normalize_output(output, irrigation_efficiency)
        irrigation_summary = cls._build_irrigation_summary(daily_results)
        summary = cls._build_summary(daily_results, irrigation_summary, variety_name)
        return {'summary': summary, 'daily_results': daily_results}

    @classmethod
    def _ensure_pcse_available(cls) -> None:
        try:
            import pcse  # noqa: F401
        except ModuleNotFoundError as exc:
            raise CropGrowthSimulationError('当前环境未安装 PCSE，请在 neaudata 环境和 Docker 镜像中安装 pcse。') from exc

    @classmethod
    def _resolve_parameter_files(cls, model_dir: str | None = None) -> tuple[str, str]:
        base_dir = model_dir or cls.default_rice_model_dir()
        crop_file = os.path.join(base_dir, 'rice.crop')
        soil_file = os.path.join(base_dir, 'rice.soil')
        missing = [path for path in (crop_file, soil_file) if not os.path.isfile(path)]
        if missing:
            raise CropGrowthSimulationError('缺少水稻参数文件: ' + ', '.join(missing))
        return crop_file, soil_file

    @classmethod
    def _load_yaml_crop_parameters(cls, crop_file: str, variety_name: str) -> dict[str, Any]:
        with open(crop_file, encoding='utf-8') as file:
            raw = yaml.safe_load(file)

        crop_parameters = raw.get('CropParameters') if isinstance(raw, dict) else None
        if not isinstance(crop_parameters, dict):
            raise CropGrowthSimulationError('rice.crop 缺少 CropParameters 节点')

        varieties = crop_parameters.get('Varieties')
        if isinstance(varieties, dict):
            variety = varieties.get(variety_name)
            candidate_source = varieties
        else:
            variety = crop_parameters.get(variety_name)
            candidate_source = crop_parameters
        if not isinstance(variety, dict):
            candidates = sorted(
                key for key, value in candidate_source.items()
                if isinstance(value, dict) and key not in {'GenericC3', 'GenericC4', 'EcoTypes'}
            )
            raise CropGrowthSimulationError(f'rice.crop 中不存在品种 {variety_name}，可选: {", ".join(candidates)}')

        flat_params: dict[str, Any] = {}
        for key, value in variety.items():
            if key == 'Metadata':
                continue
            if isinstance(value, list) and value:
                flat_params[key] = value[0]
            else:
                flat_params[key] = value
        return flat_params

    @classmethod
    def _validate_dates(cls, **date_values: str) -> dict[str, datetime]:
        parsed: dict[str, datetime] = {}
        for key, value in date_values.items():
            try:
                parsed[key] = datetime.strptime(value, '%Y-%m-%d')
            except ValueError as exc:
                raise CropGrowthSimulationError(f'{key} 必须为 YYYY-MM-DD 格式') from exc

        if parsed['simulation_start_date'] > parsed['plant_start_date']:
            raise CropGrowthSimulationError('模拟开始日期不能晚于作物开始日期')
        if parsed['plant_start_date'] >= parsed['plant_end_date']:
            raise CropGrowthSimulationError('作物开始日期必须早于作物结束日期')
        if parsed['irrigation_end_date'] < parsed['plant_start_date']:
            raise CropGrowthSimulationError('灌溉结束日期不能早于作物开始日期')
        if parsed['irrigation_end_date'] > parsed['plant_end_date']:
            raise CropGrowthSimulationError('灌溉结束日期不能晚于作物结束日期')
        return parsed

    @classmethod
    def _build_agromanagement(
        cls,
        *,
        simulation_start_date: str,
        plant_start_date: str,
        plant_end_date: str,
        irrigation_end_date: str,
        max_duration: int,
        soil_moisture_threshold: float,
        irrigation_efficiency: float,
        single_irrigation_amount: float,
        variety_name: str,
    ) -> list[dict[str, Any]]:
        # WOFOST reports SM as absolute volumetric soil moisture [cm3/cm3].
        # Valid SM range for the bundled rice.soil: ~0.09 (residual) - 0.42 (saturation),
        # with wilting point at 0.11 and field capacity at 0.375.
        #
        # To produce a realistic irrigation schedule (multiple events per season)
        # we build a tiered events_table: a primary threshold supplied by the
        # caller, plus two progressively drier tiers below it. Each tier uses
        # `zero_condition: falling`, so an irrigation event fires whenever SM
        # crosses that tier from above. The split application (small amounts)
        # prevents a single irrigation from refilling the soil to saturation,
        # which would otherwise suppress further triggers for the rest of the
        # season.
        primary_threshold = round(float(soil_moisture_threshold), 4)
        tier_step = 0.02
        irrigation_tiers = [
            (primary_threshold, round(float(single_irrigation_amount), 4)),
            (
                round(primary_threshold - tier_step, 4),
                round(float(single_irrigation_amount) * 1.25, 4),
            ),
            (
                round(primary_threshold - 2 * tier_step, 4),
                round(float(single_irrigation_amount) * 1.5, 4),
            ),
        ]

        events_table_yaml = '\n'.join(
            f'                - {threshold}: {{amount: {amount}, efficiency: {irrigation_efficiency}}}'
            for threshold, amount in irrigation_tiers
        )

        lowest_tier = irrigation_tiers[-1][0]
        stop_threshold = round(max(lowest_tier - tier_step, 0.10), 4)

        yaml_agro = f"""
        - {simulation_start_date}:
            CropCalendar:
                crop_name: rice
                variety_name: {variety_name}
                crop_start_date: {plant_start_date}
                crop_start_type: emergence
                crop_end_date: {plant_end_date}
                crop_end_type: harvest
                max_duration: {max_duration}
            TimedEvents: null
            StateEvents:
            -   event_signal: irrigate
                event_state: SM
                zero_condition: falling
                name: Rice irrigation application table
                comment: Irrigation amounts in cm, tiered thresholds with split application
                events_table:
{events_table_yaml}
        - {irrigation_end_date}:
            CropCalendar:
            TimedEvents: null
            StateEvents:
            -   event_signal: irrigate
                event_state: SM
                zero_condition: falling
                name: Stop irrigation application table
                comment: Disable irrigation after configured date
                events_table:
                - {stop_threshold}: {{amount: 0, efficiency: {irrigation_efficiency}}}
        - {plant_end_date}: null
        """
        return yaml.safe_load(yaml_agro)

    @classmethod
    def _normalize_output(
        cls,
        output: Any,
        irrigation_efficiency: float = 1.0,
    ) -> list[dict[str, Any]]:
        if output is None:
            return []
        records = output.to_dict('records') if hasattr(output, 'to_dict') else list(output)
        normalized: list[dict[str, Any]] = []
        cumulative_applied_irrigation = 0.0
        for row in records:
            item = {'day': cls._format_day(row.get('day'))}
            for var_name in cls.OUTPUT_VARS:
                item[var_name.lower()] = cls._safe_float(row.get(var_name))

            # PCSE reports effective irrigation (amount * efficiency). The API
            # accepts and displays the field-applied amount, so restore that
            # management quantity and rebuild the cumulative series from it.
            effective_irrigation = float(item.get('rirr') or 0.0)
            applied_irrigation = effective_irrigation / irrigation_efficiency
            cumulative_applied_irrigation += applied_irrigation
            item['rirr'] = round(applied_irrigation, 6)
            item['totirr'] = round(cumulative_applied_irrigation, 6)
            normalized.append(item)
        return normalized

    @staticmethod
    def _build_irrigation_summary(daily_results: list[dict[str, Any]]) -> dict[str, Any]:
        irrigation_events = [
            float(item.get('rirr') or 0.0)
            for item in daily_results
            if float(item.get('rirr') or 0.0) > 1e-9
        ]
        return {
            'total_irrigation': sum(irrigation_events),
            'irrigation_count': len(irrigation_events),
        }

    @staticmethod
    def _format_day(value: Any) -> str:
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value)

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return round(number, 6)

    @classmethod
    def _build_summary(
        cls,
        daily_results: list[dict[str, Any]],
        irrigation_summary: dict[str, Any],
        variety_name: str,
    ) -> dict[str, Any]:
        last = daily_results[-1] if daily_results else {}
        lai_values = [item['lai'] for item in daily_results if item.get('lai') is not None]
        return {
            'simulation_days': len(daily_results),
            'final_yield': last.get('twso'),
            'final_lai': last.get('lai'),
            'max_lai': round(max(lai_values), 6) if lai_values else None,
            'final_tagp': last.get('tagp'),
            'total_irrigation': round(float(irrigation_summary.get('total_irrigation', 0.0) or 0.0), 6),
            'irrigation_count': int(irrigation_summary.get('irrigation_count', 0) or 0),
            'variety_name': variety_name,
            'weather_source': 'NASA POWER',
        }
