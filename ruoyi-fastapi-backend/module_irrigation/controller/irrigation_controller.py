from typing import Annotated

from fastapi import File, Form, UploadFile
from fastapi.responses import FileResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from exceptions.exception import ServiceException
from module_irrigation.service.irrigation_service import IrrigationService
from utils.log_util import logger

irrigation_controller = APIRouterPro(
    prefix='/api/v1/irrigation',
    order_num=20,
    tags=['灌溉决策'],
    dependencies=[irrigation_api_key_dependency()],
)


@irrigation_controller.post(
    '/predict',
    summary='执行灌溉决策预测',
)
async def predict_irrigation(
    start_date: Annotated[str, Form(description='预测起始日期，格式 YYYY-MM-DD')],
    weather_files: Annotated[list[UploadFile], File(description='气象 TIF 文件（固定命名格式，需一次性上传 15×7 个）')],
    observed_sm: Annotated[list[UploadFile] | None, File(description='实测土壤含水量 TIF 文件（可选）')] = None,
    initial_sm: Annotated[float, Form(description='初始土壤含水量，默认 0.29')] = 0.29,
    sm_threshold: Annotated[float, Form(description='土壤水分阈值，默认 0.32')] = 0.32,
) -> FileResponse:
    """
    基于 LSTM 代理模型和 SAC 强化学习模型的水稻灌溉决策预测接口。
    一次性上传未来15天的气象数据，直接返回包含未来15天灌溉量和土壤含水量 TIF 的 ZIP 文件。
    """
    uploaded_files = {
        'weather_files': [(f.filename, await f.read()) for f in weather_files],
    }
    logger.info(
        'irrigation predict request parsed: start_date={}, weather_files={}, observed_sm={}, first_weather_names={}',
        start_date,
        len(uploaded_files['weather_files']),
        len(observed_sm or []),
        [name for name, _ in uploaded_files['weather_files'][:5]],
    )
    if not uploaded_files['weather_files']:
        raise ServiceException(message='未收到 weather_files 文件，请检查前端是否正确提交 multipart/form-data')
    if observed_sm:
        uploaded_files['observed_sm'] = [(f.filename, await f.read()) for f in observed_sm]

    zip_path, zip_filename = await IrrigationService.run_prediction(
        uploaded_files=uploaded_files,
        start_date=start_date,
        initial_sm=initial_sm,
        sm_threshold=sm_threshold,
    )

    return FileResponse(
        path=zip_path,
        filename=zip_filename,
        media_type='application/zip',
    )
