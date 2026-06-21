import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    port=5432,
    dbname='ruoyi-fastapi',
    user='postgres',
    password='root'
)
cur = conn.cursor()
cur.execute('''
    SELECT canal_id, canal_name, length, design_flow,
           bottom_width, slope, side_slope, roughness
    FROM agri_canal
    ORDER BY canal_id
    LIMIT 20
''')
rows = cur.fetchall()
print("canal_id | canal_name | length | design_flow | bottom_width | slope | side_slope | roughness")
print("-" * 120)
for r in rows:
    print(r)
conn.close()
