# 🏆 AI-Traffic: Judges' Benchmark Report

**Generated:** 2026-03-23 13:35:23  
**Simulation Steps:** 1000  
**Mode:** Parallel SUMO (Baseline port 8813 · AI port 8814)

---

## Executive Summary

The AI-optimized adaptive signal controller was benchmarked in a **side-by-side
parallel SUMO simulation** against a fixed-time baseline across **1000 steps**.

| KPI | Baseline | AI-Optimized | Change |
|-----|----------|-------------|--------|
| **CO₂ Emissions** | `54,417,560 mg` | `48,355,808 mg` | ▼ **11.1%** |
| **Avg Wait Time** | `3.40 s` | `0.86 s` | ▼ **74.7%** |
| **EVP Response** | `18.0 s` | `9.0 s` | Priority Green Wave |

---

## CO₂ Analysis

- **Baseline total:** `54,417,559.89 mg`
- **AI-optimized total:** `48,355,807.99 mg`
- **Reduction:** `11.14%`

> The AI controller reduces cumulative CO₂ by dynamically minimizing idle engine time,
> prioritizing high-density approaches and eliminating unnecessary fixed-phase wait periods.

---

## Wait Time Analysis

- **Baseline avg:** `3.395 s`
- **AI-optimized avg:** `0.860 s`
- **Reduction:** `74.66%`

> Adaptive signal switching (min 10s green, max 30s) with congestion-aware rotation
> ensures vehicles spend minimum time idling.

---

## Emergency Vehicle Preemption (EVP)

| Metric | Baseline | AI-Optimized |
|--------|----------|-------------|
| EVP Response Time | 18.0 s | 9.0 s |
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
| `benchmark_report.csv` | Full step-by-step timeseries (baseline vs AI) |
| `sumo/output/benchmark_summary.json` | Final summary metrics |
| `JUDGES_REPORT.md` | This report |

---

*AI-Traffic Smart City Orchestrator · SUMO TraCI + YOLOv8 + ESP32*
