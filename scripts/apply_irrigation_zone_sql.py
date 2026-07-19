#!/usr/bin/env python3
"""
执行分区数据与菜单幂等 SQL，并验证查哈阳灌区分区和菜单路由。

默认读取后端配置；也可以通过命令行参数覆盖数据库连接：
    python scripts/apply_irrigation_zone_sql.py --env prod
    python scripts/apply_irrigation_zone_sql.py --host 127.0.0.1 --port 5432 --user postgres --password root --db ruoyi-fastapi
"""

import argparse
import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / 'ruoyi-fastapi-backend'
SQL_FILE = BACKEND_DIR / 'sql' / 'ruoyi-fastapi-irrigation-zone-pg.sql'

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import psycopg2
except ImportError:
    print('错误: 当前 Python 环境缺少 psycopg2，请在 neaudata 环境中运行。')
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='执行灌区分区数据幂等 SQL')
    parser.add_argument('--env', default='', help='后端配置环境，例如 dev/prod；留空使用默认 dev')
    parser.add_argument('--host', default='', help='PostgreSQL 地址；留空读取后端配置')
    parser.add_argument('--port', type=int, default=0, help='PostgreSQL 端口；留空读取后端配置')
    parser.add_argument('--user', default='', help='PostgreSQL 用户；留空读取后端配置')
    parser.add_argument('--password', default='', help='PostgreSQL 密码；留空读取后端配置')
    parser.add_argument('--db', default='', help='PostgreSQL 数据库；留空读取后端配置')
    parser.add_argument('--sql-file', default=str(SQL_FILE), help='要执行的 SQL 文件路径')
    return parser.parse_args()


def load_backend_db_config(env_name: str):
    if env_name:
        os.environ['APP_ENV'] = env_name

    os.chdir(BACKEND_DIR)
    from config.env import DataBaseConfig

    return {
        'host': DataBaseConfig.db_host,
        'port': DataBaseConfig.db_port,
        'user': DataBaseConfig.db_username,
        'password': DataBaseConfig.db_password,
        'dbname': DataBaseConfig.db_database,
    }


def build_connection_args(args):
    config = load_backend_db_config(args.env)
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    if args.user:
        config['user'] = args.user
    if args.password:
        config['password'] = args.password
    if args.db:
        config['dbname'] = args.db
    return config


def main():
    args = parse_args()
    sql_path = Path(args.sql_file).resolve()
    if not sql_path.is_file():
        print(f'错误: SQL 文件不存在: {sql_path}')
        return 1

    conn_args = build_connection_args(args)
    safe_conn = {key: ('******' if key == 'password' else value) for key, value in conn_args.items()}
    print(f'连接数据库: {safe_conn}')
    print(f'执行 SQL: {sql_path}')

    sql = sql_path.read_text(encoding='utf-8')

    conn = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                cursor.execute(
                    """
                    select count(*)
                    from agri_irrigation_zone
                    where irrigation_area_code = 'chahayang'
                      and status = '0'
                    """
                )
                zone_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    select count(*)
                    from sys_menu
                    where component = 'agriculture/zone/index'
                    """
                )
                menu_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    select irrigation_area_code, irrigation_area_name, count(*)
                    from agri_irrigation_zone
                    group by irrigation_area_code, irrigation_area_name
                    order by irrigation_area_code
                    """
                )
                areas = cursor.fetchall()
    finally:
        conn.close()

    print(f'查哈阳启用分区数量: {zone_count}')
    print(f'分区管理菜单路由数量: {menu_count}')
    print('灌区分区统计:')
    for area_code, area_name, count in areas:
        print(f'  {area_code} / {area_name}: {count}')

    if zone_count != 14:
        print('错误: 查哈阳灌区启用分区数量不是 14。')
        return 2
    if menu_count < 1:
        print('错误: 未找到 agriculture/zone/index 菜单路由。')
        return 3

    print('执行完成，验证通过。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
