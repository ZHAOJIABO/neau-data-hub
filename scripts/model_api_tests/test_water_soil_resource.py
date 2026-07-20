from common import CROPS, post_json, print_result, water_soil_zones


payload = {
    "mode": "water-soil-resource",
    "irrigation_area_code": "chahayang",
    "zones": water_soil_zones(),
    "crops": CROPS,
    "total_water_available": 260000000,
    "pop_size": 40,
    "n_gen": 5,
    "seed": 20260720,
    "alpha": 0.5,
}

result = post_json("/api/v1/irrigation/water-soil-resource/optimize", payload)
print_result("灌区水土资源优化配置", result, ["summary", "bestSolution", "objectiveValues"])
