-- ============================================================
-- 农业数据模块菜单插入脚本
-- 使用 menu_id 从 2000 开始避免与系统菜单冲突
-- menu_type: M=目录, C=菜单, F=按钮
-- ============================================================

-- 一级目录：农业数据
insert into sys_menu values(2000, '农业数据', 0, '5', 'agriculture', null, '', '', 1, 0, 'M', '0', '0', '', 'chart', 'admin', current_timestamp, '', null, '农业数据管理目录');

-- 二级菜单：数据概览
insert into sys_menu values(2001, '数据概览', 2000, '1', 'dashboard', 'agriculture/dashboard/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:dashboard:list', 'dashboard', 'admin', current_timestamp, '', null, '数据概览');

-- 二级目录：气象数据
insert into sys_menu values(2010, '气象数据', 2000, '2', 'weather', null, '', '', 1, 0, 'M', '0', '0', '', 'cloud', 'admin', current_timestamp, '', null, '气象数据目录');

-- 三级菜单：气象综合
insert into sys_menu values(2011, '气象综合', 2010, '1', 'overview', 'agriculture/weather/overview/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:weather:overview', 'list', 'admin', current_timestamp, '', null, '气象综合数据');

-- 三级菜单：温度数据
insert into sys_menu values(2012, '温度数据', 2010, '2', 'temperature', 'agriculture/weather/temperature/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:weather:temperature', 'color', 'admin', current_timestamp, '', null, '温度数据');

-- 三级菜单：湿度数据
insert into sys_menu values(2013, '湿度数据', 2010, '3', 'humidity', 'agriculture/weather/humidity/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:weather:humidity', 'drizzle', 'admin', current_timestamp, '', null, '湿度数据');

-- 三级菜单：降水数据
insert into sys_menu values(2014, '降水数据', 2010, '4', 'precipitation', 'agriculture/weather/precipitation/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:weather:precipitation', 'cascader', 'admin', current_timestamp, '', null, '降水数据');

-- 二级目录：土壤数据
insert into sys_menu values(2020, '土壤数据', 2000, '3', 'soil', null, '', '', 1, 0, 'M', '0', '0', '', 'tree', 'admin', current_timestamp, '', null, '土壤数据目录');

-- 三级菜单：传感器监测
insert into sys_menu values(2021, '传感器监测', 2020, '1', 'sensor', 'agriculture/soil/sensor/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:soil:sensor', 'monitor', 'admin', current_timestamp, '', null, '传感器监测');

-- 三级菜单：土壤参数
insert into sys_menu values(2022, '土壤参数', 2020, '2', 'parameter', 'agriculture/soil/parameter/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:soil:parameter', 'component', 'admin', current_timestamp, '', null, '土壤水文参数');

-- 三级菜单：地温数据
insert into sys_menu values(2023, '地温数据', 2020, '3', 'groundTemp', 'agriculture/soil/groundTemp/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:soil:groundTemp', 'color', 'admin', current_timestamp, '', null, '分层地温数据');

-- 三级菜单：黑土厚度
insert into sys_menu values(2024, '黑土厚度', 2020, '4', 'thickness', 'agriculture/soil/thickness/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:soil:thickness', 'documentation', 'admin', current_timestamp, '', null, '监测点黑土厚度');

-- 三级菜单：分层统计
insert into sys_menu values(2025, '分层统计', 2020, '5', 'layerStats', 'agriculture/soil/layerStats/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:soil:layerStats', 'table', 'admin', current_timestamp, '', null, '分层含水量统计');

-- 二级目录：作物数据
insert into sys_menu values(2030, '作物数据', 2000, '4', 'crop', null, '', '', 1, 0, 'M', '0', '0', '', 'education', 'admin', current_timestamp, '', null, '作物数据目录');

-- 三级菜单：叶面积指数
insert into sys_menu values(2031, '叶面积指数', 2030, '1', 'leafArea', 'agriculture/crop/leafArea/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:crop:leafArea', 'tree', 'admin', current_timestamp, '', null, '大豆叶面积指数');

-- 二级菜单：站点管理
insert into sys_menu values(2040, '站点管理', 2000, '5', 'station', 'agriculture/station/index', '', '', 1, 0, 'C', '0', '0', 'agriculture:station:list', 'international', 'admin', current_timestamp, '', null, '监测站点管理');

-- ============================================================
-- 按钮权限（温度数据为例，其他类似）
-- ============================================================

-- 温度数据按钮
insert into sys_menu values(2051, '温度查询', 2012, '1', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:weather:temperature:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2052, '温度新增', 2012, '2', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:weather:temperature:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2053, '温度删除', 2012, '3', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:weather:temperature:remove', '#', 'admin', current_timestamp, '', null, '');

-- 站点管理按钮
insert into sys_menu values(2061, '站点查询', 2040, '1', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:station:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2062, '站点新增', 2040, '2', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:station:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2063, '站点修改', 2040, '3', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:station:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2064, '站点删除', 2040, '4', '', '', '', '', 1, 0, 'F', '0', '0', 'agriculture:station:remove', '#', 'admin', current_timestamp, '', null, '');
