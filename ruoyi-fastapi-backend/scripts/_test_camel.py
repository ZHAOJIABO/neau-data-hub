"""调试 pydantic to_camel 对 design_q_m3s 的输出"""
from pydantic.alias_generators import to_camel

tests = [
    'design_q_m3s',
    'design_depth_m',
    'design_slope',
    'min_gate_opening_m',
]
for t in tests:
    print(f'{t!r} -> {to_camel(t)!r}')
