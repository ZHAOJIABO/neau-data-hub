from common import CROPS, post_json, print_result, water_right_zones


payload = {
    "irrigationAreaCode": "chahayang",
    "zones": water_right_zones(),
    "crops": CROPS,
    "market": {
        "initialTotalWaterM3": 260000000,
        "reservePriceYuanPerM3": 5.2,
        "priceFloor": 1.0,
        "priceCeiling": 8.0,
        "transactionCostRate": 0.08,
        "fairnessWeight": 0.35,
        "savingIncentiveWeight": 0.45,
        "minSelfUseRatio": 0.0,
    },
}

result = post_json("/api/v1/irrigation/water-right-allocation/solve", payload)
print_result("灌区水权分配与市场博弈", result, ["summary", "equilibrium"])
