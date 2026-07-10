from __future__ import annotations

import logging
from typing import Any

from pcse.models import Wofost72_WLP_FD

logger = logging.getLogger(__name__)


class CustomWofost72WlpFd(Wofost72_WLP_FD):
    """
    WOFOST72 水分限制模型扩展，补充逐日灌溉量输出。
    """

    def __init__(self, parameterprovider, weatherdataprovider, agromanagement, **kwargs):
        self._daily_irrigation: list[dict[str, Any]] = []
        self._cumulative_irrigation = 0.0
        super().__init__(parameterprovider, weatherdataprovider, agromanagement, **kwargs)
        self._add_irrigation_vars_to_output()

    def _add_irrigation_vars_to_output(self) -> None:
        if hasattr(self.mconf, 'OUTPUT_VARS'):
            current_vars = list(self.mconf.OUTPUT_VARS)
        else:
            current_vars = [
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
            ]

        for var_name in ('RIRR', 'TOTIRR'):
            if var_name not in current_vars:
                current_vars.append(var_name)
        self.mconf.OUTPUT_VARS = current_vars

    def _save_output(self, day):
        super()._save_output(day)
        current_irrigation = self._get_current_irrigation()
        self._cumulative_irrigation += current_irrigation
        self._daily_irrigation.append({'day': day, 'daily_irrigation': current_irrigation})

        if self._saved_output:
            last_output = self._saved_output[-1]
            last_output['RIRR'] = current_irrigation
            last_output['TOTIRR'] = self._cumulative_irrigation

    def _get_current_irrigation(self) -> float:
        try:
            if 'RIRR' in self.kiosk:
                return float(self.kiosk['RIRR'])
            if hasattr(self, 'soil') and hasattr(self.soil, 'RIRR'):
                return float(self.soil.RIRR)
            if self._saved_output:
                return float(self._saved_output[-1].get('RIRR', 0.0) or 0.0)
        except Exception as exc:
            logger.warning('无法获取当前灌溉量: %s', exc)
        return 0.0

    def get_irrigation_summary(self) -> dict[str, float | int]:
        daily_amounts = [float(item['daily_irrigation'] or 0.0) for item in self._daily_irrigation]
        irrigation_days = len([amount for amount in daily_amounts if amount > 0])
        return {
            'total_irrigation': float(self._cumulative_irrigation),
            'irrigation_days': irrigation_days,
            'average_daily_irrigation': sum(daily_amounts) / len(daily_amounts) if daily_amounts else 0.0,
            'max_daily_irrigation': max(daily_amounts) if daily_amounts else 0.0,
        }
