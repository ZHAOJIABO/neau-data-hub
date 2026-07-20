from common import get_json, post_json, print_result


summary = get_json("/api/v1/irrigation/water-fertilizer/regulation/summary")
print_result("水肥调控时序数据摘要", summary)

payload = {
    "yieldMax": 9000,
    "maxIrrigation": 40,
    "waterEfficiency": 0.75,
    "paddyWater": 80,
    "leakage": 2.5,
    "b0": 0.62,
    "b1": 0.55,
    "b2": -0.17,
    "c": 0.35,
    "nitrogenBase": 45,
    "nitrogenOptimal": 180,
    "nitrogenMax": 260,
    "nitrogenMin": 60,
    "populationSize": 20,
    "generations": 3,
    "startDate": "2024-05-15",
    "endDate": "2024-05-26",
}

result = post_json("/api/v1/irrigation/water-fertilizer/optimize", payload)
print_result("水肥调控优化", result, ["bestSolution", "optimizationInfo"])
