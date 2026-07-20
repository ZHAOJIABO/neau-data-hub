from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path
from urllib import error, request

from common import BASE_URL, IRRIGATION_API_KEY, ensure_output_dir


weather_dir = os.getenv("IRRIGATION_WEATHER_DIR")
if not weather_dir:
    raise SystemExit("Set IRRIGATION_WEATHER_DIR to a directory containing the required weather TIF files.")

files = sorted(Path(weather_dir).glob("*.tif")) + sorted(Path(weather_dir).glob("*.tiff"))
if not files:
    raise SystemExit(f"No TIF files found in {weather_dir}.")

boundary = f"----model-api-{uuid.uuid4().hex}"
parts: list[bytes] = []


def add_field(name: str, value: str) -> None:
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())


def add_file(name: str, path: Path) -> None:
    ctype = mimetypes.guess_type(path.name)[0] or "image/tiff"
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode())
    parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    parts.append(path.read_bytes())
    parts.append(b"\r\n")


add_field("start_date", os.getenv("IRRIGATION_START_DATE", "2025-05-01"))
add_field("initial_sm", os.getenv("IRRIGATION_INITIAL_SM", "0.29"))
add_field("sm_threshold", os.getenv("IRRIGATION_SM_THRESHOLD", "0.32"))
for path in files:
    add_file("weather_files", path)
parts.append(f"--{boundary}--\r\n".encode())

body = b"".join(parts)
req = request.Request(
    f"{BASE_URL}/api/v1/irrigation/predict",
    data=body,
    headers={
        "X-Irrigation-Api-Key": IRRIGATION_API_KEY,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    },
    method="POST",
)

try:
    with request.urlopen(req, timeout=900) as resp:
        content = resp.read()
except error.HTTPError as exc:
    raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')}") from exc

out = ensure_output_dir() / "irrigation_predict_result.zip"
out.write_bytes(content)
print(f"[OK] 灌溉决策预测 ZIP 已保存: {out}")
