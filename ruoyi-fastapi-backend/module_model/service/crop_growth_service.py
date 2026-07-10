from __future__ import annotations

from module_model.entity.vo.crop_growth_vo import (
    RiceGrowthDailyResult,
    RiceGrowthSimulationRequest,
    RiceGrowthSimulationResponse,
    RiceGrowthSummary,
)
from module_model.model.pcse_growth_util import PcseGrowthUtil


class CropGrowthService:
    """
    作物生长模拟服务层。
    """

    @classmethod
    async def simulate_rice_growth(
        cls,
        request: RiceGrowthSimulationRequest,
    ) -> RiceGrowthSimulationResponse:
        result = PcseGrowthUtil.run_rice_growth_simulation(
            longitude=request.longitude,
            latitude=request.latitude,
            simulation_start_date=request.simulation_start_date,
            plant_start_date=request.plant_start_date,
            plant_end_date=request.plant_end_date,
            irrigation_end_date=request.irrigation_end_date,
            soil_moisture_threshold=request.soil_moisture_threshold,
            irrigation_efficiency=request.irrigation_efficiency,
            single_irrigation_amount=request.single_irrigation_amount,
            site_params=request.site.model_dump(),
            variety_name=request.variety_name,
        )
        return RiceGrowthSimulationResponse(
            summary=RiceGrowthSummary.model_validate(result['summary']),
            daily_results=[RiceGrowthDailyResult.model_validate(item) for item in result['daily_results']],
        )
