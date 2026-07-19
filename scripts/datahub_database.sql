-- ============================================================
-- datahub_database.sql
-- 东北农业大学 鹤北小流域/浓江农场 农业数据管理系统
-- PostgreSQL 数据库方案（后续可扩展 PostGIS）
-- ============================================================

-- 创建数据库（需单独执行，或在 psql 中手动创建）
-- CREATE DATABASE datahub WITH ENCODING 'UTF8';

-- 连接到 datahub 数据库后执行以下内容
-- \c datahub

-- ============================================================
-- 一、站点表
-- ============================================================

CREATE TABLE IF NOT EXISTS station (
    id          SERIAL PRIMARY KEY,
    stcd        VARCHAR(10)   NOT NULL UNIQUE,   -- 气象站编码
    name        VARCHAR(50)   NOT NULL,          -- 站点名称
    latitude    DECIMAL(8,4)  DEFAULT NULL,      -- 纬度
    longitude   DECIMAL(8,4)  DEFAULT NULL,      -- 经度
    altitude    DECIMAL(8,2)  DEFAULT NULL,      -- 海拔(m)
    description TEXT          DEFAULT NULL,
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE station IS '监测站信息';

-- 插入站点数据
INSERT INTO station (stcd, name, latitude, altitude) VALUES
    ('50557', '鹤北小流域', 49.16, 242.2),
    ('50873', '浓江农场',   46.47, 82.0)
ON CONFLICT (stcd) DO NOTHING;

-- ============================================================
-- 二、气象数据表（5+1 张）
-- ============================================================

-- 2.1 每日湿度
CREATE TABLE IF NOT EXISTS weather_humidity (
    id          BIGSERIAL PRIMARY KEY,
    stcd        VARCHAR(10)   NOT NULL,
    obs_date    DATE          NOT NULL,
    rh_mean     DECIMAL(12,4) DEFAULT NULL,      -- 日平均相对湿度(%)
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_humidity IS '每日相对湿度';

-- 2.2 每日降水
CREATE TABLE IF NOT EXISTS weather_precipitation (
    id              BIGSERIAL PRIMARY KEY,
    stcd            VARCHAR(10)   NOT NULL,
    obs_date        DATE          NOT NULL,
    precipitation   DECIMAL(12,4) DEFAULT NULL,  -- 日降水量(mm)
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_precipitation IS '每日降水量';

-- 2.3 每日日照
CREATE TABLE IF NOT EXISTS weather_sunshine (
    id              BIGSERIAL PRIMARY KEY,
    stcd            VARCHAR(10)   NOT NULL,
    obs_date        DATE          NOT NULL,
    sunshine_hours  DECIMAL(12,4) DEFAULT NULL,  -- 日照时数(h)
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_sunshine IS '每日日照时数';

-- 2.4 每日温度
CREATE TABLE IF NOT EXISTS weather_temperature (
    id          BIGSERIAL PRIMARY KEY,
    stcd        VARCHAR(10)   NOT NULL,
    obs_date    DATE          NOT NULL,
    tmax        DECIMAL(12,4) DEFAULT NULL,      -- 日最高温度(℃)
    tmin        DECIMAL(12,4) DEFAULT NULL,      -- 日最低温度(℃)
    tmean       DECIMAL(12,4) DEFAULT NULL,      -- 日平均温度(℃)
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_temperature IS '每日温度';

-- 2.5 每日风速
CREATE TABLE IF NOT EXISTS weather_wind (
    id          BIGSERIAL PRIMARY KEY,
    stcd        VARCHAR(10)   NOT NULL,
    obs_date    DATE          NOT NULL,
    wind_speed  DECIMAL(12,4) DEFAULT NULL,      -- 日平均风速(m/s)
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_wind IS '每日风速';

-- 2.6 每日ET0蒸散量（浓江）
CREATE TABLE IF NOT EXISTS weather_et0 (
    id          BIGSERIAL PRIMARY KEY,
    stcd        VARCHAR(10)   NOT NULL,
    obs_date    DATE          NOT NULL,
    tmean       DECIMAL(6,2)  DEFAULT NULL,      -- 日平均温度(℃)
    precip      DECIMAL(8,2)  DEFAULT NULL,      -- 日降水量(mm)
    et0         DECIMAL(10,6) DEFAULT NULL,      -- 参考蒸散量ET0(mm/d)
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (stcd, obs_date)
);

COMMENT ON TABLE weather_et0 IS '每日ET0参考蒸散量';

-- ============================================================
-- 三、土壤数据表（5 张）
-- ============================================================

-- 3.1 土壤水文参数（k/k1/k2 合并）
CREATE TABLE IF NOT EXISTS soil_parameter (
    id                              BIGSERIAL PRIMARY KEY,
    source                          VARCHAR(10)   NOT NULL,  -- k / k1 / k2
    fid                             INTEGER       DEFAULT NULL,
    grid_id                         INTEGER       DEFAULT NULL,
    grid_no                         INTEGER       DEFAULT NULL,
    crop                            INTEGER       DEFAULT NULL,
    oc_0_5                          DECIMAL(12,4) DEFAULT NULL,  -- 有机碳
    sand_0_5                        DECIMAL(12,4) DEFAULT NULL,  -- 砂粒
    clay_0_5                        DECIMAL(12,4) DEFAULT NULL,  -- 粘粒
    silt_0_5                        DECIMAL(12,4) DEFAULT NULL,  -- 粉粒
    bulk_density                    DECIMAL(16,4) DEFAULT NULL,  -- 容重
    k_value                         DECIMAL(12,6) DEFAULT NULL,  -- K值
    moisture_content                DECIMAL(16,4) DEFAULT NULL,  -- 含水量
    saturated_moisture_content      DECIMAL(16,6) DEFAULT NULL,  -- 饱和含水量
    saturated_matrix_potential      DECIMAL(12,6) DEFAULT NULL,  -- 饱和基质势
    campbell                        DECIMAL(12,5) DEFAULT NULL,  -- Campbell参数
    field_capacity                  DECIMAL(16,6) DEFAULT NULL,  -- 田间持水量
    wilting_coefficient             DECIMAL(16,6) DEFAULT NULL,  -- 凋萎系数
    saturated_hydraulic_conductivity DECIMAL(12,6) DEFAULT NULL, -- 饱和导水率
    thermal_conductivity            DECIMAL(16,6) DEFAULT NULL,  -- 热导率
    specific_heat_capacity          DECIMAL(16,6) DEFAULT NULL,  -- 比热容
    steady_state_infiltration_rate  DECIMAL(12,6) DEFAULT NULL,  -- 稳渗率
    dem                             DECIMAL(10,6) DEFAULT NULL,  -- 高程
    created_at                      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE soil_parameter IS '土壤水文参数(k/k1/k2)';
CREATE INDEX idx_soilparam_source ON soil_parameter (source);

-- 3.2 传感器监测数据（两个文件合并）
CREATE TABLE IF NOT EXISTS soil_sensor_monitor (
    id              BIGSERIAL PRIMARY KEY,
    device_name     VARCHAR(50)   NOT NULL,      -- 设备序列号(如 "2号-坡下")
    depth_cm        INTEGER       NOT NULL,      -- 监测深度(cm)
    temperature     DECIMAL(6,2)  DEFAULT NULL,  -- 温度(℃)
    humidity        DECIMAL(8,3)  DEFAULT NULL,  -- 湿度(%)
    conductivity    DECIMAL(10,2) DEFAULT NULL,  -- 电导率(μs/cm)
    obs_time        TIMESTAMP     NOT NULL,      -- 上报时间
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE soil_sensor_monitor IS '传感器监测数据(每2小时)';
CREATE INDEX idx_sensor_device_time ON soil_sensor_monitor (device_name, obs_time);
CREATE INDEX idx_sensor_time ON soil_sensor_monitor (obs_time);

-- 3.3 地温数据（日期×深度矩阵转置存储）
CREATE TABLE IF NOT EXISTS soil_ground_temperature (
    id              BIGSERIAL PRIMARY KEY,
    obs_date        DATE          NOT NULL,      -- 观测日期
    depth_cm        INTEGER       NOT NULL,      -- 深度(cm)
    temperature     DECIMAL(6,2)  DEFAULT NULL,  -- 地温(℃)
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (obs_date, depth_cm)
);

COMMENT ON TABLE soil_ground_temperature IS '分层地温(10-200cm)';

-- 3.4 分层含水量统计
CREATE TABLE IF NOT EXISTS soil_layer_stats (
    id              BIGSERIAL PRIMARY KEY,
    layer_depth     VARCHAR(20)   NOT NULL,      -- 土层深度(如 "0-10")
    max_value       DECIMAL(10,6) DEFAULT NULL,  -- 最大值
    min_value       DECIMAL(10,6) DEFAULT NULL,  -- 最小值
    mean_value      DECIMAL(10,6) DEFAULT NULL,  -- 均值
    std_dev         DECIMAL(10,6) DEFAULT NULL,  -- 标准偏差
    cv              DECIMAL(10,6) DEFAULT NULL,  -- 变异系数
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE soil_layer_stats IS '各土层含水量统计';

-- 3.5 监测点黑土厚度
CREATE TABLE IF NOT EXISTS soil_thickness (
    id              BIGSERIAL PRIMARY KEY,
    point_id        VARCHAR(20)   NOT NULL,      -- 监测点编号
    point_x         DECIMAL(12,6) NOT NULL,      -- 经度
    point_y         DECIMAL(12,6) NOT NULL,      -- 纬度
    black_soil_depth_cm INTEGER   NOT NULL,      -- 黑土厚度(cm)
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE soil_thickness IS '监测点黑土厚度';
-- 后续可添加: ALTER TABLE soil_thickness ADD COLUMN geom geometry(Point, 4326);

-- ============================================================
-- 四、作物数据表（1 张）
-- ============================================================

CREATE TABLE IF NOT EXISTS crop_leaf_area (
    id              BIGSERIAL PRIMARY KEY,
    plot            VARCHAR(20)   NOT NULL,      -- 小区编号(如 "d2-1-2")
    obs_date        VARCHAR(10)   DEFAULT NULL,  -- 观测日期(月.日格式)
    plant_no        INTEGER       DEFAULT NULL,  -- 植株序号
    density         INTEGER       DEFAULT NULL,  -- 密度(株)
    leaf_area_1     DECIMAL(10,6) DEFAULT NULL,  -- 叶面积值1
    leaf_area_2     DECIMAL(10,6) DEFAULT NULL,  -- 叶面积值2
    leaf_area_3     DECIMAL(10,6) DEFAULT NULL,  -- 叶面积值3
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE crop_leaf_area IS '大豆叶面积指数';

-- ============================================================
-- 五、辅助表（涝渍地、试验小区、空间/文件资产索引）
-- ============================================================

-- 5.1 试验小区概况（键值对结构）
CREATE TABLE IF NOT EXISTS experiment_plot_info (
    id              SERIAL PRIMARY KEY,
    param_name      VARCHAR(50)   NOT NULL,      -- 参数名称
    param_value     TEXT          NOT NULL,      -- 参数值
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE experiment_plot_info IS '试验小区概况';

-- 5.2 涝渍地面积统计（原始数据为多子表，存为 JSONB 保持灵活性）
CREATE TABLE IF NOT EXISTS waterlogging_stats (
    id              BIGSERIAL PRIMARY KEY,
    region_name     VARCHAR(50)   NOT NULL,      -- 区域名称
    region_area_ha  DECIMAL(12,6) DEFAULT NULL,  -- 区域面积(公顷)
    count           INTEGER       DEFAULT NULL,  -- 涝渍地数量(个)
    total_area_ha   DECIMAL(12,6) DEFAULT NULL,  -- 涝渍地总面积(公顷)
    area_ratio_pct  DECIMAL(8,6)  DEFAULT NULL,  -- 面积占比(%)
    avg_slope       DECIMAL(8,5)  DEFAULT NULL,  -- 平均坡度(°)
    extra_data      JSONB         DEFAULT NULL,  -- 其他子表数据
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE waterlogging_stats IS '涝渍地面积统计';

-- 5.3 土壤水分地温监测清单
CREATE TABLE IF NOT EXISTS soil_monitor_log (
    id              BIGSERIAL PRIMARY KEY,
    seq_no          INTEGER       DEFAULT NULL,  -- 序号
    obs_date        DATE          DEFAULT NULL,  -- 监测日期
    depth_desc      VARCHAR(20)   DEFAULT NULL,  -- 监测深度描述
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE soil_monitor_log IS '土壤水分地温监测试验清单';

-- 5.4 数据资产索引（GeoTIFF/Shapefile 等非表格文件先登记元数据，原始文件保留在文件系统）
CREATE TABLE IF NOT EXISTS data_asset (
    id                BIGSERIAL PRIMARY KEY,
    asset_type        VARCHAR(20)   NOT NULL,      -- raster / vector / file
    data_category     VARCHAR(50)   DEFAULT NULL,  -- 气象数据 / 自然地理数据 / 土壤数据 / 作物数据
    region_name       VARCHAR(50)   DEFAULT NULL,  -- 鹤北小流域 / 浓江农场
    asset_name        VARCHAR(200)  NOT NULL,      -- 数据名称
    variable_name     VARCHAR(50)   DEFAULT NULL,  -- RAIN / WIND / DEM / 土地利用等
    obs_date          DATE          DEFAULT NULL,  -- 逐日栅格日期
    file_format       VARCHAR(20)   NOT NULL,      -- tif / shp 等
    relative_path     TEXT          NOT NULL UNIQUE,
    original_filename VARCHAR(255)  DEFAULT NULL,  -- 用户上传时的原始文件名
    storage_path      TEXT          DEFAULT NULL,  -- 受管上传根下的实际存储路径
    size_bytes        BIGINT        DEFAULT NULL,
    checksum          VARCHAR(64)   DEFAULT NULL,  -- SHA-256 文件校验和
    source_type       VARCHAR(20)   NOT NULL DEFAULT 'import', -- import / upload
    upload_user_id    BIGINT        DEFAULT NULL,  -- 上传用户ID
    crs               TEXT          DEFAULT NULL,
    bbox              JSONB         DEFAULT NULL,  -- {"minx":..,"miny":..,"maxx":..,"maxy":..}
    raster_width      INTEGER       DEFAULT NULL,
    raster_height     INTEGER       DEFAULT NULL,
    raster_count      INTEGER       DEFAULT NULL,
    raster_dtype      VARCHAR(50)   DEFAULT NULL,
    resolution_x      DOUBLE PRECISION DEFAULT NULL,
    resolution_y      DOUBLE PRECISION DEFAULT NULL,
    nodata_value      DOUBLE PRECISION DEFAULT NULL,
    extra_metadata    JSONB         DEFAULT NULL,  -- Shapefile 组件、读取错误、驱动等扩展信息
    created_at        TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP     NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMP     DEFAULT NULL   -- 软删除时间戳
);

COMMENT ON TABLE data_asset IS '非表格空间/文件数据资产索引';

-- ============================================================
-- 六、索引
-- ============================================================

CREATE INDEX idx_humidity_date       ON weather_humidity (obs_date);
CREATE INDEX idx_humidity_stcd       ON weather_humidity (stcd);
CREATE INDEX idx_precip_date         ON weather_precipitation (obs_date);
CREATE INDEX idx_precip_stcd         ON weather_precipitation (stcd);
CREATE INDEX idx_sunshine_date       ON weather_sunshine (obs_date);
CREATE INDEX idx_sunshine_stcd       ON weather_sunshine (stcd);
CREATE INDEX idx_temp_date           ON weather_temperature (obs_date);
CREATE INDEX idx_temp_stcd           ON weather_temperature (stcd);
CREATE INDEX idx_wind_date           ON weather_wind (obs_date);
CREATE INDEX idx_wind_stcd           ON weather_wind (stcd);
CREATE INDEX idx_et0_date            ON weather_et0 (obs_date);
CREATE INDEX idx_et0_stcd            ON weather_et0 (stcd);
CREATE INDEX idx_ground_temp_date    ON soil_ground_temperature (obs_date);
CREATE INDEX idx_thickness_point     ON soil_thickness (point_id);
CREATE INDEX idx_data_asset_type     ON data_asset (asset_type);
CREATE INDEX idx_data_asset_category ON data_asset (data_category);
CREATE INDEX idx_data_asset_region   ON data_asset (region_name);
CREATE INDEX idx_data_asset_variable ON data_asset (variable_name);
CREATE INDEX idx_data_asset_date     ON data_asset (obs_date);
CREATE INDEX idx_data_asset_source   ON data_asset (source_type);
CREATE INDEX idx_data_asset_deleted  ON data_asset (deleted_at);
CREATE INDEX idx_data_asset_checksum ON data_asset (checksum);

-- ------------------------------------------------------------
-- 灌区分区基础数据
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agri_irrigation_zone (
    id BIGSERIAL PRIMARY KEY,
    irrigation_area_code VARCHAR(64) NOT NULL DEFAULT 'chahayang',
    irrigation_area_name VARCHAR(100) NOT NULL DEFAULT '查哈阳灌区',
    zone_id VARCHAR(32) NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    land_area NUMERIC(14, 4) NOT NULL,
    surface_water_available NUMERIC(18, 4) NOT NULL DEFAULT 0,
    groundwater_available NUMERIC(18, 4) NOT NULL DEFAULT 0,
    min_area NUMERIC(14, 4),
    max_area NUMERIC(14, 4),
    sort_order NUMERIC(8, 0) NOT NULL DEFAULT 0,
    status VARCHAR(1) NOT NULL DEFAULT '0',
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE agri_irrigation_zone IS '灌区分区基础数据';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_area_code IS '灌区编码';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_area_name IS '灌区名称';
COMMENT ON COLUMN agri_irrigation_zone.status IS '状态（0启用 1停用）';
CREATE INDEX IF NOT EXISTS idx_agri_irrigation_zone_status ON agri_irrigation_zone (status);
CREATE INDEX IF NOT EXISTS idx_agri_irrigation_zone_sort ON agri_irrigation_zone (irrigation_area_code, sort_order, zone_id);
CREATE UNIQUE INDEX IF NOT EXISTS uk_agri_irrigation_zone_area_zone ON agri_irrigation_zone (irrigation_area_code, zone_id);

INSERT INTO agri_irrigation_zone (
    irrigation_area_code, irrigation_area_name, zone_id, zone_name, land_area, surface_water_available, groundwater_available,
    min_area, max_area, sort_order, status, remark
) VALUES
('chahayang', '查哈阳灌区', 'Z01', '红河', 2865.02, 36259380.0, 4696734.0, 2148.7650, 2865.02, 1, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z02', '万发', 3135.47, 39296070.0, 4873331.0, 2351.6025, 3135.47, 2, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z03', '金光', 3398.08, 41055570.0, 5091537.0, 2548.5600, 3398.08, 3, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z04', '稻花香', 3550.21, 30910780.0, 3833423.0, 2662.6575, 3550.21, 4, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z05', '发展', 2672.96, 44974950.0, 5877602.0, 2004.7200, 2672.96, 5, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z06', '金星', 3212.89, 39945480.0, 5253868.0, 2409.6675, 3212.89, 6, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z07', '太平湖', 1761.67, 43645990.0, 5412790.0, 1321.2525, 1761.67, 7, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z08', '海洋', 3889.15, 64301350.0, 8974380.0, 2916.8625, 3889.15, 8, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z09', '新立', 3454.23, 19992150.0, 2979341.0, 2590.6725, 3454.23, 9, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z10', '丰收', 3774.23, 37951930.0, 4006637.0, 2830.6725, 3774.23, 10, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z11', '二十八方', 5560.37, 26396760.0, 3273614.0, 4170.2775, 5560.37, 11, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z12', '联合', 1795.09, 42364060.0, 1153810.0, 1346.3175, 1795.09, 12, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z13', '金边', 2139.52, 7026099.0, 871347.0, 1604.6400, 2139.52, 13, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z14', '长吉岗', 5459.97, 33879440.0, 6701584.0, 4094.9775, 5459.97, 14, '0', '默认14分区')
ON CONFLICT (irrigation_area_code, zone_id) DO NOTHING;

-- ============================================================
-- 七、视图
-- ============================================================

-- 气象数据综合视图
CREATE OR REPLACE VIEW v_weather_daily AS
SELECT
    s.name          AS station_name,
    t.stcd,
    t.obs_date,
    t.tmax,
    t.tmin,
    t.tmean,
    h.rh_mean,
    p.precipitation,
    sun.sunshine_hours,
    w.wind_speed
FROM weather_temperature t
JOIN station s ON s.stcd = t.stcd
LEFT JOIN weather_humidity h
    ON h.stcd = t.stcd AND h.obs_date = t.obs_date
LEFT JOIN weather_precipitation p
    ON p.stcd = t.stcd AND p.obs_date = t.obs_date
LEFT JOIN weather_sunshine sun
    ON sun.stcd = t.stcd AND sun.obs_date = t.obs_date
LEFT JOIN weather_wind w
    ON w.stcd = t.stcd AND w.obs_date = t.obs_date;

-- 按站点统计数据量
CREATE OR REPLACE VIEW v_station_data_summary AS
SELECT
    s.name AS station_name,
    s.stcd,
    (SELECT COUNT(*) FROM weather_temperature WHERE stcd = s.stcd) AS temp_records,
    (SELECT COUNT(*) FROM weather_humidity WHERE stcd = s.stcd) AS humidity_records,
    (SELECT COUNT(*) FROM weather_precipitation WHERE stcd = s.stcd) AS precip_records,
    (SELECT COUNT(*) FROM weather_sunshine WHERE stcd = s.stcd) AS sunshine_records,
    (SELECT COUNT(*) FROM weather_wind WHERE stcd = s.stcd) AS wind_records
FROM station s;

-- ============================================================
-- 完成
-- ============================================================
