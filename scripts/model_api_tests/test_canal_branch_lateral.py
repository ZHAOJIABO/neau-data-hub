from common import post_json, print_result


canals = [
    {"canal_id": "Z1", "canal_name": "红河支渠", "level": "3", "length": 2800, "design_flow": 4.2, "bottom_width": 3.0, "design_depth": 1.4, "slope": 0.00042, "side_slope": 1.5, "roughness": 0.026, "water_demand": 0},
    {"canal_id": "D1", "canal_name": "红河斗渠一", "parent_id": "Z1", "level": "4", "length": 1200, "design_flow": 1.2, "bottom_width": 1.4, "design_depth": 0.9, "slope": 0.00050, "side_slope": 1.25, "roughness": 0.027, "water_demand": 460000},
    {"canal_id": "D2", "canal_name": "红河斗渠二", "parent_id": "Z1", "level": "4", "length": 1350, "design_flow": 1.0, "bottom_width": 1.2, "design_depth": 0.85, "slope": 0.00052, "side_slope": 1.25, "roughness": 0.027, "water_demand": 430000},
    {"canal_id": "D3", "canal_name": "红河斗渠三", "parent_id": "Z1", "level": "4", "length": 1480, "design_flow": 1.1, "bottom_width": 1.3, "design_depth": 0.88, "slope": 0.00049, "side_slope": 1.25, "roughness": 0.027, "water_demand": 490000},
    {"canal_id": "D4", "canal_name": "红河斗渠四", "parent_id": "Z1", "level": "4", "length": 1100, "design_flow": 0.9, "bottom_width": 1.1, "design_depth": 0.82, "slope": 0.00055, "side_slope": 1.25, "roughness": 0.027, "water_demand": 390000},
]

payload = {
    "mode": "branch-lateral",
    "canals": canals,
    "topology": [{"canal_id": "Z1", "parent_id": None}, {"canal_id": "D1", "parent_id": "Z1"}, {"canal_id": "D2", "parent_id": "Z1"}, {"canal_id": "D3", "parent_id": "Z1"}, {"canal_id": "D4", "parent_id": "Z1"}],
    "branch_canal_id": "Z1",
    "t_max": 240,
    "flow_ratio_min": 0.6,
    "flow_ratio_max": 1.0,
    "min_groups": 2,
    "max_groups": 3,
    "pop_size": 30,
    "n_gen": 5,
    "seed": 20260720,
}

result = post_json("/api/v1/irrigation/canal/optimize/branch-lateral", payload)
print_result("渠系支斗轮续灌优化", result, ["summary", "bestSolution", "objectiveValues"])
