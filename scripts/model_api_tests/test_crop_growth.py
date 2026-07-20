from common import post_json, print_result


payload = {
    "longitude": 123.95,
    "latitude": 47.35,
    "simulationStartDate": "2025-05-01",
    "plantStartDate": "2025-05-15",
    "plantEndDate": "2025-09-30",
    "irrigationEndDate": "2025-08-31",
    "soilMoistureThreshold": 0.22,
    "irrigationEfficiency": 0.75,
    "singleIrrigationAmount": 1.5,
    "site": {"wav": 20.0, "smlim": 0.4},
    "varietyName": "Rice_IR72_WS",
}

result = post_json("/agriculture/crop-growth/rice/simulate", payload, auth="token")
print_result("水稻作物生长模拟", result, ["summary"])
