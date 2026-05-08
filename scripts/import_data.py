#!/usr/bin/env python3
"""
import_data.py — 农业数据导入脚本 (PostgreSQL)
将 data/ 目录下的表格文件(CSV/XLS/XLSX)导入 PostgreSQL datahub 数据库

用法:
    python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub
    python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub --only weather
    python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub --only soil
    python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub --only crop
"""

import argparse
import os
import sys
import re
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("错误: 需要安装 psycopg2")
    print("  pip install psycopg2-binary")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("错误: 需要安装 pandas")
    print("  pip install pandas openpyxl xlrd")
    sys.exit(1)


# ============================================================
# 工具函数
# ============================================================

def get_connection(args):
    """创建 PostgreSQL 连接"""
    kwargs = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "dbname": args.db,
    }
    if args.password:
        kwargs["password"] = args.password
    conn = psycopg2.connect(**kwargs)
    conn.autocommit = False
    return conn


def parse_numeric(val):
    """从带单位的字符串中提取数值，如 '-8.2℃' -> -8.2, '3.93%' -> 3.93"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if pd.isna(val):
            return None
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    # 去除常见单位
    s = re.sub(r'[℃%μs/cm]+$', '', s).strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_depth_cm(val):
    """从深度字符串提取数值，如 '10cm' -> 10, '20cm' -> 20"""
    if val is None:
        return None
    s = str(val).strip().lower()
    m = re.search(r'(\d+)', s)
    return int(m.group(1)) if m else None


def parse_date_flexible(val):
    """灵活解析日期"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (datetime,)):
        return val.date()
    if hasattr(val, 'date'):
        return val.date()
    s = str(val).strip()
    # 尝试常见格式
    for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%Y.%m.%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


# ============================================================
# 气象数据导入
# ============================================================

def import_weather_csv(conn, filepath, table, columns, stcd_col='STCD', date_col='date'):
    """
    通用气象 CSV 导入函数
    columns: list of (csv_col_name, db_col_name) tuples (不含 stcd 和 obs_date)
    """
    print(f"  [导入] {os.path.basename(filepath)}")
    df = pd.read_csv(filepath)
    cur = conn.cursor()

    col_names = ', '.join(['stcd', 'obs_date'] + [c[1] for c in columns])
    placeholders = ', '.join(['%s'] * (2 + len(columns)))
    conflict_updates = ', '.join([f"{c[1]} = EXCLUDED.{c[1]}" for c in columns])

    sql = f"""
        INSERT INTO {table} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT (stcd, obs_date) DO UPDATE SET {conflict_updates}
    """

    batch = []
    count = 0
    for _, row in df.iterrows():
        stcd = str(int(row[stcd_col]))
        obs_date = parse_date_flexible(row[date_col])
        if obs_date is None:
            continue
        values = [stcd, obs_date]
        for csv_col, _ in columns:
            values.append(parse_numeric(row.get(csv_col)))
        batch.append(tuple(values))
        count += 1

        if len(batch) >= 5000:
            cur.executemany(sql, batch)
            batch = []

    if batch:
        cur.executemany(sql, batch)

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_weather(conn, data_dir):
    """导入所有气象数据"""
    print("\n===== 导入气象数据 =====")
    total = 0

    # 两个站点目录
    stations = [
        ('鹤北小流域', '气象数据/鹤北小流域'),
        ('浓江农场', '气象数据/浓江农场'),
    ]

    for station_name, rel_path in stations:
        station_dir = os.path.join(data_dir, rel_path)
        if not os.path.isdir(station_dir):
            print(f"  [跳过] 目录不存在: {rel_path}")
            continue

        print(f"\n站点: {station_name}")

        # humidity_daily.csv
        f = os.path.join(station_dir, 'humidity_daily.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_humidity',
                                        [('RH_mean', 'rh_mean')])

        # precipitation_daily.csv
        f = os.path.join(station_dir, 'precipitation_daily.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_precipitation',
                                        [('precipitation', 'precipitation')])

        # sunshine_daily.csv
        f = os.path.join(station_dir, 'sunshine_daily.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_sunshine',
                                        [('sunshine_hours', 'sunshine_hours')])

        # temperature_daily.csv
        f = os.path.join(station_dir, 'temperature_daily.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_temperature',
                                        [('Tmax', 'tmax'), ('Tmin', 'tmin'), ('Tmean', 'tmean')])

        # wind_daily.csv
        f = os.path.join(station_dir, 'wind_daily.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_wind',
                                        [('wind', 'wind_speed')])

        # ET0_daily_result.csv（浓江）
        f = os.path.join(station_dir, 'ET0_daily_result.csv')
        if os.path.isfile(f):
            total += import_weather_csv(conn, f, 'weather_et0',
                                        [('Tmean', 'tmean'), ('precip', 'precip'), ('ET0', 'et0')])

    # 2000-2020 大文件（多站点数据，分块读入）
    for filename, table, columns in [
        ('2000-2020RHU.csv', 'weather_humidity', [('relative_humidity', 'rh_mean')]),
        ('2000-2020湿度.csv', 'weather_precipitation', [('precipitation', 'precipitation')]),
    ]:
        f = os.path.join(data_dir, '气象数据/鹤北小流域', filename)
        if os.path.isfile(f):
            print(f"\n  [导入] {filename} (大文件，分块处理...)")
            total += import_large_weather_csv(conn, f, table, columns)

    print(f"\n气象数据合计: {total} 条")
    return total


