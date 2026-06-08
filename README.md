<h1 align="center">DataHub</h1>
<h4 align="center">农业数据管理平台</h4>
<p align="center">
    <img alt="python version" src="https://img.shields.io/badge/python-≥3.10-blue">
    <img alt="node version" src="https://img.shields.io/badge/node-≥18-blue">
    <img alt="MySQL version" src="https://img.shields.io/badge/MySQL-≥5.7-blue">
    <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-supported-blue">
    <img alt="redis version" src="https://img.shields.io/badge/redis-≥6.2-blue">
    <img alt="LICENSE" src="https://img.shields.io/github/license/mashape/apistatus.svg">
</p>

## 项目简介

DataHub 是一个面向农业科研场景的数据管理平台，用于集中管理作物监测、气象观测、土壤传感器等多源农业数据。平台提供数据录入、查询、统计分析和可视化展示功能，同时内置完整的后台管理系统（用户、角色、权限、日志等），支持 Web 端和移动端访问。

基于 [RuoYi-Vue3-FastAPI](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI) 开发框架构建。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 (async) + Pydantic |
| 数据库 | MySQL 5.7+ / PostgreSQL |
| 缓存 | Redis 6.2+ |
| 认证 | OAuth2 + JWT |
| 前端框架 | Vue 3 + Vite + Element Plus |
| 移动端 | uni-app (Vue 3)，支持 H5 / 微信小程序等多端 |
| AI 集成 | OpenAI、Anthropic、Google GenAI、Ollama 等多模型支持 |
| 任务调度 | APScheduler |
| 部署 | Docker Compose |

## 项目结构

```
datahub/
├── ruoyi-fastapi-backend/       # 后端 (FastAPI)
│   ├── module_admin/            # 系统管理模块（用户、角色、菜单、日志等）
│   ├── module_agriculture/      # 农业数据模块（核心业务）
│   ├── module_ai/               # AI 模型管理与对话
│   ├── module_generator/        # 代码生成器
│   ├── module_task/             # 定时任务
│   ├── common/                  # 公共组件（装饰器、中间件、工具类）
│   ├── config/                  # 配置（数据库、Redis、环境变量）
│   ├── sql/                     # 数据库初始化脚本
│   └── alembic/                 # 数据库迁移
├── ruoyi-fastapi-frontend/      # Web 前端 (Vue 3 + Element Plus)
├── ruoyi-fastapi-app/           # 移动端 (uni-app)
├── ruoyi-fastapi-test/          # E2E 测试 (Playwright)
├── scripts/                     # 工具脚本（数据导入、菜单初始化）
├── docker-compose.my.yml        # Docker 部署 (MySQL 版)
└── docker-compose.pg.yml        # Docker 部署 (PostgreSQL 版)
```

## 核心功能

### 农业数据管理

- **作物监测** — 大豆叶面积指数等作物生长数据管理
- **气象数据** — 气温、湿度、降水量等气象站观测数据
- **土壤监测** — 传感器实时数据（温度、湿度、电导率，每2小时采集）
- **土壤参数** — 水文参数（有机碳、砂/黏/粉粒含量、水力传导率等）
- **地温数据** — 多层地温监测（10-200cm）
- **黑土厚度** — 黑土层厚度监测
- **监测站管理** — 气象站/监测点信息维护
- **数据看板** — 农业数据可视化仪表盘

### 系统管理

用户管理、角色管理、菜单管理、部门管理、岗位管理、字典管理、参数管理、通知公告、操作日志、登录日志、在线用户、定时任务、服务监控、缓存监控、传输加密

### 开发工具

代码生成器、在线表单构建、系统接口文档（Swagger）

### AI 功能

AI 模型管理、多模型对话（支持 OpenAI / Anthropic / Google / Ollama 等）

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- MySQL >= 5.7 或 PostgreSQL
- Redis >= 6.2

### 后端

```bash
cd ruoyi-fastapi-backend

# 安装依赖（MySQL）
pip install -r requirements.txt
# 或 PostgreSQL
pip install -r requirements-pg.txt

# 配置数据库和 Redis
# 编辑 .env.dev 文件

# 初始化数据库
# 1. 创建数据库 ruoyi-fastapi
# 2. 执行 sql/ruoyi-fastapi.sql（MySQL）或 sql/ruoyi-fastapi-pg.sql（PostgreSQL）
# 3. 执行 scripts/datahub_database.sql（农业数据表与数据资产索引表）
# 4. 执行 scripts/menu_insert.sql（农业模块菜单）

# 启动
python app.py --env=dev
```

### 农业数据导入

