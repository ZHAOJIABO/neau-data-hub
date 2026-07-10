import unittest
from datetime import date
from pydantic import ValidationError

from module_model.model.pcse_growth_util import PcseGrowthUtil
from module_model.entity.vo.crop_growth_vo import RiceGrowthSimulationRequest


class PcseGrowthIrrigationTest(unittest.TestCase):
    def test_normalize_output_restores_applied_irrigation_and_counts_events(self):
        output = [
            {'day': date(2025, 7, 1), 'RIRR': 0.0, 'TOTIRR': 0.0},
            {'day': date(2025, 7, 2), 'RIRR': 2.25, 'TOTIRR': 2.25},
            {'day': date(2025, 7, 3), 'RIRR': 0.0, 'TOTIRR': 2.25},
            {'day': date(2025, 7, 4), 'RIRR': 1.5, 'TOTIRR': 3.75},
        ]

        daily_results = PcseGrowthUtil._normalize_output(output, irrigation_efficiency=0.75)
        summary = PcseGrowthUtil._build_irrigation_summary(daily_results)

        self.assertEqual([item['rirr'] for item in daily_results], [0.0, 3.0, 0.0, 2.0])
        self.assertEqual([item['totirr'] for item in daily_results], [0.0, 3.0, 3.0, 5.0])
        self.assertEqual(summary['irrigation_count'], 2)
        self.assertEqual(summary['total_irrigation'], 5.0)

    def _build_agro(self, threshold=0.25, amount=1.5, efficiency=0.75):
        return PcseGrowthUtil._build_agromanagement(
            simulation_start_date='2025-05-01',
            plant_start_date='2025-05-15',
            plant_end_date='2025-09-30',
            irrigation_end_date='2025-08-31',
            max_duration=140,
            soil_moisture_threshold=threshold,
            irrigation_efficiency=efficiency,
            single_irrigation_amount=amount,
            variety_name='Rice_IR72_WS',
        )

    def test_agromanagement_uses_tiered_thresholds_with_split_application(self):
        agro = self._build_agro(threshold=0.25, amount=1.5, efficiency=0.75)
        active_state_events = agro[0][list(agro[0].keys())[0]]['StateEvents'][0]

        self.assertEqual(active_state_events['event_signal'], 'irrigate')
        self.assertEqual(active_state_events['event_state'], 'SM')
        self.assertEqual(active_state_events['zero_condition'], 'falling')

        table = active_state_events['events_table']
        self.assertEqual(len(table), 3, '应当生成三级递减阈值')

        thresholds = [next(iter(row.keys())) for row in table]
        amounts = [next(iter(row.values()))['amount'] for row in table]
        self.assertEqual(thresholds, [0.25, 0.23, 0.21])
        self.assertEqual(amounts, [1.5, 1.875, 2.25])
        self.assertTrue(all(thresholds[i] > thresholds[i + 1] for i in range(len(thresholds) - 1)))
        self.assertTrue(all(amounts[i] < amounts[i + 1] for i in range(len(amounts) - 1)))

        for row in table:
            payload = next(iter(row.values()))
            self.assertEqual(payload['efficiency'], 0.75)

    def test_agromanagement_stop_section_disables_irrigation(self):
        agro = self._build_agro(threshold=0.25, amount=1.5, efficiency=0.75)
        stop_section_key = list(agro[1].keys())[0]
        stop_state_events = agro[1][stop_section_key]['StateEvents'][0]
        stop_table = stop_state_events['events_table']

        self.assertEqual(len(stop_table), 1)
        stop_threshold = next(iter(stop_table[0].keys()))
        self.assertLessEqual(stop_threshold, 0.19)
        self.assertGreaterEqual(stop_threshold, 0.10)
        self.assertEqual(next(iter(stop_table[0].values()))['amount'], 0)

    def test_agromanagement_low_threshold_clamps_stop_floor(self):
        agro = self._build_agro(threshold=0.16, amount=1.5, efficiency=0.75)
        stop_section_key = list(agro[1].keys())[0]
        stop_threshold = next(iter(agro[1][stop_section_key]['StateEvents'][0]['events_table'][0].keys()))
        self.assertEqual(stop_threshold, 0.10)

    def test_request_model_rejects_out_of_range_threshold(self):
        with self.assertRaises(ValidationError):
            RiceGrowthSimulationRequest(
                longitude=125.0,
                latitude=46.0,
                simulation_start_date='2025-05-01',
                plant_start_date='2025-05-15',
                plant_end_date='2025-09-30',
                irrigation_end_date='2025-08-31',
                soil_moisture_threshold=0.10,
            )
        with self.assertRaises(ValidationError):
            RiceGrowthSimulationRequest(
                longitude=125.0,
                latitude=46.0,
                simulation_start_date='2025-05-01',
                plant_start_date='2025-05-15',
                plant_end_date='2025-09-30',
                irrigation_end_date='2025-08-31',
                soil_moisture_threshold=0.45,
            )

    def test_request_model_accepts_default_values(self):
        request = RiceGrowthSimulationRequest(
            longitude=125.0,
            latitude=46.0,
            simulation_start_date='2025-05-01',
            plant_start_date='2025-05-15',
            plant_end_date='2025-09-30',
            irrigation_end_date='2025-08-31',
        )
        self.assertEqual(request.soil_moisture_threshold, 0.22)
        self.assertEqual(request.single_irrigation_amount, 1.5)


if __name__ == '__main__':
    unittest.main()
