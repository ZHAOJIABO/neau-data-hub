from __future__ import annotations

import os
import sys
import unittest
from datetime import date

from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_model.entity.vo.water_fertilizer_vo import WaterFertilizerOptimizeRequest
from module_model.model.water_fertilizer_optimize import (
    NSGA3WaterFertilizerOptimizer,
    WaterFertilizerOptimizationProblem,
)
from module_model.service.water_fertilizer_service import WaterFertilizerService


def _make_payload(**overrides):
    payload = {
        'yieldMax': 9000,
        'maxIrrigation': 40,
        'waterEfficiency': 0.75,
        'paddyWater': 80,
        'leakage': 2.5,
        'b0': 0.62,
        'b1': 0.55,
        'b2': -0.17,
        'c': 0.35,
        'nitrogenBase': 45,
        'nitrogenOptimal': 180,
        'nitrogenMax': 260,
        'nitrogenMin': 60,
        'populationSize': 20,
        'generations': 2,
        'startDate': '2025-05-01',
        'endDate': '2025-05-12',
    }
    payload.update(overrides)
    return payload


def _make_regulation_rows(n_rows: int = 12):
    rows = []
    for idx in range(n_rows):
        rows.append(
            {
                'recordTime': date(2025, 5, idx + 1),
                'dailyEffectiveRainfall': 2.0 if idx % 3 == 0 else 0.5,
                'dailyMaxCropEvapotranspiration': 5.0,
                'dailyMinCropEvapotranspiration': 3.0,
                'maxWaterStorageDepth': 80.0,
                'maxSuitableWaterDepth': 60.0,
                'minSuitableWaterDepth': 20.0,
            }
        )
    return rows


class WaterFertilizerModelTests(unittest.TestCase):
    def test_request_accepts_camel_case_payload(self):
        req = WaterFertilizerOptimizeRequest.model_validate(_make_payload())
        self.assertEqual(req.yield_max, 9000)
        self.assertEqual(req.model_dump(by_alias=True)['yieldMax'], 9000)

    def test_request_rejects_invalid_date_range(self):
        with self.assertRaises(ValidationError):
            WaterFertilizerOptimizeRequest.model_validate(
                _make_payload(startDate='2025-06-01', endDate='2025-05-01')
            )

    def test_request_rejects_invalid_nitrogen_bounds(self):
        with self.assertRaises(ValidationError):
            WaterFertilizerOptimizeRequest.model_validate(_make_payload(nitrogenMin=300, nitrogenMax=260))

    def test_optimizer_returns_stable_result_shape(self):
        req = WaterFertilizerOptimizeRequest.model_validate(_make_payload())
        regulation_data = WaterFertilizerService._build_regulation_data(_make_regulation_rows())
        result = NSGA3WaterFertilizerOptimizer(
            population_size=req.population_size,
            generations=req.generations,
        ).optimize(WaterFertilizerOptimizationProblem(regulation_data, req.model_dump()))

        self.assertIn('bestSolution', result)
        self.assertIn('paretoSolutions', result)
        self.assertIn('optimizationInfo', result)
        self.assertIsNotNone(result['bestSolution'])
        self.assertLessEqual(len(result['paretoSolutions']), 50)
        self.assertEqual(result['optimizationInfo']['algorithm'], 'NSGA-III')

    def test_detailed_data_matches_input_days(self):
        rows = _make_regulation_rows()
        regulation_data = WaterFertilizerService._build_regulation_data(rows)
        best_solution = {'decisionVariables': {'irrigation': [1.0] * len(rows), 'nitrogen': 120.0}}
        detailed = WaterFertilizerService._calculate_detailed_data(best_solution, regulation_data, leakage=2.5)

        self.assertEqual(len(detailed), len(rows))
        self.assertEqual(detailed[0]['recordTime'], rows[0]['recordTime'])
        self.assertIn('waterDepth', detailed[0])
        self.assertIn('irrigation', detailed[0])


if __name__ == '__main__':
    unittest.main()
