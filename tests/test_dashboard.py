"""Regresiones del panel local y del paquete ejecutado en el navegador."""

import json
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

import numpy as np
import pytest

from aero_gnc.visualization.dashboard_data import simulate_dashboard, validate_dashboard

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_uses_selected_aircraft_and_weather():
    calm = simulate_dashboard({"aircraft_id": "c172", "microburst": False, "headwind": 0, "crosswind": 0, "turbulence": 0})
    windy = simulate_dashboard({"aircraft_id": "c172", "microburst": False, "headwind": 7, "crosswind": 3, "turbulence": 0})
    for result in (calm, windy):
        assert result["status"] == "success"
        assert "172" in result["aircraft"]
        data = result["data"]
        assert len(data["time"]) > 10
        assert len(data["time"]) == len(data["state"]) == len(data["wind"])
        assert np.isfinite(data["state"]).all()
        assert np.all(np.diff(data["time"]) > 0)
        json.dumps(result, allow_nan=False)
    assert calm["data"]["wind"] != windy["data"]["wind"]
    assert calm["data"]["state"] != windy["data"]["state"]


@pytest.mark.parametrize("aircraft", ["b737", "c172"])
def test_dashboard_validation(aircraft):
    data = validate_dashboard(aircraft)
    assert data["status"] == "success"
    assert data["benchmark_comparison"]
    assert data["rk4_verification"]["is_fourth_order"]
    json.dumps(data, allow_nan=False)


def test_web_bundle_has_current_python_and_assets():
    with ZipFile(ROOT / "web" / "aero_gnc.zip") as bundle:
        for source in (ROOT / "src" / "aero_gnc").rglob("*.py"):
            assert bundle.read(source.relative_to(ROOT / "src").as_posix()) == source.read_bytes()
    for name in ("index.html", "styles.css", "app.js", "engine.js", "engine-worker.js", "aero_gnc.zip"):
        assert (ROOT / name).read_bytes() == (ROOT / "web" / name).read_bytes()
    for data in (ROOT / "web" / "data").glob("*.json"):
        assert (ROOT / "data" / data.name).read_bytes() == data.read_bytes()


def test_dashboard_javascript_parses():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node no está instalado; esta comprobación se ejecuta al publicar.")
    for script in (ROOT / "web").glob("*.js"):
        subprocess.run([node, "--check", str(script)], check=True, capture_output=True, text=True)
