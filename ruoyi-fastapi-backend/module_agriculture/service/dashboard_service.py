from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from module_agriculture.entity.do.crop_do import CropLeafArea
from module_agriculture.entity.do.soil_do import SoilGroundTemperature, SoilParameter, SoilSensorMonitor, SoilThickness
from module_agriculture.entity.do.station_do import Station
from module_agriculture.entity.do.weather_do import WeatherHumidity, WeatherPrecipitation, WeatherTemperature


class DashboardService:
    """
    数据概览服务层
    """

    @classmethod
    async def get_stats_services(cls, query_db: AsyncSession) -> dict:
        station_count = (await query_db.execute(select(func.count()).select_from(Station))).scalar()
        temp_count = (await query_db.execute(select(func.count()).select_from(WeatherTemperature))).scalar()
        humidity_count = (await query_db.execute(select(func.count()).select_from(WeatherHumidity))).scalar()
        precip_count = (await query_db.execute(select(func.count()).select_from(WeatherPrecipitation))).scalar()
        sensor_count = (await query_db.execute(select(func.count()).select_from(SoilSensorMonitor))).scalar()
        soil_param_count = (await query_db.execute(select(func.count()).select_from(SoilParameter))).scalar()
        ground_temp_count = (await query_db.execute(select(func.count()).select_from(SoilGroundTemperature))).scalar()
        thickness_count = (await query_db.execute(select(func.count()).select_from(SoilThickness))).scalar()
        crop_count = (await query_db.execute(select(func.count()).select_from(CropLeafArea))).scalar()

        return {
            'stationCount': station_count,
            'weatherStats': {
                'temperatureCount': temp_count,
                'humidityCount': humidity_count,
                'precipitationCount': precip_count,
            },
            'soilStats': {
                'sensorCount': sensor_count,
                'parameterCount': soil_param_count,
                'groundTempCount': ground_temp_count,
                'thicknessCount': thickness_count,
            },
            'cropCount': crop_count,
        }
