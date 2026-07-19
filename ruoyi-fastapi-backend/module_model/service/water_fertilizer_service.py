from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from exceptions.exception import ServiceException
from module_model.dao.water_fertilizer_dao import WaterFertilizerDao
from module_model.entity.vo.water_fertilizer_vo import (
    WaterFertilizerOptimizeRequest,
    WaterFertilizerRegulationPageQueryModel,
)
from module_model.model.water_fertilizer_optimize import (
    NSGA3WaterFertilizerOptimizer,
    WaterFertilizerOptimizationProblem,
)
from utils.log_util import logger


class WaterFertilizerService:
    """
    水肥调控模型服务层。
    """

    @classmethod
    async def get_regulation_list_services(
        cls,
        query_db: AsyncSession,
        query_object: WaterFertilizerRegulationPageQueryModel,
        is_page: bool = False,
    ) -> PageModel | list[dict[str, Any]]:
        return await WaterFertilizerDao.get_regulation_list(query_db, query_object, is_page)

    @classmethod
    async def get_regulation_summary_services(cls, query_db: AsyncSession) -> dict[str, Any]:
        summary = await WaterFertilizerDao.get_regulation_summary(query_db)
        return {
            'total': int(summary.get('total') or 0),
            'startDate': summary.get('start_date'),
            'endDate': summary.get('end_date'),
        }

    @classmethod
    async def run_optimize_services(
        cls,
        query_db: AsyncSession,
        optimization_params: WaterFertilizerOptimizeRequest,
    ) -> dict[str, Any]:
        query = WaterFertilizerRegulationPageQueryModel(
            start_date=optimization_params.start_date,
            end_date=optimization_params.end_date,
            page_num=1,
            page_size=500,
        )
        regulation_list = await WaterFertilizerDao.get_regulation_list(query_db, query, is_page=False)
        if not regulation_list:
            raise ServiceException(message='指定时间范围内没有找到水肥调控数据')

        regulation_list = sorted(regulation_list, key=lambda item: item['recordTime'])
        regulation_data = cls._build_regulation_data(regulation_list)
        params = optimization_params.model_dump()

        try:
            result = await asyncio.to_thread(cls._run_optimizer, regulation_data, params)
        except (ValueError, RuntimeError) as exc:
            raise ServiceException(message=f'水肥调控优化失败: {exc}') from exc

        detailed_data = []
        best_solution = result.get('bestSolution')
        if best_solution and best_solution.get('decisionVariables'):
            detailed_data = cls._calculate_detailed_data(
                best_solution=best_solution,
                regulation_data=regulation_data,
                leakage=float(params['leakage']),
            )

        return {
            **result,
            'detailedData': detailed_data,
            'dataSummary': {
                'startDate': str(optimization_params.start_date),
                'endDate': str(optimization_params.end_date),
                'days': int(regulation_data['T']),
                'totalRainfall': float(np.sum(regulation_data['P'])),
                'meanMaxEvapotranspiration': float(np.mean(regulation_data['ET_MAXT'])),
                'meanMinEvapotranspiration': float(np.mean(regulation_data['ET_MINT'])),
            },
            'optimizationInfo': {
                **result.get('optimizationInfo', {}),
                'optimizationTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parameters': optimization_params.model_dump(mode='json', by_alias=True),
            },
        }

    @staticmethod
    def _build_regulation_data(regulation_list: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(regulation_list)
        return {
            'T': total,
            'P': np.array([float(item['dailyEffectiveRainfall']) for item in regulation_list]),
            'ET_MAXT': np.array([float(item['dailyMaxCropEvapotranspiration']) for item in regulation_list]),
            'ET_MINT': np.array([float(item['dailyMinCropEvapotranspiration']) for item in regulation_list]),
            'H_P': np.array([float(item['maxWaterStorageDepth']) for item in regulation_list]),
            'H_MAX': np.array([float(item['maxSuitableWaterDepth']) for item in regulation_list]),
            'H_MIN': np.array([float(item['minSuitableWaterDepth']) for item in regulation_list]),
            'records': regulation_list,
        }

    @staticmethod
    def _run_optimizer(regulation_data: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        problem = WaterFertilizerOptimizationProblem(regulation_data, params)
        optimizer = NSGA3WaterFertilizerOptimizer(
            population_size=int(params['population_size']),
            generations=int(params['generations']),
        )
        return optimizer.optimize(problem)

    @staticmethod
    def _calculate_detailed_data(
        best_solution: dict[str, Any],
        regulation_data: dict[str, Any],
        leakage: float,
    ) -> list[dict[str, Any]]:
        total = int(regulation_data['T'])
        rainfall = regulation_data['P']
        et_max = regulation_data['ET_MAXT']
        et_min = regulation_data['ET_MINT']
        h_p = regulation_data['H_P']
        h_max = regulation_data['H_MAX']
        h_min = regulation_data['H_MIN']
        records = regulation_data['records']
        irrigation = np.array(best_solution['decisionVariables']['irrigation'], dtype=float)

        water_depth = np.zeros(total)
        drainage = np.zeros(total)
        actual_et = np.zeros(total)
        water_depth[0] = h_p[0]

        detailed_data: list[dict[str, Any]] = []
        for idx in range(total):
            if water_depth[idx] <= h_min[idx]:
                actual_et[idx] = et_min[idx]
            elif water_depth[idx] >= h_max[idx]:
                actual_et[idx] = et_max[idx]
            else:
                denom = h_max[idx] - h_min[idx]
                gamma = (water_depth[idx] - h_min[idx]) / (denom if denom else 1e-12)
                actual_et[idx] = (1.0 - gamma) * et_min[idx] + gamma * et_max[idx]

            drainage[idx] = max(water_depth[idx] - h_p[idx], 0.0)
            if idx < total - 1:
                water_depth[idx + 1] = (
                    water_depth[idx] + irrigation[idx] + rainfall[idx] - actual_et[idx] - leakage - drainage[idx]
                )

            detailed_data.append(
                {
                    'period': idx + 1,
                    'recordTime': records[idx]['recordTime'],
                    'irrigation': float(irrigation[idx]),
                    'rainfall': float(rainfall[idx]),
                    'evapotranspiration': float(actual_et[idx]),
                    'leakage': float(leakage),
                    'drainage': float(drainage[idx]),
                    'waterDepth': float(water_depth[idx]),
                    'waterDepthMin': float(h_min[idx]),
                    'waterDepthMax': float(h_max[idx]),
                }
            )
        return detailed_data
