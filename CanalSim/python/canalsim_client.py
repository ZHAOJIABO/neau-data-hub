"""
canalsim_client.py - Python wrapper for the CanalSim CLI.

Usage:

    from canalsim_client import run

    cfg = {
        "channel": {"L": 5000, "nx": 51, "b": 5, ...},
        "solver":  {"theta": 0.5, ...},
        "branches":[{"x_position": 1000, "Q_offtake": 3}, ...]
    }
    result = run(cfg, workdir="runs/demo")
    print(result["summary"], result["final_state"]["Q"][:5])

Or from the command line:

    python python/canalsim_client.py configs/example_input.json runs/demo
"""
from __future__ import annotations

import json
import pathlib
import platform
import subprocess
import sys
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent

# Default executable path; can be overridden by passing exe=...
_DEFAULT_EXE = _ROOT / ("canalsim.exe" if platform.system() == "Windows" else "canalsim")


def run(input_cfg: dict[str, Any],
        workdir: str | pathlib.Path = ".",
        exe: str | pathlib.Path | None = None,
        timeout_s: float | None = None,
        keep_files: bool = True) -> dict[str, Any]:
    """Run a CanalSim simulation.

    Parameters
    ----------
    input_cfg  : dict with keys 'channel', 'solver', 'branches'
    workdir    : directory where input.json / result.json will be written
    exe        : path to canalsim executable; default = <repo>/canalsim[.exe]
    timeout_s  : optional subprocess timeout
    keep_files : if False, delete input.json / result.json afterwards

    Returns
    -------
    dict parsed from result.json
    """
    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    in_path  = workdir / "input.json"
    out_path = workdir / "result.json"

    in_path.write_text(json.dumps(input_cfg, indent=2), encoding="utf-8")

    exe_path = pathlib.Path(exe) if exe else _DEFAULT_EXE
    if not exe_path.exists():
        raise FileNotFoundError(f"canalsim executable not found: {exe_path}")

    proc = subprocess.run(
        [str(exe_path), str(in_path), str(out_path)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"canalsim failed (exit {proc.returncode}):\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )

    result = json.loads(out_path.read_text(encoding="utf-8"))

    if not keep_files:
        in_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

    return result


def main() -> int:
    """CLI: python canalsim_client.py <input.json> <workdir>"""
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    in_path  = pathlib.Path(sys.argv[1])
    workdir  = pathlib.Path(sys.argv[2])
    cfg = json.loads(in_path.read_text(encoding="utf-8"))
    result = run(cfg, workdir=workdir)
    summary = result.get("summary", {})
    print("Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"Timeseries length: {len(result.get('timeseries', {}).get('t', []))}")
    print(f"Final state nodes: {len(result.get('final_state', {}).get('x', []))}")
    print(f"Branches: {len(result.get('branches', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
