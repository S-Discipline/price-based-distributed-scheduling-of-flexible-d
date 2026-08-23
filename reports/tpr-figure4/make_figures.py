"""Render the evidence figures used by the Figure 4 reproduction report."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
IMAGES = ROOT / "images"
BLUE = "#2563eb"
ORANGE = "#c2410c"
INK = "#172033"
GREY = "#64748b"
GRID = "#dbe3ee"


def read_csv(name: str) -> list[dict[str, float]]:
    with (DATA / name).open(newline="") as handle:
        return [{key: float(value) for key, value in row.items()}
                for row in csv.DictReader(handle)]


def finish(fig: plt.Figure, filename: str) -> None:
    fig.savefig(IMAGES / filename, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def style_axis(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#94a3b8")
    ax.tick_params(colors="#475569")
    ax.grid(True, color=GRID, linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def headline(baseline: list[dict[str, float]], stress: list[dict[str, float]]) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    n = np.array([row["N"] for row in stress])
    gap = np.array([row["gap_mean"] for row in stress])
    sem = np.array([row["gap_sem"] for row in stress])
    shown = np.maximum(gap, 1e-14)
    ax.errorbar(n, shown, yerr=np.minimum(sem, shown * 0.8), color=BLUE,
                marker="o", markersize=5, linewidth=2.2, capsize=3,
                label="Observed: high-utilization control (16 seeds)")
    # Approximate visual reads are deliberately shown as unconnected reference
    # points: the paper does not publish the underlying Figure 4 values.
    ax.scatter([5, 50, 200], [0.4, 0.004, 1.5e-6], marker="D", s=54,
               facecolors="white", edgecolors=ORANGE, linewidths=1.8,
               label="Paper Figure 4 (approximate visual read)")
    ax.axhline(1e-14, color=GREY, linestyle="--", linewidth=1.3,
               label="Numerical floor; baseline repeat lies here")
    ax.annotate("0.1221 ± 0.0335", (5, shown[0]), xytext=(12, 14),
                textcoords="offset points", color=BLUE, fontsize=9)
    ax.annotate("0.00373 ± 0.00373", (10, shown[1]), xytext=(10, 11),
                textcoords="offset points", color=BLUE, fontsize=9)
    ax.annotate("numerical zero from N=15", (15, 1e-14), xytext=(18, 12),
                textcoords="offset points", color=GREY, fontsize=9)
    ax.set(xscale="log", yscale="log", xlabel="Community size, N",
           ylabel="TPR − oracle cost per household ($)",
           title="TPR–oracle gap versus community size")
    ax.set_ylim(4e-15, 1.2)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    style_axis(ax)
    fig.suptitle("Observed decay is qualitatively aligned and faster than the paper",
                 x=0.12, ha="left", fontsize=11, color=INK, y=0.995)
    finish(fig, "headline-gap-comparison.png")


def mechanism(baseline: list[dict[str, float]], stress: list[dict[str, float]]) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    for rows, label, color, marker in [
        (baseline, "Baseline synthetic demand", GREY, "s"),
        (stress, "High-utilization control", BLUE, "o"),
    ]:
        ax.plot([r["N"] for r in rows], [100 * r["zero_zone_mean"] for r in rows],
                color=color, marker=marker, linewidth=2, markersize=5, label=label)
    ax.set(xscale="log", xlabel="Community size, N",
           ylabel="Intervals in net-zero zone (%)",
           title="Net-zero-zone frequency")
    ax.legend(frameon=False)
    style_axis(ax)
    fig.suptitle("The only difficult pricing zone rapidly becomes rare",
                 x=0.12, ha="left", fontsize=11, color=INK, y=0.995)
    finish(fig, "mechanism-zero-zone.png")


def uncertainty(stress_reps: list[dict[str, float]]) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    rng = np.random.default_rng(26071570)
    groups = []
    for position, n in enumerate([5, 10], start=1):
        values = np.array([r["gap_per_household"] for r in stress_reps if r["N"] == n])
        groups.append(values)
        jitter = rng.uniform(-0.08, 0.08, size=len(values))
        ax.scatter(position + jitter, values, color=BLUE, alpha=0.72, s=30,
                   edgecolor="white", linewidth=0.5, zorder=3)
    boxes = ax.boxplot(groups, positions=[1, 2], widths=0.38, patch_artist=True,
                       showfliers=False, medianprops={"color": INK, "linewidth": 1.6})
    for box in boxes["boxes"]:
        box.set(facecolor="#dbeafe", edgecolor=BLUE, linewidth=1.2)
    for key in ("whiskers", "caps"):
        for artist in boxes[key]:
            artist.set(color=BLUE, linewidth=1.1)
    ax.set(xticks=[1, 2], xticklabels=["N = 5", "N = 10"],
           ylabel="Gap per household ($)", title="Seed-to-seed finite-size gaps")
    ax.set_ylim(-0.025, 0.47)
    style_axis(ax)
    fig.suptitle("Finite-size uncertainty is substantial before the gap reaches zero",
                 x=0.12, ha="left", fontsize=11, color=INK, y=0.995)
    finish(fig, "robustness-seed-distribution.png")


def guarantees(base_reps: list[dict[str, float]], stress_reps: list[dict[str, float]]) -> None:
    tolerance = 1e-10
    diagnostics = [
        ("Revenue adequacy\ncoordinator margin", "coordinator_margin_min"),
        ("Individual rationality\nhousehold saving", "min_household_saving"),
    ]
    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    for offset, (label, key) in enumerate(diagnostics):
        for j, (rows, branch, color, marker) in enumerate([
            (base_reps, "Baseline", GREY, "s"),
            (stress_reps, "High utilization", BLUE, "o"),
        ]):
            worst = min(r[key] for r in rows)
            normalized = max(abs(min(worst, 0.0)) / tolerance, 1e-8)
            ax.scatter(offset + (j - 0.5) * 0.18, normalized, s=72, color=color,
                       marker=marker, label=branch if offset == 0 else None, zorder=3)
            ax.annotate(f"{worst:.1e}", (offset + (j - 0.5) * 0.18, normalized),
                        xytext=(0, 8), textcoords="offset points", ha="center",
                        fontsize=8, color=color)
    ax.axhline(1, color=ORANGE, linestyle="--", linewidth=1.5,
               label="Prespecified numerical tolerance (1e−10)")
    ax.set(yscale="log", xticks=[0, 1], xticklabels=[d[0] for d in diagnostics],
           ylabel="Worst apparent violation / tolerance",
           title="Feasibility diagnostics")
    ax.set_ylim(1e-8, 3)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    style_axis(ax)
    fig.suptitle("Both guarantees hold within floating-point tolerance",
                 x=0.12, ha="left", fontsize=11, color=INK, y=0.995)
    finish(fig, "diagnostic-guarantees.png")


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    baseline = read_csv("baseline_scaling_summary.csv")
    stress = read_csv("stress_scaling_summary.csv")
    base_reps = read_csv("baseline_replicates.csv")
    stress_reps = read_csv("stress_replicates.csv")
    headline(baseline, stress)
    mechanism(baseline, stress)
    uncertainty(stress_reps)
    guarantees(base_reps, stress_reps)


if __name__ == "__main__":
    main()
