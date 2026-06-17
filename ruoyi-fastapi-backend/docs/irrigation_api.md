# 灌溉决策接口文档

## 接口说明
用于根据未来 15 天气象栅格数据，生成未来 15 天的：
- 灌溉量 GeoTIFF
- 土壤含水量 GeoTIFF

接口返回一个 ZIP 压缩包，内含全部结果文件。

## 部署地址
- 服务器：`http://8.146.227.98`
- 接口：`POST /api/v1/irrigation/predict`
- 完整地址：`http://8.146.227.98/api/v1/irrigation/predict`

如果你的服务实际启用了 HTTPS 或反向代理端口，请把上面的域名替换为实际访问地址。

## 认证方式
请求头必须携带：

- `X-Irrigation-Api-Key: irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY`

未传或错误时会返回认证失败信息。

## 请求方式
`multipart/form-data`

## 请求参数

### 1）表单字段

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 预测起始日期，格式：`YYYY-MM-DD` |
| `initial_sm` | float | 否 | 初始土壤含水量，默认 `0.29` |
| `sm_threshold` | float | 否 | 土壤水分阈值，默认 `0.32` |

### 2）文件字段

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `weather_files` | file[] | 是 | 未来 15 天气象 TIF 文件，一次性上传 |
| `observed_sm` | file[] | 否 | 实测土壤含水量 TIF 文件 |

## weather_files 文件要求
`weather_files` 需要一次性上传未来 15 天、共 7 类气象变量的 GeoTIFF 文件。

常见变量包括：
- `irrad`
- `tmax`
- `tmin`
- `vap`
- `wind`
- `rain`
- `et0`

通常应为：
- 15 天 × 7 类变量 = 105 个文件

注意：文件命名需要符合后端固定命名规则，否则会解析失败。

## 成功响应
- HTTP 状态码：`200`
- `Content-Type: application/zip`
- 响应体：ZIP 二进制文件

### ZIP 文件名示例
```text
irrigation_prediction_2026-06-01.zip
```

### ZIP 内容示例
```text
irrigation/
  Irrigation_2026-06-01.tif
  Irrigation_2026-06-02.tif
  ...
soil_moisture/
  SM_2026-06-01.tif
  SM_2026-06-02.tif
  ...
```

## 失败响应
失败时通常返回 JSON，常见字段为 `msg`。

### 1）缺少 API Key
```json
{
  "code": 401,
  "msg": "缺少 X-Irrigation-Api-Key 请求头"
}
```

### 2）API Key 无效
```json
{
  "code": 401,
  "msg": "API Key 无效"
}
```

### 3）未上传 weather_files
```json
{
  "code": 500,
  "msg": "未收到 weather_files 文件，请检查前端是否正确提交 multipart/form-data"
}
```

### 4）参数或文件命名不合法
```json
{
  "code": 500,
  "msg": "具体错误信息"
}
```

## cURL 调用示例
```bash
curl -X POST "http://8.146.227.98/api/v1/irrigation/predict" \
  -H "X-Irrigation-Api-Key: irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY" \
  -F "start_date=2026-06-01" \
  -F "initial_sm=0.29" \
  -F "sm_threshold=0.32" \
  -F "weather_files=@./data/irrad_2026-06-01.tif" \
  -F "weather_files=@./data/tmax_2026-06-01.tif" \
  -F "weather_files=@./data/tmin_2026-06-01.tif"
```

实际使用时，请把全部 `weather_files` 文件都追加上传。

## 调用说明
1. 准备好符合命名规则的 15 天气象 TIF 文件。
2. 按 `multipart/form-data` 上传。
3. 接口返回 ZIP 文件后保存到本地。
4. 解压后查看 `irrigation/` 与 `soil_moisture/` 结果。
