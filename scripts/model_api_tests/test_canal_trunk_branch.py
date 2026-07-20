from common import post_json, print_result


canals = [
    {"canal_id": "G1", "canal_name": "查哈阳干渠一段", "level": "2", "length": 5200, "design_flow": 16.0, "bottom_width": 8.0, "design_depth": 2.2, "slope": 0.00035, "side_slope": 1.5, "roughness": 0.025, "water_demand": 0},
    {"canal_id": "Z1", "canal_name": "红河支渠", "parent_id": "G1", "level": "3", "length": 2800, "design_flow": 4.2, "bottom_width": 3.0, "design_depth": 1.4, "slope": 0.00042, "side_slope": 1.5, "roughness": 0.026, "water_demand": 1850000},
    {"canal_id": "Z2", "canal_name": "万发支渠", "parent_id": "G1", "level": "3", "length": 3100, "design_flow": 4.8, "bottom_width": 3.2, "design_depth": 1.5, "slope": 0.00040, "side_slope": 1.5, "roughness": 0.026, "water_demand": 2120000},
    {"canal_id": "Z3", "canal_name": "金光支渠", "parent_id": "G1", "level": "3", "length": 3300, "design_flow": 5.0, "bottom_width": 3.3, "design_depth": 1.5, "slope": 0.00038, "side_slope": 1.5, "roughness": 0.026, "water_demand": 2280000},
]

payload = {
    "mode": "trunk-branch",
    "canals": canals,
    "topology": [{"canal_id": "G1", "parent_id": None}, {"canal_id": "Z1", "parent_id": "G1"}, {"canal_id": "Z2", "parent_id": "G1"}, {"canal_id": "Z3", "parent_id": "G1"}],
    "trunk_canal_id": "G1",
    "t_max": 240,
    "flow_ratio_min": 0.6,
    "flow_ratio_max": 1.0,
    "pop_size": 30,
    "n_gen": 5,
    "seed": 20260720,
}

result = post_json("/api/v1/irrigation/canal/optimize/trunk-branch", payload)
print_result("渠系干支优化配水", result, ["summary", "bestSolution", "objectiveValues"])
