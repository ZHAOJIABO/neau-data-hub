-- 灌区分区基础数据表与默认 14 分区（PostgreSQL，幂等）

CREATE TABLE IF NOT EXISTS agri_irrigation_zone (
    id BIGSERIAL PRIMARY KEY,
    irrigation_area_code VARCHAR(64) NOT NULL DEFAULT 'chahayang',
    irrigation_area_name VARCHAR(100) NOT NULL DEFAULT '查哈阳灌区',
    zone_id VARCHAR(32) NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    land_area NUMERIC(14, 4) NOT NULL,
    surface_water_available NUMERIC(18, 4) NOT NULL DEFAULT 0,
    groundwater_available NUMERIC(18, 4) NOT NULL DEFAULT 0,
    iwue NUMERIC(8, 4) NOT NULL DEFAULT 0,
    water_productivity_kg_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0,
    benefit_yuan_per_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0,
    irrigation_reliability NUMERIC(8, 4) NOT NULL DEFAULT 0,
    field_efficiency NUMERIC(8, 4) NOT NULL DEFAULT 0,
    surface_water_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0,
    groundwater_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0,
    groundwater_dependency NUMERIC(8, 4) NOT NULL DEFAULT 0,
    min_area NUMERIC(14, 4),
    max_area NUMERIC(14, 4),
    sort_order NUMERIC(8, 0) NOT NULL DEFAULT 0,
    status VARCHAR(1) NOT NULL DEFAULT '0',
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS id BIGSERIAL;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS irrigation_area_code VARCHAR(64) NOT NULL DEFAULT 'chahayang';
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS irrigation_area_name VARCHAR(100) NOT NULL DEFAULT '查哈阳灌区';
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS iwue NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS water_productivity_kg_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS benefit_yuan_per_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS irrigation_reliability NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS field_efficiency NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS surface_water_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS groundwater_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS groundwater_dependency NUMERIC(8, 4) NOT NULL DEFAULT 0;
UPDATE agri_irrigation_zone
SET irrigation_area_code = COALESCE(NULLIF(irrigation_area_code, ''), 'chahayang'),
    irrigation_area_name = COALESCE(NULLIF(irrigation_area_name, ''), '查哈阳灌区');

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'agri_irrigation_zone'
          AND c.contype = 'p'
          AND c.conname = 'agri_irrigation_zone_pkey'
    ) AND EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
        WHERE t.relname = 'agri_irrigation_zone'
          AND i.indisprimary
          AND a.attname = 'zone_id'
    ) THEN
        ALTER TABLE agri_irrigation_zone DROP CONSTRAINT agri_irrigation_zone_pkey;
        ALTER TABLE agri_irrigation_zone ADD PRIMARY KEY (id);
    END IF;
END $$;

COMMENT ON TABLE agri_irrigation_zone IS '灌区分区基础数据';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_area_code IS '灌区编码';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_area_name IS '灌区名称';
COMMENT ON COLUMN agri_irrigation_zone.status IS '状态（0启用 1停用）';
COMMENT ON COLUMN agri_irrigation_zone.iwue IS '年度灌溉水利用系数 IWUE';
COMMENT ON COLUMN agri_irrigation_zone.water_productivity_kg_m3 IS '年度水分生产率 WUE (kg/m³)';
COMMENT ON COLUMN agri_irrigation_zone.benefit_yuan_per_m3 IS '年度单方水净效益 BEC (元/m³)';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_reliability IS '年度灌溉保证率 IRS';
COMMENT ON COLUMN agri_irrigation_zone.field_efficiency IS '年度田间水利用系数 FE';
COMMENT ON COLUMN agri_irrigation_zone.surface_water_utilization IS '年度地表水利用率 SUR';
COMMENT ON COLUMN agri_irrigation_zone.groundwater_utilization IS '年度地下水利用率 GWR';
COMMENT ON COLUMN agri_irrigation_zone.groundwater_dependency IS '年度地下水依赖度 GWI';
CREATE INDEX IF NOT EXISTS idx_agri_irrigation_zone_status ON agri_irrigation_zone (status);
CREATE INDEX IF NOT EXISTS idx_agri_irrigation_zone_sort ON agri_irrigation_zone (irrigation_area_code, sort_order, zone_id);
CREATE UNIQUE INDEX IF NOT EXISTS uk_agri_irrigation_zone_area_zone ON agri_irrigation_zone (irrigation_area_code, zone_id);

