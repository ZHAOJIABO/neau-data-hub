"""
灌区年度用水评价（熵权-TOPSIS）响应序列化回归测试。

覆盖：
1. 请求体可使用 camelCase 别名绑定（前端默认形态）。
2. 响应顶层字段、summary、periodResults[].summary、zoneResults[].{original,normalized,weighted}
   及 indicatorWeights 全部使用 camelCase 键名。
3. 评价结果按预期产生等级分布与排名（与熵权-TOPSIS 算法一致）。
"""

from __future__ import annotations

import os
import sys

import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_model.entity.vo.water_efficiency_evaluate_vo import WaterEfficiencyEvaluateRequest
from module_model.model.water_efficiency_evaluate_model import evaluate_water_efficiency


def _build_payload() -> dict:
    rows = [
        ('红河',    0.63, 2.85, 12.8, 0.93, 0.92, 0.78, 0.22, 0.18),
        ('万发',    0.60, 2.70, 11.5, 0.90, 0.90, 0.72, 0.28, 0.22),
        ('金光',    0.58, 2.65, 10.9, 0.87, 0.89, 0.70, 0.30, 0.25),
        ('稻花香',  0.56, 2.45, 10.2, 0.85, 0.87, 0.68, 0.32, 0.28),
        ('发展',    0.54, 2.30,  9.6, 0.82, 0.85, 0.65, 0.35, 0.30),
        ('金星',    0.52, 2.15,  8.8, 0.78, 0.83, 0.60, 0.40, 0.35),
        ('太平湖',  0.50, 2.05,  8.2, 0.73, 0.80, 0.55, 0.45, 0.40),
        ('海洋',    0.62, 2.80, 12.4, 0.92, 0.91, 0.80, 0.20, 0.15),
        ('新立',    0.55, 2.38,  9.9, 0.80, 0.86, 0.62, 0.38, 0.33),
        ('丰收',    0.58, 2.55, 10.6, 0.86, 0.88, 0.68, 0.32, 0.27),
        ('二十八方', 0.49, 1.95,  7.8, 0.68, 0.79, 0.52, 0.48, 0.44),
        ('联合',    0.48, 1.88,  7.3, 0.65, 0.77, 0.48, 0.52, 0.48),
        ('金边',    0.46, 1.75,  6.6, 0.60, 0.74, 0.42, 0.58, 0.54),
        ('长吉岗',  0.44, 1.65,  6.0, 0.55, 0.72, 0.38, 0.62, 0.58),
    ]
    zones = []
    for i, (name, iwue, wue, bec, irs, fe, sur, gwr, gwi) in enumerate(rows):
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
    return {'periods': [{'periodId': '2025', 'periodLabel': '2025 年', 'zones': zones}], 'alpha': 0.5}


class WaterEfficiencyResponseSerializationTests(unittest.TestCase):
    """水效评价响应 camelCase 序列化回归。"""

    def setUp(self) -> None:
        req = WaterEfficiencyEvaluateRequest.model_validate(_build_payload())
        self.result = evaluate_water_efficiency(req)

    def test_top_level_keys_are_camel_case(self):
        self.assertEqual(set(self.result.keys()), {'summary', 'periodResults', 'indicatorInfo'})

    def test_overall_summary_keys_are_camel_case(self):
        s = self.result['summary']
        self.assertIn('totalZones', s)
        self.assertIn('gradeDistribution', s)
        self.assertEqual(s['totalZones'], 14)
        self.assertEqual(set(s['gradeDistribution'].keys()),
                         {'excellent', 'good', 'qualified', 'unqualified'})

    def test_period_result_keys_are_camel_case(self):
        pr = self.result['periodResults'][0]
        self.assertIn('nZones', pr)
        self.assertIn('zoneResults', pr)
        self.assertIn('indicatorWeights', pr)
        self.assertIn('topsisIdeal', pr)
        self.assertIn('summary', pr)
        self.assertEqual(pr['nZones'], 14)

    def test_period_summary_keys_are_camel_case(self):
        ps = self.result['periodResults'][0]['summary']
        for key in ('meanScore', 'stdScore', 'maxScore', 'minScore',
                    'bestZoneId', 'bestZoneName', 'worstZoneId', 'worstZoneName',
                    'gradeDistribution'):
            self.assertIn(key, ps, f'missing key: {key}')

    def test_zone_result_keys_are_camel_case(self):
        zr = self.result['periodResults'][0]['zoneResults'][0]
        for key in ('zoneId', 'zoneName', 'original', 'normalized', 'weighted',
                    'score', 'rank', 'grade'):
            self.assertIn(key, zr, f'missing key: {key}')

    def test_indicator_subdict_keys_are_camel_case(self):
        zr = self.result['periodResults'][0]['zoneResults'][0]
        for sub in ('original', 'normalized', 'weighted'):
            self.assertIn('waterProductivityKgM3', zr[sub], f'{sub} 缺少 camelCase 键')
            self.assertIn('groundwaterDependency', zr[sub], f'{sub} 缺少 camelCase 键')

    def test_indicator_weights_keys_are_camel_case(self):
        iw = self.result['periodResults'][0]['indicatorWeights']
        self.assertIn('waterProductivityKgM3', iw)

    def test_zone_results_sorted_by_rank(self):
        pr = self.result['periodResults'][0]
        ranks = [zr['rank'] for zr in pr['zoneResults']]
        # zone_results 按 rank 升序排列
        self.assertEqual(ranks, sorted(ranks))
        # 排名连续覆盖 1..n_zones，且 rank=1 对应最高得分
        self.assertEqual(sorted(set(ranks)), list(range(1, pr['nZones'] + 1)))
        scores = [zr['score'] for zr in pr['zoneResults']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        # summary 中最佳 / 最差分区名称与 zoneResults 一致
        best = max(pr['zoneResults'], key=lambda z: z['score'])
        worst = min(pr['zoneResults'], key=lambda z: z['score'])
        self.assertEqual(pr['summary']['bestZoneName'], best['zoneName'])
        self.assertEqual(pr['summary']['worstZoneName'], worst['zoneName'])
        # rank=1 的分区必须是评分最高的那一个
        rank_one = next(zr for zr in pr['zoneResults'] if zr['rank'] == 1)
        self.assertEqual(rank_one['zoneName'], best['zoneName'])


if __name__ == '__main__':
    unittest.main()