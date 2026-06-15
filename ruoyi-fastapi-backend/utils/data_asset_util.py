from __future__ import annotations

import math
import os
import re
import tempfile
import zipfile
from datetime import datetime

RASTER_EXTS = {'.tif', '.tiff'}
VECTOR_EXTS = {'.shp'}
SHAPEFILE_SIDECAR_EXTS = {
    '.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.xml',
}
SUPPORTED_UPLOAD_EXTS = {'.tif', '.tiff', '.zip'}
KNOWN_REGIONS = {'鹤北小流域', '浓江农场'}


def normalize_rel_path(path: str) -> str:
    return path.replace(os.sep, '/')


def clean_float(val):
    if val is None:
        return None
    try:
        fval = float(val)
    except (TypeError, ValueError):
        return None
    return fval if math.isfinite(fval) else None


def first_matching_part(parts: list[str], names: set[str]) -> str | None:
    for part in parts:
        if part in names:
            return part
    return None


def parse_date_from_stem(stem: str):
    weather_raster = re.match(r'^([A-Za-z][A-Za-z0-9]*|radiationNet)_(\d{4}-\d{2}-\d{2})$', stem)
    if weather_raster:
        try:
            return weather_raster.group(1), datetime.strptime(weather_raster.group(2), '%Y-%m-%d').date()
        except ValueError:
            pass
    return None, None


def classify_asset_path(data_dir: str, filepath: str) -> dict:
    rel_path = normalize_rel_path(os.path.relpath(filepath, data_dir))
    parts = rel_path.split('/')
    filename = os.path.basename(filepath)
    stem, ext = os.path.splitext(filename)
    lower_ext = ext.lower()

    data_category = parts[0] if parts else None
    region_name = first_matching_part(parts, KNOWN_REGIONS)
    asset_type = 'raster' if lower_ext in RASTER_EXTS else 'vector' if lower_ext in VECTOR_EXTS else 'file'
    asset_name = stem
    variable_name = None
    obs_date = None

    var_from_stem, date_from_stem = parse_date_from_stem(stem)
    if var_from_stem:
        variable_name = var_from_stem
        obs_date = date_from_stem
        asset_name = os.path.basename(os.path.dirname(filepath))
    elif 'dem' in stem.lower():
        variable_name = 'DEM'
        asset_name = f'{region_name or ""}DEM'.strip()
    elif 'TDLY' in stem or '土地利用' in rel_path:
        variable_name = '土地利用'
        asset_name = '鹤北流域土地利用'
    elif '种植' in stem or '水稻' in stem:
        variable_name = '种植结构'
        asset_name = '浓江农场水稻种植分布'
    elif lower_ext in VECTOR_EXTS:
        variable_name = os.path.basename(os.path.dirname(filepath))

    return {
        'asset_type': asset_type,
        'data_category': data_category,
        'region_name': region_name,
        'asset_name': asset_name,
        'variable_name': variable_name,
        'obs_date': obs_date,
        'file_format': lower_ext.lstrip('.'),
        'relative_path': rel_path,
        'size_bytes': os.path.getsize(filepath) if os.path.exists(filepath) else None,
    }


def read_raster_metadata(filepath: str) -> dict:
    metadata = {
        'crs': None,
        'bbox': None,
        'raster_width': None,
        'raster_height': None,
        'raster_count': None,
        'raster_dtype': None,
        'resolution_x': None,
        'resolution_y': None,
        'nodata_value': None,
        'extra_metadata': {},
    }
    try:
        import rasterio
    except ImportError:
        metadata['extra_metadata']['metadata_warning'] = 'rasterio 未安装，未读取栅格空间元数据'
        return metadata

    try:
        with rasterio.open(filepath) as src:
            bounds = src.bounds
            metadata.update({
                'crs': src.crs.to_string() if src.crs else None,
                'bbox': {
                    'minx': clean_float(bounds.left),
                    'miny': clean_float(bounds.bottom),
                    'maxx': clean_float(bounds.right),
                    'maxy': clean_float(bounds.top),
                },
                'raster_width': src.width,
                'raster_height': src.height,
                'raster_count': src.count,
                'raster_dtype': src.dtypes[0] if src.dtypes else None,
                'resolution_x': clean_float(abs(src.res[0])) if src.res else None,
                'resolution_y': clean_float(abs(src.res[1])) if src.res else None,
                'nodata_value': clean_float(src.nodata),
                'extra_metadata': {
                    'driver': src.driver,
                    'transform': [clean_float(v) for v in list(src.transform)[:6]],
                },
            })
    except Exception as e:
        metadata['extra_metadata']['metadata_error'] = str(e)
    return metadata


