from fastapi import Depends, Request, params

from config.env import IrrigationConfig
from exceptions.exception import AuthException


class IrrigationApiKey:
    """
    灌溉接口 API Key 认证类
    """

    async def __call__(self, request: Request) -> None:
        """
        验证 X-Irrigation-Api-Key header

        :param request: 当前请求对象
        :raises AuthException: API Key 不匹配时抛出
        """
        api_key = request.headers.get('X-Irrigation-Api-Key')
        if not api_key:
            raise AuthException(data='', message='缺少 X-Irrigation-Api-Key 请求头')
        if api_key != IrrigationConfig.irrigation_api_key:
            raise AuthException(data='', message='API Key 无效')


def irrigation_api_key_dependency() -> params.Depends:
    """
    灌溉接口 API Key 认证依赖工厂函数

    :return: Irrigation API Key 认证依赖
    """
    return Depends(IrrigationApiKey())


IrrigationApiKeyDependency = irrigation_api_key_dependency
