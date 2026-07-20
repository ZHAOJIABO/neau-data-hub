from common import post_json, print_result


rows = [
    ("红河", 0.74, 3.45, 15.5, 0.98, 0.97, 0.90, 0.14, 0.08),
    ("万发", 0.60, 2.70, 11.5, 0.90, 0.90, 0.72, 0.28, 0.22),
    ("金光", 0.58, 2.65, 10.9, 0.87, 0.89, 0.70, 0.30, 0.25),
    ("稻花香", 0.56, 2.45, 10.2, 0.85, 0.87, 0.68, 0.32, 0.28),
    ("发展", 0.54, 2.30, 9.6, 0.82, 0.85, 0.65, 0.35, 0.30),
    ("金星", 0.52, 2.15, 8.8, 0.78, 0.83, 0.60, 0.40, 0.35),
    ("太平湖", 0.50, 2.05, 8.2, 0.73, 0.80, 0.55, 0.45, 0.40),
    ("海洋", 0.74, 3.42, 15.1, 0.97, 0.96, 0.92, 0.12, 0.06),
    ("新立", 0.55, 2.38, 9.9, 0.80, 0.86, 0.62, 0.38, 0.33),
    ("丰收", 0.58, 2.55, 10.6, 0.86, 0.88, 0.68, 0.32, 0.27),
    ("二十八方", 0.42, 1.55, 5.0, 0.50, 0.68, 0.32, 0.68, 0.65),
    ("联合", 0.40, 1.45, 4.5, 0.45, 0.65, 0.28, 0.72, 0.70),
    ("金边", 0.38, 1.30, 3.8, 0.40, 0.62, 0.22, 0.78, 0.76),
    ("长吉岗", 0.35, 1.20, 3.2, 0.35, 0.58, 0.18, 0.82, 0.82),
]

zones = [
    {
        "zoneId": f"Z{i + 1:02d}",
        "zoneName": name,
        "iwue": iwue,
        "waterProductivityKgM3": wue,
        "benefitYuanPerM3": bec,
        "irrigationReliability": irs,
        "fieldEfficiency": fe,
        "surfaceWaterUtilization": sur,
        "groundwaterUtilization": gwr,
        "groundwaterDependency": gwi,
    }
    for i, (name, iwue, wue, bec, irs, fe, sur, gwr, gwi) in enumerate(rows)
]

payload = {
    "irrigationAreaCode": "chahayang",
    "periods": [{"periodId": "2025", "periodLabel": "2025 年", "zones": zones}],
    "alpha": 0.5,
}

result = post_json("/api/v1/irrigation/water-efficiency/evaluate", payload)
print_result("灌区农业水效评价", result, ["summary", "periodResults"])
