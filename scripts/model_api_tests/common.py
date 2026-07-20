from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error, parse, request


BASE_URL = os.getenv("MODEL_API_BASE_URL", "http://8.146.227.98:19099").rstrip("/")
IRRIGATION_API_KEY = os.getenv("IRRIGATION_API_KEY", "irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")


ZONES = [
    ("Z01", "红河", 2865.02, 18500000, 3200000),
    ("Z02", "万发", 3135.47, 21200000, 3500000),
    ("Z03", "金光", 3398.08, 22800000, 3800000),
    ("Z04", "稻花香", 3550.21, 15600000, 2800000),
    ("Z05", "发展", 2672.96, 24800000, 4400000),
    ("Z06", "金星", 3212.89, 21600000, 4100000),
    ("Z07", "太平湖", 1761.67, 23600000, 3900000),
    ("Z08", "海洋", 3889.15, 39500000, 8500000),
    ("Z09", "新立", 3454.23, 9800000, 2600000),
    ("Z10", "丰收", 3774.23, 19800000, 3600000),
    ("Z11", "二十八方", 5560.37, 13200000, 3000000),
    ("Z12", "联合", 1795.09, 23400000, 1100000),
    ("Z13", "金边", 2139.52, 3200000, 800000),
    ("Z14", "长吉岗", 5459.97, 17600000, 6100000),
]


CROP_MIX = {
    "Z01": {"rice": 0.15, "corn": 0.45, "soybean": 0.40},
    "Z02": {"rice": 0.20, "corn": 0.50, "soybean": 0.30},
    "Z03": {"rice": 0.10, "corn": 0.55, "soybean": 0.35},
    "Z04": {"rice": 0.25, "corn": 0.50, "soybean": 0.25},
    "Z05": {"rice": 0.10, "corn": 0.40, "soybean": 0.50},
    "Z06": {"rice": 0.15, "corn": 0.45, "soybean": 0.40},
    "Z07": {"rice": 0.30, "corn": 0.50, "soybean": 0.20},
    "Z08": {"rice": 0.80, "corn": 0.15, "soybean": 0.05},
    "Z09": {"rice": 0.75, "corn": 0.20, "soybean": 0.05},
    "Z10": {"rice": 0.70, "corn": 0.20, "soybean": 0.10},
    "Z11": {"rice": 0.85, "corn": 0.10, "soybean": 0.05},
    "Z12": {"rice": 0.80, "corn": 0.15, "soybean": 0.05},
    "Z13": {"rice": 0.70, "corn": 0.20, "soybean": 0.10},
    "Z14": {"rice": 0.90, "corn": 0.07, "soybean": 0.03},
}


CROPS = [
    {
        "crop": "rice",
        "cropName": "水稻",
        "yieldKgPerHa": 9255.56,
        "priceYuanPerKg": 3.16,
        "costYuanPerHa": 8400,
        "waterQuotaM3PerHa": 8000,
        "nitrogenMinKgHa": 80,
        "nitrogenMaxKgHa": 260,
        "nitrogenProductivityCoeff": 1.0,
        "waterProductivityCoeff": 1.0,
        "nitrogenCostYuanPerKg": 4.2,
    },
    {
        "crop": "corn",
        "cropName": "玉米",
        "yieldKgPerHa": 5269.44,
        "priceYuanPerKg": 2.25,
        "costYuanPerHa": 7200,
        "waterQuotaM3PerHa": 1900,
        "nitrogenMinKgHa": 60,
        "nitrogenMaxKgHa": 220,
        "nitrogenProductivityCoeff": 1.0,
        "waterProductivityCoeff": 1.0,
        "nitrogenCostYuanPerKg": 4.2,
    },
    {
        "crop": "soybean",
        "cropName": "大豆",
        "yieldKgPerHa": 5945.0,
        "priceYuanPerKg": 5.4,
        "costYuanPerHa": 3000,
        "waterQuotaM3PerHa": 1700,
        "nitrogenMinKgHa": 20,
        "nitrogenMaxKgHa": 120,
        "nitrogenProductivityCoeff": 1.0,
        "waterProductivityCoeff": 1.0,
        "nitrogenCostYuanPerKg": 4.2,
    },
]


def post_json(path: str, payload: dict[str, Any], *, auth: str = "irrigation", timeout: int = 600) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if auth == "irrigation":
        headers["X-Irrigation-Api-Key"] = IRRIGATION_API_KEY
    elif auth == "token":
        if not AUTH_TOKEN:
            raise SystemExit("AUTH_TOKEN is required for this endpoint.")
        headers["Authorization"] = AUTH_TOKEN
    req = request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method="POST")
    return _open_json(req, timeout)


def get_json(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    auth: str = "irrigation",
    timeout: int = 120,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{parse.urlencode(params)}"
    headers = {}
    if auth == "irrigation":
        headers["X-Irrigation-Api-Key"] = IRRIGATION_API_KEY
    elif auth == "token":
        if not AUTH_TOKEN:
            raise SystemExit("AUTH_TOKEN is required for this endpoint.")
        headers["Authorization"] = AUTH_TOKEN
    req = request.Request(url, headers=headers, method="GET")
    return _open_json(req, timeout)


def _open_json(req: request.Request, timeout: int) -> dict[str, Any]:
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')}") from exc
    parsed = json.loads(data)
    if parsed.get("success") is False:
        raise SystemExit(json.dumps(parsed, ensure_ascii=False, indent=2))
    return parsed


def print_result(name: str, result: dict[str, Any], keys: list[str] | None = None) -> None:
    data = result.get("data", result)
    preview = {key: data.get(key) for key in keys or [] if isinstance(data, dict)}
    print(f"[OK] {name}")
    print(json.dumps(preview or data, ensure_ascii=False, indent=2)[:3000])


def water_soil_zones() -> list[dict[str, Any]]:
    return [
        {
            "zone_id": zid,
            "zone_name": name,
            "land_area": land,
            "surface_water_available": surf,
            "groundwater_available": ground,
            "min_area": round(land * 0.75, 4),
        }
        for zid, name, land, surf, ground in ZONES
    ]


def water_right_zones() -> list[dict[str, Any]]:
    return [
        {
            "zoneId": zid,
            "zoneName": name,
            "landArea": land,
            "surfaceWaterAvailable": surf,
            "groundwaterAvailable": ground,
            "waterDemandM3": round(land * 7200),
            "cropMix": CROP_MIX[zid],
            "waterSavingPotentialM3": round(land * 600),
        }
        for zid, name, land, surf, ground in ZONES
    ]


def ensure_output_dir() -> Path:
    out = Path(os.getenv("MODEL_API_OUTPUT_DIR", "tmp/model_api_tests"))
    out.mkdir(parents=True, exist_ok=True)
    return out
