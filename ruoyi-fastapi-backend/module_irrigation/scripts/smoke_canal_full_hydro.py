"""Smoke test for solve_full_hydro (3 canals, 30 min)."""
import sys
sys.path.insert(0, '.')

from module_irrigation.model.canal_full_hydro import FullHydroContext, solve_full_hydro


def main():
    ctx = FullHydroContext(
        main_canal_id='1',
        records=[
            {
                'canal_id': '1', 'level': '1', 'length': 1500.0,
                'design_flow': 4.0, 'design_depth': 1.2,
                'top_width': 3.0, 'bottom_width': 1.5,
                'slope': 0.0002, 'side_slope': 1.5, 'roughness': 0.015,
                'water_demand': 0.0,
                'inflow_series': [
                    {'time_min': 0.0, 'q_m3s': 4.0},
                    {'time_min': 60.0, 'q_m3s': 0.0},
                ],
            },
            {
                'canal_id': '1-1', 'parent_id': '1', 'level': '2',
                'length': 800.0, 'design_flow': 2.0, 'design_depth': 0.9,
                'top_width': 2.0, 'bottom_width': 1.0,
                'slope': 0.0002, 'side_slope': 1.5, 'roughness': 0.015,
                'water_demand': 0.0,
                'inflow_series': [
                    {'time_min': 0.0, 'q_m3s': 2.0},
                    {'time_min': 30.0, 'q_m3s': 0.0},
                ],
            },
            {
                'canal_id': '1-1-1', 'parent_id': '1-1', 'level': '3',
                'length': 400.0, 'design_flow': 1.0, 'design_depth': 0.5,
                'top_width': 1.0, 'bottom_width': 0.5,
                'slope': 0.0003, 'side_slope': 1.5, 'roughness': 0.017,
                'water_demand': 0.0,
                'inflow_series': [
                    {'time_min': 0.0, 'q_m3s': 1.0},
                    {'time_min': 20.0, 'q_m3s': 0.0},
                ],
            },
        ],
        sim_duration_min=30,
        dt_sec=30,
        downstream_h_mode='normal',
    )
    result = solve_full_hydro(ctx)
    print('summary:', result.summary)
    print('canals count:', len(result.canals))
    print('timeseries rows:', len(result.timeseries))
    print('topology nodes:', len(result.topology['nodes']))
    print('violations:', len(result.violations))
    for v in result.violations[:5]:
        print('  violation:', v)


if __name__ == '__main__':
    main()
