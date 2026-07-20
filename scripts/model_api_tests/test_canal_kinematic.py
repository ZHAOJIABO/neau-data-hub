from common import post_json, print_result


payload = {
    "canal_id": "G1",
    "L": 5200.0,
    "nx": 61,
    "b": 8.0,
    "m": 1.5,
    "n_Manning": 0.025,
    "S0": 0.00035,
    "Q_upstream": 12.0,
    "Q_initial": 10.0,
    "tf": 3600.0,
    "dt": 30.0,
    "theta": 0.6,
    "output_interval_sec": 300.0,
    "branches": [
        {"x_position": 1800.0, "Q_offtake": 1.5, "spread_cells": 2},
        {"x_position": 3400.0, "Q_offtake": 1.2, "spread_cells": 2},
    ],
    "inflow_series": [
        {"t_sec": 0, "q_m3s": 10.0},
        {"t_sec": 1200, "q_m3s": 12.0},
        {"t_sec": 2400, "q_m3s": 11.0},
        {"t_sec": 3600, "q_m3s": 10.5},
    ],
}

result = post_json("/api/v1/irrigation/canal/hydro/kinematic", payload)
print_result("渠系 Kinematic Wave 水动力仿真", result, ["summary", "timeseries", "final_state"])
