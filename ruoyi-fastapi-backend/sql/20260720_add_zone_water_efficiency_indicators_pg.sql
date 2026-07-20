-- 为灌区分区表补充年度水效评价指标字段，并为查哈阳默认 14 分区写入当前年度指标。
-- PostgreSQL，幂等，可在已有库上重复执行。

ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS iwue NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS water_productivity_kg_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS benefit_yuan_per_m3 NUMERIC(10, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS irrigation_reliability NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS field_efficiency NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS surface_water_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS groundwater_utilization NUMERIC(8, 4) NOT NULL DEFAULT 0;
ALTER TABLE agri_irrigation_zone ADD COLUMN IF NOT EXISTS groundwater_dependency NUMERIC(8, 4) NOT NULL DEFAULT 0;

COMMENT ON COLUMN agri_irrigation_zone.iwue IS '年度灌溉水利用系数 IWUE';
COMMENT ON COLUMN agri_irrigation_zone.water_productivity_kg_m3 IS '年度水分生产率 WUE (kg/m³)';
COMMENT ON COLUMN agri_irrigation_zone.benefit_yuan_per_m3 IS '年度单方水净效益 BEC (元/m³)';
COMMENT ON COLUMN agri_irrigation_zone.irrigation_reliability IS '年度灌溉保证率 IRS';
COMMENT ON COLUMN agri_irrigation_zone.field_efficiency IS '年度田间水利用系数 FE';
COMMENT ON COLUMN agri_irrigation_zone.surface_water_utilization IS '年度地表水利用率 SUR';
COMMENT ON COLUMN agri_irrigation_zone.groundwater_utilization IS '年度地下水利用率 GWR';
COMMENT ON COLUMN agri_irrigation_zone.groundwater_dependency IS '年度地下水依赖度 GWI';

UPDATE agri_irrigation_zone AS z
SET
    iwue = v.iwue,
    water_productivity_kg_m3 = v.water_productivity_kg_m3,
    benefit_yuan_per_m3 = v.benefit_yuan_per_m3,
    irrigation_reliability = v.irrigation_reliability,
    field_efficiency = v.field_efficiency,
    surface_water_utilization = v.surface_water_utilization,
    groundwater_utilization = v.groundwater_utilization,
    groundwater_dependency = v.groundwater_dependency,
    updated_at = CURRENT_TIMESTAMP
FROM (
    VALUES
    ('Z01', 0.74, 3.45, 15.5, 0.98, 0.97, 0.90, 0.14, 0.08),
    ('Z02', 0.60, 2.70, 11.5, 0.90, 0.90, 0.72, 0.28, 0.22),
    ('Z03', 0.58, 2.65, 10.9, 0.87, 0.89, 0.70, 0.30, 0.25),
    ('Z04', 0.56, 2.45, 10.2, 0.85, 0.87, 0.68, 0.32, 0.28),
    ('Z05', 0.54, 2.30, 9.6, 0.82, 0.85, 0.65, 0.35, 0.30),
    ('Z06', 0.52, 2.15, 8.8, 0.78, 0.83, 0.60, 0.40, 0.35),
    ('Z07', 0.50, 2.05, 8.2, 0.73, 0.80, 0.55, 0.45, 0.40),
    ('Z08', 0.74, 3.42, 15.1, 0.97, 0.96, 0.92, 0.12, 0.06),
    ('Z09', 0.55, 2.38, 9.9, 0.80, 0.86, 0.62, 0.38, 0.33),
    ('Z10', 0.58, 2.55, 10.6, 0.86, 0.88, 0.68, 0.32, 0.27),
    ('Z11', 0.42, 1.55, 5.0, 0.50, 0.68, 0.32, 0.68, 0.65),
    ('Z12', 0.40, 1.45, 4.5, 0.45, 0.65, 0.28, 0.72, 0.70),
    ('Z13', 0.38, 1.30, 3.8, 0.40, 0.62, 0.22, 0.78, 0.76),
    ('Z14', 0.35, 1.20, 3.2, 0.35, 0.58, 0.18, 0.82, 0.82)
) AS v(
    zone_id, iwue, water_productivity_kg_m3, benefit_yuan_per_m3, irrigation_reliability,
    field_efficiency, surface_water_utilization, groundwater_utilization, groundwater_dependency
)
WHERE z.irrigation_area_code = 'chahayang'
  AND z.zone_id = v.zone_id;
