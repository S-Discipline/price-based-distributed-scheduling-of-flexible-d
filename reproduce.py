"""Claim-level reproduction of arXiv:2607.15570, Figure 4.

The implementation preserves every simulation parameter disclosed in the paper.
Because neither the plotted data nor the ACN preprocessing is published, EV
energy is sampled from a seeded synthetic truncated duration-demand model. The
perfect-information lower bound is solved as a sparse linear program.
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


def _ensure_dependencies():
    """Install pinned wheels only when the execution image lacks them."""
    try:
        import matplotlib  # noqa: F401
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ModuleNotFoundError:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--break-system-packages",
            "numpy==2.2.6", "scipy==1.15.3", "matplotlib==3.10.3",
        ])
        os.execv(sys.executable, [sys.executable, *sys.argv])


_ensure_dependencies()

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.optimize import linprog  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"


@dataclass(frozen=True)
class Job:
    household: int
    arrival: int
    deadline: int
    demand: float


def payment(z: np.ndarray | float, p_import: float, p_export: float):
    z = np.asarray(z)
    return np.where(z >= 0, p_import * z, p_export * z)


def make_instance(n: int, rng: np.random.Generator, cfg: dict):
    t_max = cfg["horizon_intervals"]
    cbar = cfg["charger_kw"] * cfg["interval_hours"]
    max_duration = cfg["max_duration_intervals"]
    alpha = cfg["renewable_mean_kwh"] / (cbar * max_duration)
    jobs: list[Job] = []
    # Occupancy is action-independent. A charger becomes available immediately
    # after its deadline, matching the paper's Bernoulli-at-empty-charger model.
    for i in range(n):
        available = 0
        for t in range(t_max):
            if t < available or rng.random() >= alpha:
                continue
            duration = int(np.clip(round(rng.normal(
                cfg["mean_duration_intervals"], cfg["sd_duration_intervals"]
            )), 4, max_duration))
            if t + duration > t_max:
                continue
            # Stress/control substitution for undisclosed ACN preprocessing:
            # jobs use 85--100% of their feasible charging envelope.
            utilization = rng.uniform(
                cfg["synthetic_utilization_min"],
                cfg["synthetic_utilization_max"],
            )
            demand = float(cbar * duration * utilization)
            jobs.append(Job(i, t, t + duration - 1, demand))
            available = t + duration

    sigma = cfg["renewable_lognormal_sigma"]
    mu = math.log(cfg["renewable_mean_kwh"]) - 0.5 * sigma * sigma
    renewable = rng.lognormal(mu, sigma, size=(n, t_max))
    return jobs, renewable


def oracle_cost(jobs: list[Job], renewable: np.ndarray, cfg: dict) -> float:
    """Perfect-information open-loop lower bound used by the paper."""
    t_max = cfg["horizon_intervals"]
    cbar = cfg["charger_kw"] * cfg["interval_hours"]
    arcs: list[tuple[int, int]] = []
    for j, job in enumerate(jobs):
        arcs.extend((j, t) for t in range(job.arrival, job.deadline + 1))
    n_arc = len(arcs)
    n_var = n_arc + 2 * t_max  # charging arcs, import, export
    c = np.zeros(n_var)
    c[n_arc:n_arc + t_max] = cfg["nem_import_price"]
    c[n_arc + t_max:] = -cfg["nem_export_price"]

    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    b = np.zeros(len(jobs) + t_max)
    b[:len(jobs)] = [j.demand for j in jobs]
    b[len(jobs):] = renewable.sum(axis=0)
    for k, (j, t) in enumerate(arcs):
        rows.extend((j, len(jobs) + t))
        cols.extend((k, k))
        vals.extend((1.0, 1.0))
    for t in range(t_max):
        # sum(charging) - import + export = renewable
        rows.extend((len(jobs) + t, len(jobs) + t))
        cols.extend((n_arc + t, n_arc + t_max + t))
        vals.extend((-1.0, 1.0))
    a_eq = coo_matrix((vals, (rows, cols)), shape=(len(jobs) + t_max, n_var)).tocsr()
    bounds = [(0.0, cbar)] * n_arc + [(0.0, None)] * (2 * t_max)
    result = linprog(c, A_eq=a_eq, b_eq=b, bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"Oracle LP did not solve: {result.message}")
    return float(result.fun)


def schedule(jobs: list[Job], renewable: np.ndarray, cfg: dict, mode: str):
    """Run TPR or stand-alone NEM procrastination schedules pathwise."""
    n, t_max = renewable.shape
    cbar = cfg["charger_kw"] * cfg["interval_hours"]
    p_plus = cfg["nem_import_price"]
    p_minus = cfg["nem_export_price"]
    by_arrival: dict[int, list[int]] = {}
    for idx, job in enumerate(jobs):
        by_arrival.setdefault(job.arrival, []).append(idx)
    remaining = np.zeros(len(jobs))
    charges = np.zeros((n, t_max))
    household_payments = np.zeros(n)
    coordinator_margin_min = float("inf")
    zone_counts = np.zeros(3, dtype=int)  # consuming, zero, producing
    active: list[int] = []

    for t in range(t_max):
        for idx in by_arrival.get(t, []):
            remaining[idx] = jobs[idx].demand
            active.append(idx)
        m = np.zeros(n)
        upper = np.zeros(n)
        active_now = []
        for idx in active:
            job = jobs[idx]
            if remaining[idx] <= 1e-9:
                continue
            slots_after = job.deadline - t
            m[job.household] = max(0.0, remaining[idx] - cbar * slots_after)
            upper[job.household] = min(cbar, remaining[idx])
            active_now.append(idx)
        active = active_now
        local_p = np.clip(renewable[:, t], m, upper)

        if mode == "nem":
            action = local_p
            individual = payment(action - renewable[:, t], p_plus, p_minus)
            household_payments += individual
        else:
            g = float(renewable[:, t].sum())
            if g < m.sum() - 1e-12:
                action = m
                individual = p_plus * (action - renewable[:, t])
                zone_counts[0] += 1
            elif g > upper.sum() + 1e-12:
                action = upper
                individual = p_minus * (action - renewable[:, t])
                zone_counts[2] += 1
            else:
                action = local_p
                individual = payment(action - renewable[:, t], p_plus, p_minus)
                zone_counts[1] += 1
            household_payments += individual
            utility_bill = float(payment(action.sum() - g, p_plus, p_minus))
            interval_margin = float(individual.sum()) - utility_bill
            coordinator_margin_min = min(coordinator_margin_min, interval_margin)

        charges[:, t] = action
        for idx in active:
            h = jobs[idx].household
            remaining[idx] = max(0.0, remaining[idx] - action[h])
        for idx in active:
            if t == jobs[idx].deadline and remaining[idx] > 1e-6:
                raise RuntimeError(f"Missed deadline by {remaining[idx]:.6g} kWh")

    community_cost = float(payment(
        charges.sum(axis=0) - renewable.sum(axis=0), p_plus, p_minus
    ).sum())
    return {
        "community_cost": community_cost,
        "household_payments": household_payments,
        "coordinator_margin_min": coordinator_margin_min,
        "zone_counts": zone_counts,
    }


def summarize(rows: list[dict]):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["N"], []).append(row)
    summary = []
    for n, group in sorted(grouped.items()):
        gaps = np.array([r["gap_per_household"] for r in group])
        zero = np.array([r["zero_zone_fraction"] for r in group])
        runtimes = np.array([r["runtime_seconds"] for r in group])
        summary.append({
            "N": n,
            "gap_mean": float(gaps.mean()),
            "gap_sem": float(gaps.std(ddof=1) / math.sqrt(len(gaps))),
            "zero_zone_mean": float(zero.mean()),
            "runtime_mean": float(runtimes.mean()),
        })
    return summary


def write_csv(name: str, rows: list[dict]):
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_results(summary: list[dict], rows: list[dict]):
    plt.style.use("seaborn-v0_8-whitegrid")
    n = np.array([r["N"] for r in summary])
    gap = np.array([r["gap_mean"] for r in summary])
    sem = np.array([r["gap_sem"] for r in summary])
    zero = np.array([r["zero_zone_mean"] for r in summary])
    runtime = np.array([r["runtime_mean"] for r in summary])

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.errorbar(n, np.maximum(gap, 1e-8), yerr=sem, marker="o", capsize=3, color="#0f766e")
    ax.set(xscale="log", yscale="log", xlabel="Community size N",
           ylabel="TPR − Oracle cost per household ($)",
           title="Headline result: TPR approaches the perfect-information lower bound")
    fig.tight_layout(); fig.savefig(OUT / "headline_gap.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(n, zero, marker="o", color="#7c3aed")
    ax.set(xscale="log", xlabel="Community size N", ylabel="Fraction of intervals",
           title="Mechanism: the suboptimal net-zero pricing zone becomes rare")
    fig.tight_layout(); fig.savefig(OUT / "zero_zone.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(n, runtime, marker="o", color="#b45309")
    ax.set(xscale="log", yscale="log", xlabel="Community size N",
           ylabel="Wall time per replicate (s)", title="Oracle evaluation cost grows with community size")
    fig.tight_layout(); fig.savefig(OUT / "runtime.png", dpi=180); plt.close(fig)

    margins = np.array([r["coordinator_margin_min"] for r in rows])
    ir = np.array([r["min_household_saving"] for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    axes[0].hist(margins, bins=24, color="#2563eb"); axes[0].axvline(0, color="black", lw=1)
    axes[0].set(title="Revenue adequacy", xlabel="Coordinator margin ($)", ylabel="Replicates")
    axes[1].hist(ir, bins=24, color="#16a34a"); axes[1].axvline(0, color="black", lw=1)
    axes[1].set(title="Individual rationality", xlabel="Minimum household saving ($)")
    fig.tight_layout(); fig.savefig(OUT / "guarantee_diagnostics.png", dpi=180); plt.close(fig)


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    OUT.mkdir(exist_ok=True)
    rows = []
    for n in cfg["community_sizes"]:
        for rep in range(cfg["replicates"]):
            start = time.perf_counter()
            rng = np.random.default_rng(cfg["seed"] + 1009 * n + rep)
            jobs, renewable = make_instance(n, rng, cfg)
            oracle = oracle_cost(jobs, renewable, cfg)
            tpr = schedule(jobs, renewable, cfg, "tpr")
            nem = schedule(jobs, renewable, cfg, "nem")
            elapsed = time.perf_counter() - start
            savings = nem["household_payments"] - tpr["household_payments"]
            gap = max(0.0, (tpr["community_cost"] - oracle) / n)
            rows.append({
                "N": n, "replicate": rep, "jobs": len(jobs),
                "oracle_cost": oracle, "tpr_cost": tpr["community_cost"],
                "gap_per_household": gap,
                "zero_zone_fraction": tpr["zone_counts"][1] / cfg["horizon_intervals"],
                "coordinator_margin_min": tpr["coordinator_margin_min"],
                "min_household_saving": float(savings.min()),
                "runtime_seconds": elapsed,
            })
        print(f"completed N={n}", flush=True)
    summary = summarize(rows)
    write_csv("replicates.csv", rows)
    write_csv("scaling_summary.csv", summary)
    plot_results(summary, rows)

    positive = [(r["N"], r["gap_mean"]) for r in summary if r["gap_mean"] > 1e-7]
    slope = float(np.polyfit([math.log2(x) for x, _ in positive],
                             [math.log(y) for _, y in positive], 1)[0]) if len(positive) > 1 else float("nan")
    min_margin = min(r["coordinator_margin_min"] for r in rows)
    min_saving = min(r["min_household_saving"] for r in rows)
    print("\n=== CLAIM SUMMARY ===")
    print(f"paper_claim=TPR gap to Oracle decays approximately exponentially with N")
    print(f"observed_gap_N{summary[0]['N']}={summary[0]['gap_mean']:.8f}")
    print(f"observed_gap_N{summary[-1]['N']}={summary[-1]['gap_mean']:.8f}")
    print(f"log_gap_slope_per_doubling={slope:.6f}")
    print(f"zero_zone_fraction_N{summary[0]['N']}={summary[0]['zero_zone_mean']:.6f}")
    print(f"zero_zone_fraction_N{summary[-1]['N']}={summary[-1]['zero_zone_mean']:.6f}")
    print(f"minimum_coordinator_margin={min_margin:.10f}")
    print(f"minimum_household_saving_vs_NEM={min_saving:.10f}")
    print(f"replicates_per_N={cfg['replicates']}")
    print(f"total_replicates={len(rows)}")
    print("substitution=seeded high-utilization synthetic EV demand; ACN preprocessing and paper point values unavailable")
    print("summary_json=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    print("diagnostics_json=" + json.dumps({
        "minimum_coordinator_margin": min_margin,
        "minimum_household_saving_vs_nem": min_saving,
        "max_gap_per_household": max(r["gap_per_household"] for r in rows),
        "nonzero_gap_replicates": sum(r["gap_per_household"] > 1e-10 for r in rows),
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
