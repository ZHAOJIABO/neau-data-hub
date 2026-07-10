import unittest
from datetime import date

from module_model.model.pcse_growth_util import PcseGrowthUtil


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


if __name__ == '__main__':
    unittest.main()