def import_large_weather_csv(conn, filepath, table, columns):
    """分块导入大型多站点 CSV 文件"""
    col_names = ', '.join(['stcd', 'obs_date'] + [c[1] for c in columns])
    placeholders = ', '.join(['%s'] * (2 + len(columns)))
    conflict_updates = ', '.join([f"{c[1]} = EXCLUDED.{c[1]}" for c in columns])

    sql = f"""
        INSERT INTO {table} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT (stcd, obs_date) DO UPDATE SET {conflict_updates}
    """

    cur = conn.cursor()
    total = 0
    chunk_size = 50000

    for chunk in pd.read_csv(filepath, chunksize=chunk_size):
        batch = []
        for _, row in chunk.iterrows():
            stcd = str(int(row['STCD']))
            obs_date = parse_date_flexible(row['date'])
            if obs_date is None:
                continue
            values = [stcd, obs_date]
            for csv_col, _ in columns:
                values.append(parse_numeric(row.get(csv_col)))
            batch.append(tuple(values))

        if batch:
            cur.executemany(sql, batch)
            conn.commit()
            total += len(batch)
            print(f"    已处理 {total} 条...", end='\r')

    conn.commit()
    cur.close()
    print(f"    {total} 条记录" + " " * 20)
    return total


# ============================================================
# 土壤数据导入
# ============================================================

def import_soil_parameter(conn, data_dir):
    """导入土壤参数 k/k1/k2"""
    soil_dir = os.path.join(data_dir, '土壤数据/鹤北小流域')
    total = 0

    # 原始列名到数据库字段的映射
    col_mapping = {
        'FID': 'fid',
        'Id': 'grid_id',
        'No': 'grid_no',
        'CROP': 'crop',
        'oc_0_5': 'oc_0_5',
        'sand_0_5': 'sand_0_5',
        'clay_0_5': 'clay_0_5',
        'silt05': 'silt_0_5',
        'Bulk.density': 'bulk_density',
        'K': 'k_value',
        'Moisture content': 'moisture_content',
        'Saturated moisture content': 'saturated_moisture_content',
        'Saturated matrix potential': 'saturated_matrix_potential',
        'Campbell': 'campbell',
        'Field capacity': 'field_capacity',
        'Wilting coefficient': 'wilting_coefficient',
        'Saturated hydraulic conductivity': 'saturated_hydraulic_conductivity',
        'Thermal conductivity': 'thermal_conductivity',
        'Specific heat capacity': 'specific_heat_capacity',
        'Steady.state.infiltration.rate': 'steady_state_infiltration_rate',
        'dem': 'dem',
    }

    db_cols = list(col_mapping.values())

    for source in ['k', 'k1', 'k2']:
        filename = f'土壤参数{source}.xls'
        filepath = os.path.join(soil_dir, filename)
        if not os.path.isfile(filepath):
            print(f"  [跳过] {filename}")
            continue

        print(f"  [导入] {filename}")
        df = pd.read_excel(filepath)
        cur = conn.cursor()

        col_str = ', '.join(['source'] + db_cols)
        placeholders = ', '.join(['%s'] * (1 + len(db_cols)))
        sql = f"INSERT INTO soil_parameter ({col_str}) VALUES ({placeholders})"

        batch = []
        for _, row in df.iterrows():
            values = [source]
            for orig_col, _ in col_mapping.items():
                values.append(parse_numeric(row.get(orig_col)))
            batch.append(tuple(values))

        if batch:
            cur.executemany(sql, batch)
            conn.commit()
            total += len(batch)
            print(f"    {len(batch)} 条记录")

        cur.close()

    return total