def read_vector_metadata(filepath: str) -> dict:
    base, _ = os.path.splitext(filepath)
    dir_name = os.path.dirname(filepath)
    prefix = os.path.basename(base)
    components = []
    if os.path.isdir(dir_name):
        for name in sorted(os.listdir(dir_name)):
            candidate = os.path.join(dir_name, name)
            candidate_base, candidate_ext = os.path.splitext(candidate)
            is_direct_component = candidate_base == base and candidate_ext.lower() in SHAPEFILE_SIDECAR_EXTS
            is_metadata_component = name == f'{prefix}.shp.xml'
            if is_direct_component or is_metadata_component:
                components.append(name)

    metadata = {
        'crs': None,
        'bbox': None,
        'raster_width': None,
        'raster_height': None,
        'raster_count': None,
        'raster_dtype': None,
        'resolution_x': None,
        'resolution_y': None,
        'nodata_value': None,
        'extra_metadata': {
            'components': components,
            'component_count': len(components),
            'shapefile_stem': prefix,
        },
    }

    try:
        import fiona
    except ImportError:
        metadata['extra_metadata']['metadata_warning'] = 'fiona 未安装，未读取矢量空间元数据'
        return metadata

    try:
        with fiona.open(filepath) as src:
            bounds = src.bounds
            crs_text = src.crs_wkt
            if not crs_text and src.crs:
                import json
                crs_text = json.dumps(dict(src.crs), ensure_ascii=False)
            metadata.update({
                'crs': crs_text,
                'bbox': {
                    'minx': clean_float(bounds[0]),
                    'miny': clean_float(bounds[1]),
                    'maxx': clean_float(bounds[2]),
                    'maxy': clean_float(bounds[3]),
                },
            })
            metadata['extra_metadata'].update({
                'driver': src.driver,
                'feature_count': len(src),
                'schema': src.schema,
            })
    except Exception as e:
        metadata['extra_metadata']['metadata_error'] = str(e)

    return metadata


def build_asset_record(data_dir: str, filepath: str) -> dict:
    record = classify_asset_path(data_dir, filepath)
    ext = os.path.splitext(filepath)[1].lower()
    if ext in RASTER_EXTS:
        record.update(read_raster_metadata(filepath))
    elif ext in VECTOR_EXTS:
        record.update(read_vector_metadata(filepath))
    return record


def validate_shapefile_zip(zip_path: str) -> tuple[str, list[str]]:
    """Validate a Shapefile ZIP bundle.

    Returns (shp_name, member_list) on success.
    Raises ValueError with a descriptive message on failure.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError('上传文件不是有效的ZIP归档')

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        for member in members:
            normalized = member.replace('\\', '/')
            if normalized.startswith('/') or '..' in normalized:
                raise ValueError(f'ZIP中包含不安全路径: {member}')

        shp_files = [m for m in members if m.lower().endswith('.shp')]
        if not shp_files:
            raise ValueError('ZIP中未找到.shp主文件')
        if len(shp_files) > 1:
            raise ValueError(f'ZIP中包含多个.shp文件: {shp_files}')

        return shp_files[0], members


def extract_shapefile_zip(zip_path: str, target_dir: str) -> str:
    """Extract a validated Shapefile ZIP into target_dir.

    Returns the path to the .shp main file.
    """
    shp_name, members = validate_shapefile_zip(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in members:
            dest = os.path.join(target_dir, os.path.basename(member))
            with zf.open(member) as src, open(dest, 'wb') as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

    return os.path.join(target_dir, os.path.basename(shp_name))


def is_safe_filename(filename: str) -> bool:
    if not filename:
        return False
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    if filename.startswith('.'):
        return False
    return True


def is_supported_upload_extension(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in SUPPORTED_UPLOAD_EXTS
