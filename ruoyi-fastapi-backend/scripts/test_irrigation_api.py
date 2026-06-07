import argparse
import json
import mimetypes
from pathlib import Path

import requests


DEFAULT_URL = 'http://8.146.227.98/api/v1/irrigation/predict'
DEFAULT_API_KEY = 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
DEFAULT_WEATHER_DIR = DEFAULT_DATA_DIR / 'weather_files'
DEFAULT_OBSERVED_SM_DIR = DEFAULT_DATA_DIR / 'observed_sm'


def build_files(weather_dir: Path, observed_sm_dir: Path | None):
    files = []

    weather_files = sorted(
        [p for p in weather_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.tif', '.tiff'}]
    )
    if not weather_files:
        raise ValueError(f'weather_dir 下未找到 tif 文件: {weather_dir}')

    for path in weather_files:
        content_type = mimetypes.guess_type(path.name)[0] or 'image/tiff'
        files.append(('weather_files', (path.name, path.open('rb'), content_type)))

    if observed_sm_dir:
        observed_files = sorted(
            [p for p in observed_sm_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.tif', '.tiff'}]
        )
        for path in observed_files:
            content_type = mimetypes.guess_type(path.name)[0] or 'image/tiff'
            files.append(('observed_sm', (path.name, path.open('rb'), content_type)))

    return files


def parse_filename(response: requests.Response) -> str:
    content_disposition = response.headers.get('Content-Disposition', '')
    marker = 'filename='
    if marker in content_disposition:
        return content_disposition.split(marker, 1)[1].strip('"')
    return 'irrigation_prediction.zip'


def main():
    parser = argparse.ArgumentParser(description='测试灌溉决策接口并下载返回的 ZIP 文件')
    parser.add_argument('--api-key', default=DEFAULT_API_KEY, help='接口请求头 X-Irrigation-Api-Key')
    parser.add_argument('--weather-dir', default=str(DEFAULT_WEATHER_DIR), help='天气 TIF 文件目录')
    parser.add_argument('--start-date', required=True, help='起始日期，格式 YYYY-MM-DD')
    parser.add_argument('--output', default='irrigation_result.zip', help='输出 ZIP 文件路径')
    parser.add_argument('--url', default=DEFAULT_URL, help='接口地址')
    parser.add_argument('--initial-sm', type=float, default=0.29, help='初始土壤含水量')
    parser.add_argument('--sm-threshold', type=float, default=0.32, help='土壤水分阈值')
    parser.add_argument('--observed-sm-dir', default=str(DEFAULT_OBSERVED_SM_DIR), help='可选，实测土壤含水量 TIF 目录')
    args = parser.parse_args()

    weather_dir = Path(args.weather_dir)
    observed_sm_dir = Path(args.observed_sm_dir) if args.observed_sm_dir else None
    if observed_sm_dir and not observed_sm_dir.exists():
        observed_sm_dir = None

    files = build_files(weather_dir, observed_sm_dir)
    data = {
        'start_date': args.start_date,
        'initial_sm': str(args.initial_sm),
        'sm_threshold': str(args.sm_threshold),
    }
    headers = {
        'X-Irrigation-Api-Key': args.api_key,
    }

    try:
        response = requests.post(args.url, headers=headers, data=data, files=files, timeout=600)

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                payload = response.json()
            except json.JSONDecodeError:
                print('请求失败，返回内容不是有效 JSON：')
                print(response.text)
                return
            print('请求失败：')
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        response.raise_for_status()
        output_path = Path(args.output)
        if output_path.is_dir():
            output_path = output_path / parse_filename(response)

        output_path.write_bytes(response.content)
        print(f'请求成功，结果已保存到: {output_path.resolve()}')
        print(f'HTTP 状态码: {response.status_code}')
        print(f'Content-Type: {content_type}')
    finally:
        for _, file_tuple in files:
            file_tuple[1].close()


if __name__ == '__main__':
    main()
