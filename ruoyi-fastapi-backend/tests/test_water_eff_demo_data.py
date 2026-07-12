"""
灌区年度用水评价默认模拟数据回归测试。

锁定 14 分区模拟数据在当前默认阈值（excellent=0.7 / good=0.5 / qualified=0.3）下
能覆盖四个等级，且具体分区数与排名位置稳定。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_model.entity.vo.water_efficiency_evaluate_vo import WaterEfficiencyEvaluateRequest
from module_model.model.water_efficiency_evaluate_model import evaluate_water_efficiency


# 与 ruoyi-fastapi-frontend/src/views/model/waterEfficiency/index.vue 中
# DEFAULT_ZONE_DATA 严格保持一致；修改其中一边时，另一边需同步。
_DEMO_ROWS = [
    ('红河',    0.74, 3.45, 15.5, 0.98, 0.97, 0.90, 0.14, 0.08),
    ('万发',    0.60, 2.70, 11.5, 0.90, 0.90, 0.72, 0.28, 0.22),
    ('金光',    0.58, 2.65, 10.9, 0.87, 0.89, 0.70, 0.30, 0.25),
    ('稻花香',  0.56, 2.45, 10.2, 0.85, 0.87, 0.68, 0.32, 0.28),
    ('发展',    0.54, 2.30,  9.6, 0.82, 0.85, 0.65, 0.35, 0.30),
    ('金星',    0.52, 2.15,  8.8, 0.78, 0.83, 0.60, 0.40, 0.35),
    ('太平湖',  0.50, 2.05,  8.2, 0.73, 0.80, 0.55, 0.45, 0.40),
    ('海洋',    0.74, 3.42, 15.1, 0.97, 0.96, 0.92, 0.12, 0.06),
    ('新立',    0.55, 2.38,  9.9, 0.80, 0.86, 0.62, 0.38, 0.33),
    ('丰收',    0.58, 2.55, 10.6, 0.86, 0.88, 0.68, 0.32, 0.27),
    ('二十八方', 0.42, 1.55,  5.0, 0.50, 0.68, 0.32, 0.68, 0.65),
    ('联合',    0.40, 1.45,  4.5, 0.45, 0.65, 0.28, 0.72, 0.70),
    ('金边',    0.38, 1.30,  3.8, 0.40, 0.62, 0.22, 0.78, 0.76),
    ('长吉岗',  0.35, 1.20,  3.2, 0.35, 0.58, 0.18, 0.82, 0.82),
]


def _build_zones() -> list[dict]:
    zones = []
    for i, (name, iwue, wue, bec, irs, fe, sur, gwr, gwi) in enumerate(_DEMO_ROWS):
        zones.append({
            'zoneId': f'Z{i+1:02d}',
            'zoneName': name,
            'iwue': iwue,
            'waterProductivityKgM3': wue,
            'benefitYuanPerM3': bec,
            'irrigationReliability': irs,
            'fieldEfficiency': fe,
            'surfaceWaterUtilization': sur,
            'groundwaterUtilization': gwr,
            'groundwaterDependency': gwi,
        })
    return zones


class WaterEfficiencyDemoDataTests(unittest.TestCase):
    """默认 14 分区模拟数据评价结果回归。"""

    @classmethod
    def setUpClass(cls) -> None:
        req = WaterEfficiencyEvaluateRequest.model_validate({
            'periods': [{'periodId': '2025', 'periodLabel': '2025 年', 'zones': _build_zones()}],
            'alpha': 0.5,
        })
        result = evaluate_water_efficiency(req)
        cls.period = result['periodResults'][0]

    def test_grade_distribution_covers_all_tiers(self):
        gd = self.period['summary']['gradeDistribution']
        # 优秀至少 2 个（Z01 红河 + Z08 海洋）
        self.assertGreaterEqual(gd['excellent'], 2, f"excellent={gd['excellent']}")
        # 良好至少 2 个
        self.assertGreaterEqual(gd['good'], 2, f"good={gd['good']}")
        # 合格至少 2 个
        self.assertGreaterEqual(gd['qualified'], 2, f"qualified={gd['qualified']}")
        # 不合格至少 1 个
        self.assertGreaterEqual(gd['unqualified'], 1, f"unqualified={gd['unqualified']}")

    def test_red_river_is_top_and_excellent(self):
        pr_summary = self.period['summary']
        self.assertEqual(pr_summary['bestZoneName'], '红河')
        rank_one = next(z for z in self.period['zoneResults'] if z['rank'] == 1)
        self.assertEqual(rank_one['zoneName'], '红河')
        self.assertEqual(rank_one['grade'], '优秀')

    def test_longjigang_is_worst_and_unqualified(self):
        pr_summary = self.period['summary']
        self.assertEqual(pr_summary['worstZoneName'], '长吉岗')
        last = max(self.period['zoneResults'], key=lambda z: z['rank'])
        self.assertEqual(last['zoneName'], '长吉岗')
        self.assertEqual(last['grade'], '不合格')

    def test_score_range_is_well_distributed(self):
        scores = [z['score'] for z in self.period['zoneResults']]
        self.assertGreater(max(scores) - min(scores), 0.35,
                           '14 分区分差应大于 0.35，体现差异化')


if __name__ == '__main__':
    unittest.main()