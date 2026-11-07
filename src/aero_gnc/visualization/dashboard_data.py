"""Datos del panel: mismo cálculo para el servidor local y el navegador."""

from typing import Dict, Any
import numpy as np

from aero_gnc.config.aircraft_database import get_aircraft, AVAILABLE_AIRCRAFT
from aero_gnc.config.airport_ils import DEFAULT_ILS
from aero_gnc.core.wind_turbulence import WindScenarioConfig
from aero_gnc.control.autopilot_longitudinal import LongitudinalGains
from aero_gnc.control.autopilot_lateral import LateralGains
from aero_gnc.simulator import AeroGNCSimulator, SimulationConfig
from aero_gnc.validation.modal_validation import FlightDynamicsLinearizer

def simulate_dashboard(params: Dict[str, Any]):
    ac_id = str(params.get("aircraft_id", "b737"))
    headwind = float(params.get("headwind", 5.0))
    crosswind = float(params.get("crosswind", 2.0))

    mb_val = params.get("microburst", True)
    if isinstance(mb_val, str):
        microburst = mb_val.lower() in ("true", "1", "yes")
    else:
        microburst = bool(mb_val)

    micro_u = float(params.get("microburst_delta_u", 14.0))
    micro_w = float(params.get("microburst_w_down", 5.5))
    turbulence = float(params.get("turbulence", 0.6))

    # Ganancias opcionales del autopiloto
    kp_pitch = float(params.get("kp_pitch", 1.6))
    kd_pitch = float(params.get("kd_pitch", 0.8))
    kp_roll = float(params.get("kp_roll", 1.8))

    w_cfg = WindScenarioConfig(
        headwind_mean=headwind,
        crosswind_mean=crosswind,
        enable_microburst=microburst,
        microburst_center_x=-1500.0,
        microburst_delta_u=micro_u,
        microburst_w_down=micro_w,
        turbulence_intensity=turbulence,
    )

    sim_cfg = SimulationConfig(
        aircraft_id=ac_id,
        duration_s=65.0,
        dt=0.02,
        initial_dist_m=-3800.0,
        initial_lateral_offset_m=float(params.get("lateral_offset", 18.0)),
        wind_config=w_cfg,
    )

    lon_gains = LongitudinalGains(kp_pitch=kp_pitch, kd_pitch=kd_pitch)
    lat_gains = LateralGains(kp_roll=kp_roll)

    sim = AeroGNCSimulator(config=sim_cfg, lon_gains=lon_gains, lat_gains=lat_gains)
    history, summary = sim.run()

    # Muestreo de datos para transmisión web fluida (paso de 50 ms / 20 Hz es ideal)
    stride = max(1, int(0.05 / sim_cfg.dt))
    sampled_indices = np.arange(0, len(history.time), stride)
    if len(sampled_indices) == 0 or sampled_indices[-1] != len(history.time) - 1:
        sampled_indices = np.append(sampled_indices, len(history.time) - 1)

    times_s = history.time[sampled_indices].tolist()
    states_s = history.state[sampled_indices].tolist()
    ctrls_s = history.controls[sampled_indices].tolist()
    winds_s = history.wind[sampled_indices].tolist()

    telemetry_s = {
        k: [round(float(v), 3) for v in arr[sampled_indices]]
        for k, arr in history.telemetry.items()
    }

    # Serialización de resultados de compuertas
    imc_dict = None
    if summary["imc_gate"]:
        g = summary["imc_gate"]
        imc_dict = {
            "gate_name": g.gate_name,
            "is_stabilized": g.is_stabilized,
            "gs_dots": round(g.gs_dots, 2),
            "loc_dots": round(g.loc_dots, 2),
            "speed_error_kts": round(g.speed_error_kts, 1),
            "descent_rate_fpm": round(g.descent_rate_fpm, 0),
            "discrepancies": g.discrepancies,
        }

    vmc_dict = None
    if summary["vmc_gate"]:
        g = summary["vmc_gate"]
        vmc_dict = {
            "gate_name": g.gate_name,
            "is_stabilized": g.is_stabilized,
            "gs_dots": round(g.gs_dots, 2),
            "loc_dots": round(g.loc_dots, 2),
            "speed_error_kts": round(g.speed_error_kts, 1),
            "descent_rate_fpm": round(g.descent_rate_fpm, 0),
            "discrepancies": g.discrepancies,
        }

    response_data = {
        "status": "success",
        "aircraft": summary["aircraft"],
        "duration_s": summary["duration_simulated_s"],
        "touchdown": summary["touchdown_occurred"],
        "touchdown_info": summary["touchdown_info"],
        "imc_gate": imc_dict,
        "vmc_gate": vmc_dict,
        "total_alerts": summary["total_safety_alerts"],
        "events": summary["events"],
        "data": {
            "time": times_s,
            "state": states_s,
            "controls": ctrls_s,
            "wind": winds_s,
            "telemetry": telemetry_s,
        }
    }
    return response_data


def validate_dashboard(ac_id: str):
    ac = get_aircraft(ac_id)
    lin = FlightDynamicsLinearizer(ac)

    rows_bench = lin.compare_against_reference()
    bench_data = [
        {
            "mode_name": r.mode_name,
            "computed_eigenvalue": f"{r.computed_eigenvalue.real:.4f} + {r.computed_eigenvalue.imag:.4f}j",
            "reference_eigenvalue": f"{r.reference_eigenvalue.real:.4f} + {r.reference_eigenvalue.imag:.4f}j",
            "computed_wn": round(r.computed_wn, 4),
            "reference_wn": round(r.reference_wn, 4),
            "computed_zeta": round(r.computed_zeta, 4),
            "reference_zeta": round(r.reference_zeta, 4),
            "rel_error_wn_percent": round(r.rel_error_wn_percent, 2),
            "rel_error_eigenvalue_percent": round(r.rel_error_eigenvalue_percent, 2),
        }
        for r in rows_bench
    ]

    rows_approx = lin.compare_analytical_approximations()
    approx_data = [
        {
            "mode_name": a.mode_name,
            "exact_4dof_wn": round(a.exact_4dof_wn, 4),
            "approx_2dof_wn": round(a.approx_2dof_wn, 4),
            "exact_4dof_zeta": round(a.exact_4dof_zeta, 4),
            "approx_2dof_zeta": round(a.approx_2dof_zeta, 4),
            "rel_error_wn_percent": round(a.rel_error_wn_percent, 2),
        }
        for a in rows_approx
    ]

    rk_res = lin.verify_integrator_order()

    return {
        "status": "success",
        "aircraft": ac.name,
        "benchmark_comparison": bench_data,
        "analytical_approximations": approx_data,
        "rk4_verification": {
            "estimated_order": round(rk_res["estimated_order"], 2),
            "is_fourth_order": rk_res["is_fourth_order"],
            "final_error_percent": rk_res["final_error_percent"]
        }
    }
