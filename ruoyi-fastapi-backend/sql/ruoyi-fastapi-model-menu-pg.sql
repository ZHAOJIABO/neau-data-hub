-- =====================================================
-- 模型业务菜单补丁（远程 DB 适配版）
-- 适用：ruoyi-fastapi-pg (PostgreSQL) - 远程 8.146.227.98:15432
-- 前提：远程 sys_menu 已有 menu_id=2100 "模型平台" (M目录)
--       已挂 2101 灌溉决策 / 2102 水土资源 / 2103 渠系配水 / 2104 渠系水动力学
--       作物生长模拟挂在 menu_id=2032 (parent=2100)
-- 本脚本作用：
--   1) 新增 "初始水权分配" 菜单（menu_id=2105）
--   2) 给普通角色 (role_id=2) 授权所有 model 业务菜单
-- =====================================================

-- 新增：初始水权分配（与现有 2101~2104 平级，挂模型平台下）
insert into sys_menu values(2105, '初始水权分配', 2100, '5', 'water-right-allocation', 'model/waterRightAllocation/index', '', '', 1, 0, 'C', '0', '0', 'model:water:right:allocation', 'money', 'admin', current_timestamp, '', null, '初始水权分配菜单');

-- 普通角色 (role_id=2) 授权：模型平台 + 全部 model 业务菜单 + 渠系数据查询
insert into sys_role_menu values (2, 2100);
insert into sys_role_menu values (2, 2032);
insert into sys_role_menu values (2, 2101);
insert into sys_role_menu values (2, 2102);
insert into sys_role_menu values (2, 2103);
insert into sys_role_menu values (2, 2104);
insert into sys_role_menu values (2, 2105);