INSERT INTO agri_irrigation_zone (
    irrigation_area_code, irrigation_area_name, zone_id, zone_name, land_area, surface_water_available, groundwater_available,
    iwue, water_productivity_kg_m3, benefit_yuan_per_m3, irrigation_reliability, field_efficiency,
    surface_water_utilization, groundwater_utilization, groundwater_dependency,
    min_area, max_area, sort_order, status, remark
) VALUES
('chahayang', '查哈阳灌区', 'Z01', '红河', 2865.02, 36259380.0, 4696734.0, 0.74, 3.45, 15.5, 0.98, 0.97, 0.90, 0.14, 0.08, 2148.7650, 2865.02, 1, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z02', '万发', 3135.47, 39296070.0, 4873331.0, 0.60, 2.70, 11.5, 0.90, 0.90, 0.72, 0.28, 0.22, 2351.6025, 3135.47, 2, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z03', '金光', 3398.08, 41055570.0, 5091537.0, 0.58, 2.65, 10.9, 0.87, 0.89, 0.70, 0.30, 0.25, 2548.5600, 3398.08, 3, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z04', '稻花香', 3550.21, 30910780.0, 3833423.0, 0.56, 2.45, 10.2, 0.85, 0.87, 0.68, 0.32, 0.28, 2662.6575, 3550.21, 4, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z05', '发展', 2672.96, 44974950.0, 5877602.0, 0.54, 2.30, 9.6, 0.82, 0.85, 0.65, 0.35, 0.30, 2004.7200, 2672.96, 5, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z06', '金星', 3212.89, 39945480.0, 5253868.0, 0.52, 2.15, 8.8, 0.78, 0.83, 0.60, 0.40, 0.35, 2409.6675, 3212.89, 6, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z07', '太平湖', 1761.67, 43645990.0, 5412790.0, 0.50, 2.05, 8.2, 0.73, 0.80, 0.55, 0.45, 0.40, 1321.2525, 1761.67, 7, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z08', '海洋', 3889.15, 64301350.0, 8974380.0, 0.74, 3.42, 15.1, 0.97, 0.96, 0.92, 0.12, 0.06, 2916.8625, 3889.15, 8, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z09', '新立', 3454.23, 19992150.0, 2979341.0, 0.55, 2.38, 9.9, 0.80, 0.86, 0.62, 0.38, 0.33, 2590.6725, 3454.23, 9, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z10', '丰收', 3774.23, 37951930.0, 4006637.0, 0.58, 2.55, 10.6, 0.86, 0.88, 0.68, 0.32, 0.27, 2830.6725, 3774.23, 10, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z11', '二十八方', 5560.37, 26396760.0, 3273614.0, 0.42, 1.55, 5.0, 0.50, 0.68, 0.32, 0.68, 0.65, 4170.2775, 5560.37, 11, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z12', '联合', 1795.09, 42364060.0, 1153810.0, 0.40, 1.45, 4.5, 0.45, 0.65, 0.28, 0.72, 0.70, 1346.3175, 1795.09, 12, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z13', '金边', 2139.52, 7026099.0, 871347.0, 0.38, 1.30, 3.8, 0.40, 0.62, 0.22, 0.78, 0.76, 1604.6400, 2139.52, 13, '0', '默认14分区'),
('chahayang', '查哈阳灌区', 'Z14', '长吉岗', 5459.97, 33879440.0, 6701584.0, 0.35, 1.20, 3.2, 0.35, 0.58, 0.18, 0.82, 0.82, 4094.9775, 5459.97, 14, '0', '默认14分区')
ON CONFLICT (irrigation_area_code, zone_id) DO UPDATE SET
    irrigation_area_name = EXCLUDED.irrigation_area_name,
    zone_name = EXCLUDED.zone_name,
    land_area = EXCLUDED.land_area,
    surface_water_available = EXCLUDED.surface_water_available,
    groundwater_available = EXCLUDED.groundwater_available,
    iwue = EXCLUDED.iwue,
    water_productivity_kg_m3 = EXCLUDED.water_productivity_kg_m3,
    benefit_yuan_per_m3 = EXCLUDED.benefit_yuan_per_m3,
    irrigation_reliability = EXCLUDED.irrigation_reliability,
    field_efficiency = EXCLUDED.field_efficiency,
    surface_water_utilization = EXCLUDED.surface_water_utilization,
    groundwater_utilization = EXCLUDED.groundwater_utilization,
    groundwater_dependency = EXCLUDED.groundwater_dependency,
    min_area = EXCLUDED.min_area,
    max_area = EXCLUDED.max_area,
    sort_order = EXCLUDED.sort_order,
    status = EXCLUDED.status,
    remark = EXCLUDED.remark,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO sys_menu VALUES (2086, '分区数据', 2000, '8', 'zone', 'agriculture/zone/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:zone:list', 'tree-table', 'admin', current_timestamp, '', null, '灌区分区基础数据管理')
ON CONFLICT (menu_id) DO NOTHING;
INSERT INTO sys_menu VALUES (2087, '分区查询', 2086, '1', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:zone:query', '#', 'admin', current_timestamp, '', null, '')
ON CONFLICT (menu_id) DO NOTHING;
INSERT INTO sys_menu VALUES (2088, '分区新增', 2086, '2', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:zone:add', '#', 'admin', current_timestamp, '', null, '')
ON CONFLICT (menu_id) DO NOTHING;
INSERT INTO sys_menu VALUES (2089, '分区修改', 2086, '3', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:zone:edit', '#', 'admin', current_timestamp, '', null, '')
ON CONFLICT (menu_id) DO NOTHING;
INSERT INTO sys_menu VALUES (2090, '分区删除', 2086, '4', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:zone:remove', '#', 'admin', current_timestamp, '', null, '')
ON CONFLICT (menu_id) DO NOTHING;
INSERT INTO sys_menu VALUES (2091, '分区导入', 2086, '5', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:zone:import', '#', 'admin', current_timestamp, '', null, '')
ON CONFLICT (menu_id) DO NOTHING;