```bash
# 导入表格数据和非表格空间数据资产索引
python3 scripts/import_data.py --data-dir ./data --host localhost --port 15432 --user postgres --password root --db ruoyi-fastapi

# 只登记 GeoTIFF/Shapefile 等非表格空间数据资产
python3 scripts/import_data.py --data-dir ./data --host localhost --port 15432 --user postgres --password root --db ruoyi-fastapi --only asset
```

非表格空间数据采用“原始文件保留在 `data/`，数据库登记 `data_asset` 元数据索引”的方式。GeoTIFF 会登记坐标系、范围、分辨率、变量名和日期；Shapefile 会登记主文件及配套组件。若后续需要将 Shapefile 几何写入数据库，需要把 PostgreSQL 环境升级为 PostGIS 后再扩展几何入库流程。

### 前端

```bash
cd ruoyi-fastapi-frontend

npm install --registry=https://registry.npmmirror.com

npm run dev
```

### 移动端

```bash
cd ruoyi-fastapi-app

pnpm install

# H5
pnpm dev:h5

# 微信小程序
pnpm dev:mp-weixin
```

### 访问

- Web 端：http://localhost:80
- 默认账号：`admin` / `admin123`

## Docker 部署

> **注意：** PostgreSQL 版本会使用 `pgdata/`、`redisdata/` 做本地持久化；农业 TIF/Shapefile 等大文件不进入 Git，通过 `NEAU_DATA_DIR` 挂载到后端容器的 `/app/data`。

```bash
# MySQL 版本
docker compose -f docker-compose.my.yml up -d --build

# PostgreSQL 版本
cp .env.example .env
# 按服务器实际数据目录调整 NEAU_DATA_DIR，例如：
# NEAU_DATA_DIR=/root/workspace/neau-data-hub/data
docker compose -f docker-compose.pg.yml up -d --build
```

### PostgreSQL 版重新初始化与数据导入

如果当前 Docker 数据库没有需要保留的数据，可以删除旧容器和 `pgdata/` 后重新初始化，启动时会自动执行 `ruoyi-fastapi-pg.sql`、`scripts/datahub_database.sql` 和 `scripts/menu_insert.sql`：

```bash
docker compose -f docker-compose.pg.yml down
rm -rf pgdata redisdata
docker compose -f docker-compose.pg.yml up -d --build
```

容器启动后，可在后端容器内导入表格数据并登记 TIF/Shapefile 资产索引：

```bash
docker exec -it ruoyi-backend-pg python /app/datahub_scripts/import_data.py \
  --data-dir /app/data \
  --host ruoyi-pg \
  --port 5432 \
  --user postgres \
  --password root \
  --db ruoyi-fastapi
```

如果只需要登记 TIF/Shapefile 等非表格空间资产：

```bash
docker exec -it ruoyi-backend-pg python /app/datahub_scripts/import_data.py \
  --data-dir /app/data \
  --host ruoyi-pg \
  --port 5432 \
  --user postgres \
  --password root \
  --db ruoyi-fastapi \
  --only asset
```

## 生产构建

```bash
# 前端构建
cd ruoyi-fastapi-frontend
npm run build:prod

# 后端运行
cd ruoyi-fastapi-backend
# 编辑 .env.prod 配置生产环境数据库和 Redis
python app.py --env=prod
```

## 项目特性

- **全异步架构** — 后端基于 FastAPI + SQLAlchemy async，高并发性能
- **多数据库支持** — 同时支持 MySQL 和 PostgreSQL
- **多终端** — Web + 移动端（H5/微信小程序等）
- **传输加密** — 支持请求/响应加密、公钥轮换
- **日志脱敏** — 敏感数据自动脱敏
- **接口限流** — 装饰器方式实现接口限流
- **接口缓存** — ApiCache/ApiCacheEvict 装饰器
- **代码生成** — 一键生成前后端 CRUD 代码
- **AI 集成** — 多模型对话能力

## 相关文档

- 传输层加解密配置：[ruoyi-fastapi-backend/docs/transport_crypto_config.md](./ruoyi-fastapi-backend/docs/transport_crypto_config.md)
- 移动端开发文档：[ruoyi-fastapi-app/README.md](./ruoyi-fastapi-app/README.md)

## 致谢

- [RuoYi-Vue3-FastAPI](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI) — 基础开发框架
- [RuoYi-Vue3](https://github.com/yangzongzhuan/RuoYi-Vue3) — 前端参考
- [RuoYi-App](https://github.com/yangzongzhuan/RuoYi-App) — 移动端参考

## License

[MIT](./LICENSE)
