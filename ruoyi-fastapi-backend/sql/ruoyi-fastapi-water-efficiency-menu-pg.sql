-- =====================================================
-- 农业水效评价菜单补丁
-- 适用：ruoyi-fastapi-pg (PostgreSQL) - 远程 8.146.227.98:15432
-- 前提：远程 sys_menu 已有 menu_id=2100 "模型平台" (M目录)
--       已挂 2101 灌溉决策 / 2102 水土资源 / 2103 渠系配水 / 2104 渠系水动力学 / 2105 初始水权分配
-- 本脚本作用：
--   1) 新增 "农业水效评价" 菜单（menu_id=2106）
--   2) 给普通角色 (role_id=2) 授权该菜单
-- =====================================================

-- 新增：农业水效评价（与现有 2101~2105 平级，挂模型平台下，order_num=6）
INSERT INTO sys_menu VALUES (2106, '农业水效评价', 2100, '6', 'water-efficiency', 'model/waterEfficiency/index', '', '', 1, 0, 'C', '0', '0', 'model:water:efficiency', 'data-analysis', 'admin', current_timestamp, '', null, '灌区农业水效综合评价菜单');

-- 普通角色 (role_id=2) 授权
INSERT INTO sys_role_menu VALUES (2, 2106);
