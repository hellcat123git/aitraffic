"""
generate_benchmark_report.py — Post-run Markdown report generator.

Reads sumo/output/benchmark_summary.json (created by run_benchmark.py)
and produces JUDGES_REPORT.md with full side-by-side comparison.
"""

import os
import json
import datetime

JSON_PATH   = "sumo/output/benchmark_summary.json"
OUTPUT_MD   = "JUDGES_REPORT.md"
CSV_PATH    = "benchmark_report.csv"


def generate():
    if not os.path.isfile(JSON_PATH):
        print(f"ERROR: {JSON_PATH} not found. Run: python run_benchmark.py first.")
        return

    with open(JSON_PATH) as f:
        d = json.load(f)

    co2_pct  = d.get("co2_improvement_pct", 0)
    wait_pct = d.get("wait_improvement_pct", 0)
    evp_ai   = d.get("ai_evp_response_s", -1)
    evp_b    = d.get("baseline_evp_response_s", -1)

    evp_ai_s  = f"{evp_ai:.1f} s"  if evp_ai  >= 0 else "N/A"
    evp_b_s   = f"{evp_b:.1f} s"   if evp_b   >= 0 else "N/A"
    co2_sign  = "▼" if co2_pct  > 0 else "▲"
    wait_sign = "▼" if wait_pct > 0 else "▲"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# 🏆 AI-Traffic: Judges' Benchmark Report

**Generated:** {now}  
**Simulation Steps:** {d.get('steps_run', 0)}  
**Mode:** Parallel SUMO (Baseline port 8813 · AI port 8814)

---

## Executive Summary

The AI-optimized adaptive signal controller was benchmarked in a **side-by-side
parallel SUMO simulation** against a fixed-time baseline across **{d.get('steps_run',0)} steps**.

| KPI | Baseline | AI-Optimized | Change |
|-----|----------|-------------|--------|
| **CO₂ Emissions** | `{d.get('baseline_co2_mg',0):,.0f} mg` | `{d.get('ai_co2_mg',0):,.0f} mg` | {co2_sign} **{abs(co2_pct):.1f}%** |
| **Avg Wait Time** | `{d.get('baseline_avg_wait_s',0):.2f} s` | `{d.get('ai_avg_wait_s',0):.2f} s` | {wait_sign} **{abs(wait_pct):.1f}%** |
| **EVP Response** | `{evp_b_s}` | `{evp_ai_s}` | Priority Green Wave |

---

## CO₂ Analysis

- **Baseline total:** `{d.get('baseline_co2_mg', 0):,.2f} mg`
- **AI-optimized total:** `{d.get('ai_co2_mg', 0):,.2f} mg`
- **Reduction:** `{co2_pct:.2f}%`

> The AI controller reduces cumulative CO₂ by dynamically minimizing idle engine time,
> prioritizing high-density approaches and eliminating unnecessary fixed-phase wait periods.

---

## Wait Time Analysis

- **Baseline avg:** `{d.get('baseline_avg_wait_s', 0):.3f} s`
- **AI-optimized avg:** `{d.get('ai_avg_wait_s', 0):.3f} s`
- **Reduction:** `{wait_pct:.2f}%`

> Adaptive signal switching (min 10s green, max 30s) with congestion-aware rotation
> ensures vehicles spend minimum time idling.

---

## Emergency Vehicle Preemption (EVP)

| Metric | Baseline | AI-Optimized |
|--------|----------|-------------|
| EVP Response Time | {evp_b_s} | {evp_ai_s} |
| Mechanism | Fixed-cycle delay | Priority Green Wave (immediate) |
| Yellow bypass | No | Yes (life-safety override) |
| Visual highlight | None | Red ring + 200m proximity sensor |

> The AI EVP system grants immediate green to the emergency vehicle approach,
> bypassing normal yellow transitions. The 200m proximity sensor (TraCI junction
> subscribeContext) triggers the override with zero delay.

---

## Methodology

1. **Parallel execution**: Two independent SUMO instances running on ports 8813 (baseline) and 8814 (AI)
2. **Lockstep stepping**: Both instances advance one step simultaneously per iteration
3. **Emergency injection**: Synthetic ambulance (`emergency_car` class) injected at step 300 on `west_to_east` route
4. **Metrics**: Per-step CO₂ (mg/s via `getCO2Emission`) + wait time (`getWaitingTime`) averaged over all vehicles

---

## Files Generated

| File | Description |
|------|-------------|
| `{CSV_PATH}` | Full step-by-step timeseries (baseline vs AI) |
| `{JSON_PATH}` | Final summary metrics |
| `{OUTPUT_MD}` | This report |

---

*AI-Traffic Smart City Orchestrator · SUMO TraCI + YOLOv8 + ESP32*
"""

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[OK] Report written: {OUTPUT_MD}")
    print(f"\n  CO2 Reduction:   {co2_pct:.1f}%")
    print(f"  Wait Reduction:  {wait_pct:.1f}%")
    print(f"  EVP Response:    {evp_ai_s}")


if __name__ == "__main__":
    generate()
