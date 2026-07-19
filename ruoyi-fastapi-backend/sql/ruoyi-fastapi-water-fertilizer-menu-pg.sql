-- =====================================================
-- 水肥调控模型菜单补丁
-- 适用：ruoyi-fastapi-pg (PostgreSQL) - 远程 8.146.227.98:15432
-- 前提：远程 sys_menu 已有 menu_id=2100 "模型平台" (M目录)
--       已挂 2101~2106 模型业务菜单
-- 本脚本作用：
--   1) 新增 "水肥调控模型" 菜单（menu_id=2107）
--   2) 给普通角色 (role_id=2) 授权该菜单
-- =====================================================

INSERT INTO sys_menu VALUES (
  2107,
  '水肥调控模型',
  2100,
  '7',
  'water-fertilizer',
  'model/waterFertilizer/index',
  '',
  '',
  1,
  0,
  'C',
  '0',
  '0',
  'model:water:fertilizer',
  'tree',
  'admin',
  current_timestamp,
  '',
  null,
  '水肥调控模型菜单'
) ON CONFLICT (menu_id) DO NOTHING;

INSERT INTO sys_role_menu VALUES (2, 2107)
ON CONFLICT DO NOTHING;