def import_soil_sensor(conn, data_dir):
    """导入传感器监测数据"""
    soil_dir = os.path.join(data_dir, '土壤数据/鹤北小流域')
    total = 0

    # 查找传感器数据文件
    sensor_files = [f for f in os.listdir(soil_dir)
                    if ('传感器' in f) and f.endswith('.xls')]

    for filename in sorted(sensor_files):
        filepath = os.path.join(soil_dir, filename)
        print(f"  [导入] {filename}")
        df = pd.read_excel(filepath)
        cur = conn.cursor()

        sql = """
            INSERT INTO soil_sensor_monitor
            (device_name, depth_cm, temperature, humidity, conductivity, obs_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        batch = []
        for _, row in df.iterrows():
            device = str(row.get('设备序列号', '')).strip()
            if not device or device == 'nan':
                continue
            depth = parse_depth_cm(row.get('序号'))
            if depth is None:
                continue
            temp = parse_numeric(row.get('温度'))
            humidity = parse_numeric(row.get('湿度'))
            conductivity = parse_numeric(row.get('电导率'))
            obs_time = row.get('上报时间')
            if obs_time is None or (isinstance(obs_time, float) and pd.isna(obs_time)):
                continue
            try:
                obs_time = pd.to_datetime(obs_time)
            except Exception:
                continue

            batch.append((device, depth, temp, humidity, conductivity, obs_time))

        if batch:
            cur.executemany(sql, batch)
            conn.commit()
            total += len(batch)
            print(f"    {len(batch)} 条记录")

        cur.close()

    return total


def import_soil_ground_temp(conn, data_dir):
    """导入地温数据（日期×深度矩阵转置）"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/2012地温数据整理(1).xlsx')
    if not os.path.isfile(filepath):
        print("  [跳过] 2012地温数据整理(1).xlsx")
        return 0

    print(f"  [导入] 2012地温数据整理(1).xlsx")
    df = pd.read_excel(filepath, header=None)

    # 第一行: [日期标签, 深度标签, 10cm, 20cm, ..., 200cm]
    # 后续行: [NaN, 日期字符串, 温度值...]
    # 从第一行提取深度列表
    depths = []
    for col_idx in range(2, df.shape[1]):
        depth_str = str(df.iloc[0, col_idx]).replace('cm', '').strip()
        try:
            depths.append(int(depth_str))
        except ValueError:
            depths.append(None)

    cur = conn.cursor()
    sql = """
        INSERT INTO soil_ground_temperature (obs_date, depth_cm, temperature)
        VALUES (%s, %s, %s)
        ON CONFLICT (obs_date, depth_cm) DO UPDATE SET temperature = EXCLUDED.temperature
    """

    count = 0
    for row_idx in range(1, df.shape[0]):
        date_val = df.iloc[row_idx, 1]
        obs_date = parse_date_flexible(date_val)
        if obs_date is None:
            continue

        for col_idx, depth in enumerate(depths):
            if depth is None:
                continue
            temp = parse_numeric(df.iloc[row_idx, col_idx + 2])
            if temp is not None:
                cur.execute(sql, (obs_date, depth, temp))
                count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_soil_layer_stats(conn, data_dir):
    """导入分层含水量统计"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/分层数据统计(1).xls')
    if not os.path.isfile(filepath):
        print("  [跳过] 分层数据统计(1).xls")
        return 0

    print(f"  [导入] 分层数据统计(1).xls")
    df = pd.read_excel(filepath, header=None)

    # 结构: 行0=表头(土层深度/cm, 土壤含水量(%), ..., 标准偏差, 变异系数)
    #        行1=子表头(NaN, 最大值, 最小值, 均值, NaN, NaN)
    #        行2+: 实际数据
    cur = conn.cursor()
    sql = """
        INSERT INTO soil_layer_stats (layer_depth, max_value, min_value, mean_value, std_dev, cv)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    count = 0
    for row_idx in range(2, df.shape[0]):
        layer = str(df.iloc[row_idx, 0]).strip()
        if not layer or layer == 'nan':
            continue
        max_val = parse_numeric(df.iloc[row_idx, 1])
        min_val = parse_numeric(df.iloc[row_idx, 2])
        mean_val = parse_numeric(df.iloc[row_idx, 3])
        std_val = parse_numeric(df.iloc[row_idx, 4])
        cv_val = parse_numeric(df.iloc[row_idx, 5])

        cur.execute(sql, (layer, max_val, min_val, mean_val, std_val, cv_val))
        count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_soil_thickness(conn, data_dir):
    """导入黑土厚度数据"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/监测点黑土厚度数据(1).xls')
    if not os.path.isfile(filepath):
        print("  [跳过] 监测点黑土厚度数据(1).xls")
        return 0

    print(f"  [导入] 监测点黑土厚度数据(1).xls")
    df = pd.read_excel(filepath)
    cur = conn.cursor()

    sql = """
        INSERT INTO soil_thickness (point_id, point_x, point_y, black_soil_depth_cm)
        VALUES (%s, %s, %s, %s)
    """

    count = 0
    for _, row in df.iterrows():
        point_id = str(row.get('ID', '')).strip()
        if not point_id or point_id == 'nan':
            continue
        point_x = parse_numeric(row.get('POINT_X'))
        point_y = parse_numeric(row.get('POINT_Y'))
        depth = parse_numeric(row.get('BlackSoilDepth（cm）'))
        if point_x is None or point_y is None:
            continue

        cur.execute(sql, (point_id, point_x, point_y, int(depth) if depth else 0))
        count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_experiment_plot(conn, data_dir):
    """导入试验小区概况"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/试验小区概况(1).xls')
    if not os.path.isfile(filepath):
        print("  [跳过] 试验小区概况(1).xls")
        return 0

    print(f"  [导入] 试验小区概况(1).xls")
    df = pd.read_excel(filepath)
    cur = conn.cursor()

    sql = "INSERT INTO experiment_plot_info (param_name, param_value) VALUES (%s, %s)"

    count = 0
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        value = str(row.iloc[1]).strip()
        if name == 'nan' or value == 'nan':
            continue
        cur.execute(sql, (name, value))
        count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_waterlogging(conn, data_dir):
    """导入涝渍地面积统计（解析第一个子表的主要数据）"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/涝渍地面积统计数据汇总.xls')
    if not os.path.isfile(filepath):
        print("  [跳过] 涝渍地面积统计数据汇总.xls")
        return 0

    print(f"  [导入] 涝渍地面积统计数据汇总.xls")
    df = pd.read_excel(filepath, header=None)

    cur = conn.cursor()
    sql = """
        INSERT INTO waterlogging_stats
        (region_name, region_area_ha, count, total_area_ha, area_ratio_pct)
        VALUES (%s, %s, %s, %s, %s)
    """

    count = 0
    # 第一个子表从列0开始，行0=标题，行1=子表头，行2+=数据
    # 列: 区域名称 | 区域面积(公顷) | 数量(个) | 总面积(公顷) | NaN | 面积占比(%)
    for row_idx in range(2, df.shape[0]):
        region = str(df.iloc[row_idx, 0]).strip()
        if not region or region == 'nan' or region == 'NaN':
            break
        area = parse_numeric(df.iloc[row_idx, 1])
        cnt = parse_numeric(df.iloc[row_idx, 2])
        total_area = parse_numeric(df.iloc[row_idx, 3])
        ratio = parse_numeric(df.iloc[row_idx, 5])

        cur.execute(sql, (region, area, int(cnt) if cnt else None, total_area, ratio))
        count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_soil_monitor_log(conn, data_dir):
    """导入土壤水分地温监测清单"""
    filepath = os.path.join(data_dir, '土壤数据/鹤北小流域/土壤水分、地温数据清单(1).xls')
    if not os.path.isfile(filepath):
        print("  [跳过] 土壤水分、地温数据清单(1).xls")
        return 0

    print(f"  [导入] 土壤水分、地温数据清单(1).xls")
    df = pd.read_excel(filepath, header=None)

    cur = conn.cursor()
    sql = """
        INSERT INTO soil_monitor_log (seq_no, obs_date, depth_desc)
        VALUES (%s, %s, %s)
    """

    count = 0
    # 数据从行2开始（行0=标题，行1=子表头）
    for row_idx in range(2, df.shape[0]):
        seq = parse_numeric(df.iloc[row_idx, 0])
        if seq is None:
            continue
        obs_date = parse_date_flexible(df.iloc[row_idx, 1])
        depth = str(df.iloc[row_idx, 2]).strip()
        if depth == 'nan':
            depth = None

        cur.execute(sql, (int(seq), obs_date, depth))
        count += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_soil(conn, data_dir):
    """导入所有土壤数据"""
    print("\n===== 导入土壤数据 =====")
    total = 0
    total += import_soil_parameter(conn, data_dir)
    total += import_soil_sensor(conn, data_dir)
    total += import_soil_ground_temp(conn, data_dir)
    total += import_soil_layer_stats(conn, data_dir)
    total += import_soil_thickness(conn, data_dir)
    total += import_experiment_plot(conn, data_dir)
    total += import_waterlogging(conn, data_dir)
    total += import_soil_monitor_log(conn, data_dir)
    print(f"\n土壤数据合计: {total} 条")
    return total


# ============================================================
# 作物数据导入
# ============================================================

def import_crop_leaf_area(conn, data_dir):
    """导入叶面积数据（重复分组结构）"""
    filepath = os.path.join(data_dir, '作物数据/鹤北小流域/叶面积.xlsx')
    if not os.path.isfile(filepath):
        print("  [跳过] 叶面积.xlsx")
        return 0

    print(f"  [导入] 叶面积.xlsx")
    df = pd.read_excel(filepath, header=None)

    cur = conn.cursor()
    sql = """
        INSERT INTO crop_leaf_area
        (plot, obs_date, plant_no, density, leaf_area_1, leaf_area_2, leaf_area_3)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    count = 0
    row_idx = 0
    while row_idx < df.shape[0]:
        # 找到 "日期" 标记行
        cell_val = str(df.iloc[row_idx, 0]).strip()
        if cell_val != '日期':
            row_idx += 1
            continue

        # 下一行包含小区编号和密度信息
        row_idx += 1
        if row_idx >= df.shape[0]:
            break

        # 从列11(大豆区)获取 plot 和 density
        plot = str(df.iloc[row_idx, 11]).strip()
        if plot == 'nan':
            plot = str(df.iloc[row_idx, 1]).strip()  # fallback to col 1
        density_val = parse_numeric(df.iloc[row_idx, 12])
        density = int(density_val) if density_val else None

        # 读取数据行（植株1-5）
        row_idx += 1
        while row_idx < df.shape[0]:
            obs_date = str(df.iloc[row_idx, 0]).strip()
            if obs_date == 'nan' or obs_date == '' or obs_date == '日期':
                break

            plant_no = parse_numeric(df.iloc[row_idx, 11])
            # 大豆叶面积(密度相关)在列12, 列13
            la1 = parse_numeric(df.iloc[row_idx, 12])
            la2 = parse_numeric(df.iloc[row_idx, 13])
            # 单株叶面积在列2-4区域
            la3 = parse_numeric(df.iloc[row_idx, 2])

            cur.execute(sql, (
                plot, obs_date,
                int(plant_no) if plant_no else None,
                density, la1, la2, la3
            ))
            count += 1
            row_idx += 1

    conn.commit()
    cur.close()
    print(f"    {count} 条记录")
    return count


