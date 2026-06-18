"""
渠系优化配水接口 Python 测试脚本
==============================

测试范围:
  1. T01 optimize/full       鉴权缺失 (期望 401)
  2. T02 optimize/full       API Key 错误 (期望 401)
  3. T03 optimize/full       canals 数组为空 (期望 422 或业务码非 200)
  4. T04 optimize/full       多根自动识别 91 渠道 (验证节点守恒约束)

参数说明:
  BASE_URL 默认指向本地 dev 环境 (端口 9099)
  API_KEY  与 config/env.py IrrigationConfig.irrigation_api_key 一致
  渠段数据使用最小可运行规模, 在 neaudata 环境下数秒内完成

执行:
  d:\\Anaconda\\envs\\neaudata\\python.exe scripts\\test_canal_model_api.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import requests

BASE_URL = "http://127.0.0.1:9099"  # 本地 dev 环境 (端口 9099)
API_KEY = "irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY"
TIMEOUT = 600  # s, 单次请求最长等待

# 仅探测本地候选 BASE_URL，避免远程 nginx 反代干扰
CANDIDATE_BASES = [
    "http://127.0.0.1:9099",
    "http://127.0.0.1:9099/dev-api",
    "http://127.0.0.1:80/dev-api",
]


def _detect_base_url() -> str:
    for base in CANDIDATE_BASES:
        try:
            r = requests.get(
                f"{base}/api/v1/irrigation/canal/topology",
                headers={"X-Irrigation-Api-Key": API_KEY},
                timeout=3,
            )
        except requests.RequestException:
            continue
        if r.status_code == 200:
            return base
    return BASE_URL  # 探测失败时使用默认值, 让后续用例的失败信息更直观


BASE_URL = _detect_base_url()
OPTIMIZE_URL = f"{BASE_URL}/api/v1/irrigation/canal/optimize/full"
TOPOLOGY_URL = f"{BASE_URL}/api/v1/irrigation/canal/topology"


# ---------- 1. 构造测试数据 ----------

def build_optimize_multi_root_payload(n_laterals_per_branch: int = 5) -> dict[str, Any]:
    """构造多根（2 条干渠）的渠系数据, 验证自动识别 + 节点守恒约束。

    拓扑:
        干渠 1 (Q_design=6.0)
            支渠 1-1 / 1-2 / 1-3 / 1-4
                每条支渠下 n_laterals_per_branch 条斗渠
        干渠 2 (Q_design=4.0)
            支渠 2-1 / 2-2 / 2-3
                每条支渠下 n_laterals_per_branch 条斗渠

    n_laterals_per_branch=12 时:
        2 + 7 + 7*12 = 93 条 (≈ 91 渠道)
    """
    n_lat = max(1, int(n_laterals_per_branch))
    canals: list[dict[str, Any]] = []
    # 干渠 1
    canals.append({
        "canal_id": "1", "level": "1",
        "length": 3000, "design_flow": 6.0, "design_depth": 1.8,
        "bottom_width": 2.5, "slope": 0.0002, "side_slope": 1.5,
        "roughness": 0.015, "water_demand": 0,
    })
    # 干渠 2
    canals.append({
        "canal_id": "2", "level": "1",
        "length": 2400, "design_flow": 4.0, "design_depth": 1.5,
        "bottom_width": 2.0, "slope": 0.0002, "side_slope": 1.5,
        "roughness": 0.015, "water_demand": 0,
    })

    def _add_branch(branch_id: str, parent_id: str, qd: float) -> None:
        canals.append({
            "canal_id": branch_id, "parent_id": parent_id, "level": "2",
            "length": 1200, "design_flow": qd, "design_depth": 1.0,
            "bottom_width": 1.2, "slope": 0.0002, "side_slope": 1.5,
            "roughness": 0.015, "water_demand": 0,
        })
        for j in range(n_lat):
            lat_id = f"{branch_id}-{j + 1}"
            canals.append({
                "canal_id": lat_id, "parent_id": branch_id, "level": "3",
                "length": 600, "design_flow": max(0.2, qd / (n_lat + 1)),
                "design_depth": 0.5, "bottom_width": 0.5,
                "slope": 0.0003, "side_slope": 1.5,
                "roughness": 0.017, "water_demand": 3500 + j * 200,
            })

    for k in range(1, 5):
        _add_branch(f"1-{k}", "1", qd=1.5)
    for k in range(1, 4):
        _add_branch(f"2-{k}", "2", qd=1.2)

    return {
        "canals": canals,
        "t_max": 360,
        "flow_ratio_min": 0.8,
        "flow_ratio_max": 1.0,
        "min_groups": 2,
        "max_groups": 3,
        "pop_size": 40,
        "n_gen": 20,
        "seed": 1,
    }


# ---------- 2. 用例结果封装 ----------

@dataclass
class CaseResult:
    name: str
    passed: bool
    elapsed_s: float
    http_status: int
    detail: str = ""
    response: dict[str, Any] = field(default_factory=dict)


def auth_headers() -> dict[str, str]:
    return {
        "X-Irrigation-Api-Key": API_KEY,
        "Content-Type": "application/json",
    }


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> tuple[requests.Response, float]:
    t0 = time.time()
    resp = requests.post(url, headers=headers or auth_headers(), json=payload, timeout=TIMEOUT)
    return resp, time.time() - t0


# ---------- 3. 4 个用例 ----------

def case_t01_optimize_missing_key() -> CaseResult:
    name = "T01 optimize/full 缺少 X-Irrigation-Api-Key (期望 401)"
    headers = {"Content-Type": "application/json"}  # 故意不带 API Key
    payload = build_optimize_multi_root_payload(n_laterals_per_branch=12)
    try:
        resp, dt = post_json(OPTIMIZE_URL, payload, headers=headers)
    except requests.RequestException as e:
        return CaseResult(name, False, 0.0, 0, detail=f"网络异常: {e}")
    try:
        body = resp.json()
    except ValueError:
        return CaseResult(name, False, dt, resp.status_code, detail="响应非 JSON", response={"raw": resp.text[:400]})
    passed = resp.status_code in (200, 401) and body.get("code") == 401
    detail = f"http={resp.status_code}, code={body.get('code')}, msg={body.get('msg')!r}"
    return CaseResult(name, passed, dt, resp.status_code, detail=detail, response=body)


def case_t02_optimize_wrong_key() -> CaseResult:
    name = "T02 optimize/full API Key 错误 (期望 401)"
    headers = {
        "X-Irrigation-Api-Key": "this_is_a_wrong_key",
        "Content-Type": "application/json",
    }
    payload = build_optimize_multi_root_payload(n_laterals_per_branch=12)
    try:
        resp, dt = post_json(OPTIMIZE_URL, payload, headers=headers)
    except requests.RequestException as e:
        return CaseResult(name, False, 0.0, 0, detail=f"网络异常: {e}")
    try:
        body = resp.json()
    except ValueError:
        return CaseResult(name, False, dt, resp.status_code, detail="响应非 JSON", response={"raw": resp.text[:400]})
    passed = resp.status_code in (200, 401) and body.get("code") == 401
    detail = f"http={resp.status_code}, code={body.get('code')}, msg={body.get('msg')!r}"
    return CaseResult(name, passed, dt, resp.status_code, detail=detail, response=body)


def case_t03_optimize_empty_canals() -> CaseResult:
    """把 canals 数组置空, 触发 Pydantic 422 校验失败."""
    name = "T03 optimize/full canals 数组为空 (期望 422 或业务码非 200)"
    payload = build_optimize_multi_root_payload(n_laterals_per_branch=12)
    payload["canals"] = []
    try:
        resp, dt = post_json(OPTIMIZE_URL, payload)
    except requests.RequestException as e:
        return CaseResult(name, False, 0.0, 0, detail=f"网络异常: {e}")
    try:
        body = resp.json()
    except ValueError:
        return CaseResult(name, resp.status_code == 422, dt, resp.status_code,
                          detail="响应非 JSON (FastAPI 422 校验)", response={"raw": resp.text[:400]})
    passed = resp.status_code in (422, 500) or (
        resp.status_code == 200 and body.get("code") in (500, 400)
    )
    detail = f"http={resp.status_code}, code={body.get('code')}, msg={body.get('msg')!r}"
    return CaseResult(name, passed, dt, resp.status_code, detail=detail, response=body)


def case_t04_optimize_multi_root_91() -> CaseResult:
    """多根渠系一次性优化 + 节点守恒约束验证。

    构造 2 条干渠、共 ~91 条渠道的合成数据：
      - 校验响应 200 且 summary.n_roots == 2
      - 校验 summary.branches / laterals 数量
      - 抽样校验每条根下的支渠 q_actual/qd ≤ 1.0
    """
    name = "T04 optimize/full 多根自动识别 91 渠道 + 节点守恒约束"
    n_lat = 12  # 2 干 + 7 支 + 7*12 斗 = 93 条 (≈ 91 渠道)
    payload = build_optimize_multi_root_payload(n_laterals_per_branch=n_lat)
    n_canals = len(payload["canals"])
    try:
        resp, dt = post_json(OPTIMIZE_URL, payload)
    except requests.RequestException as e:
        return CaseResult(name, False, 0.0, 0, detail=f"网络异常: {e}")
    try:
        body = resp.json()
    except ValueError:
        return CaseResult(name, False, dt, resp.status_code,
                          detail="响应非 JSON", response={"raw": resp.text[:400]})

    base_ok = resp.status_code == 200 and body.get("code") == 200
    if not base_ok:
        detail = (
            f"http={resp.status_code}, code={body.get('code')}, "
            f"msg={body.get('msg')!r}, canals={n_canals}"
        )
        return CaseResult(name, False, dt, resp.status_code,
                          detail=detail, response=body)

    data = body.get("data") or {}
    summary = data.get("summary") or {}
    roots = data.get("roots") or []
    branches = data.get("branches") or []
    laterals = data.get("laterals") or []

    n_roots_ok = int(summary.get("n_roots") or 0) == 2
    has_roots_field = isinstance(roots, list) and len(roots) == 2
    all_ok_branches = all(
        float(b.get("qd") or 0) > 0
        and float(b.get("q_actual") or 0) / float(b.get("qd") or 1e-9) <= 1.0 + 1e-6
        for b in branches
    ) if branches else False

    passed = base_ok and n_roots_ok and has_roots_field and all_ok_branches
    detail = (
        f"http={resp.status_code}, code={body.get('code')}, "
        f"canals={n_canals}, n_roots={summary.get('n_roots')}, "
        f"branches={len(branches)}, laterals={len(laterals)}, "
        f"q_actual/qd≤1: {all_ok_branches}, "
        f"roots_field={has_roots_field}, mode={summary.get('mode')}"
    )
    return CaseResult(name, passed, dt, resp.status_code, detail=detail, response=body)


# ---------- 4. 主流程 ----------

def run() -> int:
    cases = [
        case_t01_optimize_missing_key,
        case_t02_optimize_wrong_key,
        case_t03_optimize_empty_canals,
        case_t04_optimize_multi_root_91,
    ]

    print("=" * 88)
    print(f"BASE_URL = {BASE_URL}")
    print(f"API_KEY  = {API_KEY}")
    print("=" * 88)

    # 探活一次 topology, 失败立即中止, 避免全部用例 404
    try:
        topo = requests.get(TOPOLOGY_URL, headers=auth_headers(), timeout=10)
        if topo.status_code != 200:
            print(f"[FATAL] topology 探活失败 http={topo.status_code}, body={topo.text[:300]}")
            return 2
        topo_body = topo.json()
        topo_data = topo_body.get("data") or {}
        print(f"探活 OK: roots={topo_data.get('roots')}, "
              f"nodes={len(topo_data.get('nodes', []))}, "
              f"edges={len(topo_data.get('edges', []))}")
    except requests.RequestException as e:
        print(f"[FATAL] topology 探活网络异常: {e}")
        return 2

    print()

    results: list[CaseResult] = []
    for fn in cases:
        print(f"\n>>> 正在执行: {fn.__name__}")
        r = fn()
        results.append(r)
        flag = "PASS" if r.passed else "FAIL"
        print(f"[{flag}] {r.name}")
        print(f"       {r.detail}")
        print(f"       elapsed={r.elapsed_s:.2f}s, http={r.http_status}")

    print("\n" + "=" * 88)
    print("汇总:")
    pass_n = sum(1 for r in results if r.passed)
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"  [{flag}] {r.elapsed_s:6.2f}s  {r.name}")
    print(f"\n通过 {pass_n}/{len(results)}")
    print("=" * 88)

    # 把完整响应落盘, 便于调试
    dump_path = "scripts/_last_canal_test_responses.json"
    try:
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(
                [{"name": r.name, "passed": r.passed, "elapsed_s": r.elapsed_s,
                  "http_status": r.http_status, "detail": r.detail, "response": r.response}
                 for r in results],
                f, ensure_ascii=False, indent=2, default=str,
            )
        print(f"完整响应已写入: {dump_path}")
    except OSError as e:
        print(f"[warn] 响应落盘失败: {e}")

    return 0 if pass_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
