# 数据资产管理

## 概述

数据资产模块管理非表格空间文件（GeoTIFF、Shapefile），提供列表浏览、上传、下载和删除功能。模块与表格数据导入管道共存，不替换现有导入流程。

## 文件来源分类

| 来源 | source_type | 文件位置 | 删除策略 |
|------|-------------|----------|----------|
| 脚本导入 | import | `data/`（挂载目录） | 仅软删除，不删物理文件 |
| 用户上传 | upload | `data_assets/YYYY/MM/DD/` | 软删除 + 删除物理文件 |
| 灌溉预测 | — | 不在本模块管理范围 | — |

## 支持的文件类型

- **GeoTIFF**（`.tif`、`.tiff`）：单文件上传，自动提取 CRS、边界框、分辨率、波段等元数据。
- **Shapefile ZIP**（`.zip`）：包含一个 `.shp` 主文件及 `.shx`、`.dbf`、`.prj` 等配套文件的压缩包。要求 ZIP 中恰好有一个 `.shp`，不允许多个或缺失。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agriculture/dataAsset/list` | 分页列表，支持多条件筛选 |
| GET | `/agriculture/dataAsset/{id}` | 资产详情 |
| POST | `/agriculture/dataAsset/upload` | 上传文件（multipart/form-data） |
| GET | `/agriculture/dataAsset/download/{id}` | 按 ID 下载文件 |
| DELETE | `/agriculture/dataAsset/{ids}` | 批量删除（逗号分隔 ID） |

## 上传流程

1. 前端选择 `.tif`/`.tiff` 或 `.zip` 文件，携带可选的 `dataCategory`、`regionName`、`variableName` 表单字段。
2. 后端验证文件名安全性和扩展名。
3. 流式写入 `data_assets/YYYY/MM/DD/{uuid}.ext`，同时计算 SHA-256。
4. 若为 ZIP，验证 Shapefile 结构（单 `.shp`、无路径穿越）。
5. 提取空间元数据（rasterio/fiona），失败时降级为 `metadata_error`。
6. 写入 `data_asset` 表，`source_type = upload`。

## 删除策略

- `source_type = import`：设置 `deleted_at` 时间戳，物理文件保留在 `data/` 目录。
- `source_type = upload`：设置 `deleted_at`，且物理文件位于 `data_assets/` 下时同步删除。
- 任何情况下不删除 `data_assets/` 以外的文件。

## 恢复软删除

若误删导入记录，可直接清除 `deleted_at` 字段恢复：

```sql
UPDATE data_asset SET deleted_at = NULL WHERE id = <id>;
```

## 重新索引

已有文件可通过脚本重新索引：

```bash
python3 scripts/import_data.py --data-dir ./data --only asset ...
```

## Docker 部署注意事项

`data_assets/` 目录需通过 volume 挂载持久化：

```yaml
volumes:
  - ./data_assets:/app/data_assets
```

## 元数据字段说明

| 字段 | 说明 |
|------|------|
| asset_type | raster / vector / file |
| data_category | 气象数据 / 自然地理数据 / 土壤数据 / 作物数据 |
| region_name | 鹤北小流域 / 浓江农场 |
| variable_name | RAIN / WIND / DEM / 土地利用 等 |
| obs_date | 时间序列栅格的观测日期 |
| crs | 坐标参考系字符串 |
| bbox | 边界框 {minx, miny, maxx, maxy} |
| extra_metadata | Shapefile 组件列表、驱动信息、读取错误等 |