def import_crop(conn, data_dir):
    """导入所有作物数据"""
    print("\n===== 导入作物数据 =====")
    total = import_crop_leaf_area(conn, data_dir)
    print(f"\n作物数据合计: {total} 条")
    return total


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="将农业数据文件导入 PostgreSQL datahub 数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
数据目录结构 (--data-dir):
  data/
  ├── 气象数据/
  │   ├── 鹤北小流域/   (humidity_daily.csv, temperature_daily.csv, ...)
  │   └── 浓江农场/     (humidity_daily.csv, ET0_daily_result.csv, ...)
  ├── 土壤数据/
  │   └── 鹤北小流域/   (土壤参数k.xls, 传感器监测数据...xls, ...)
  └── 作物数据/
      └── 鹤北小流域/   (叶面积.xlsx)

示例:
  python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub
  python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub --only weather
  python3 import_data.py --data-dir ./data --host localhost --user postgres --db datahub --password mypass --only soil
        """,
    )
    parser.add_argument("--data-dir", required=True,
                        help="数据文件根目录")
    parser.add_argument("--host", default="localhost",
                        help="PostgreSQL 主机 (默认: localhost)")
    parser.add_argument("--port", type=int, default=5432,
                        help="PostgreSQL 端口 (默认: 5432)")
    parser.add_argument("--user", default="postgres",
                        help="PostgreSQL 用户名 (默认: postgres)")
    parser.add_argument("--password", default=None,
                        help="PostgreSQL 密码")
    parser.add_argument("--db", default="datahub",
                        help="数据库名 (默认: datahub)")
    parser.add_argument("--only", choices=["weather", "soil", "crop"],
                        default=None, help="只导入指定类别")
    parser.add_argument("--skip-large", action="store_true",
                        help="跳过大文件(2000-2020RHU.csv等，约1800万行)")

    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"错误: 数据目录不存在: {args.data_dir}")
        sys.exit(1)

    print("=" * 60)
    print("  农业数据导入工具 — datahub (PostgreSQL)")
    print("=" * 60)
    print(f"数据目录: {os.path.abspath(args.data_dir)}")
    print(f"数据库:   {args.user}@{args.host}:{args.port}/{args.db}")
    if args.only:
        print(f"只导入:   {args.only}")
    if args.skip_large:
        print(f"跳过大文件: 是")
    print()

    # 连接数据库
    try:
        conn = get_connection(args)
        print("数据库连接成功")
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

    # 如果 skip-large，临时重命名大文件以跳过
    skip_files = []
    if args.skip_large:
        for fname in ['2000-2020RHU.csv', '2000-2020湿度.csv']:
            fpath = os.path.join(args.data_dir, '气象数据/鹤北小流域', fname)
            if os.path.isfile(fpath):
                skip_path = fpath + '.skip'
                os.rename(fpath, skip_path)
                skip_files.append((fpath, skip_path))

    try:
        grand_total = 0

        if args.only is None or args.only == "weather":
            grand_total += import_weather(conn, args.data_dir)

        if args.only is None or args.only == "soil":
            grand_total += import_soil(conn, args.data_dir)

        if args.only is None or args.only == "crop":
            grand_total += import_crop(conn, args.data_dir)

        print("\n" + "=" * 60)
        print(f"  导入完成！总计: {grand_total} 条记录")
        print("=" * 60)

    except Exception as e:
        print(f"\n导入过程出错: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        # 恢复被跳过的文件
        for orig, skip in skip_files:
            if os.path.isfile(skip):
                os.rename(skip, orig)
        conn.close()


if __name__ == "__main__":
    main()
