from common import get_json, post_json, print_result


zone_response = get_json(
    "/agriculture/zone/enabled",
    {"irrigationAreaCode": "chahayang"},
    auth="token",
)
zone_rows = zone_response.get("data", zone_response)
if not isinstance(zone_rows, list) or not zone_rows:
    raise SystemExit("No enabled zone rows returned from /agriculture/zone/enabled.")

zones = [
    {
        "zoneId": row.get("zoneId") or row.get("zone_id"),
        "zoneName": row.get("zoneName") or row.get("zone_name"),
        "iwue": float(row.get("iwue") or 0),
        "waterProductivityKgM3": float(row.get("waterProductivityKgM3") or row.get("water_productivity_kg_m3") or 0),
        "benefitYuanPerM3": float(row.get("benefitYuanPerM3") or row.get("benefit_yuan_per_m3") or 0),
        "irrigationReliability": float(row.get("irrigationReliability") or row.get("irrigation_reliability") or 0),
        "fieldEfficiency": float(row.get("fieldEfficiency") or row.get("field_efficiency") or 0),
        "surfaceWaterUtilization": float(row.get("surfaceWaterUtilization") or row.get("surface_water_utilization") or 0),
        "groundwaterUtilization": float(row.get("groundwaterUtilization") or row.get("groundwater_utilization") or 0),
        "groundwaterDependency": float(row.get("groundwaterDependency") or row.get("groundwater_dependency") or 0),
    }
    for row in zone_rows
]

payload = {
    "irrigationAreaCode": "chahayang",
    "periods": [{"periodId": "2025", "periodLabel": "2025 年", "zones": zones}],
    "alpha": 0.5,
}

result = post_json("/api/v1/irrigation/water-efficiency/evaluate", payload)
print_result("灌区农业水效评价", result, ["summary", "periodResults"])
