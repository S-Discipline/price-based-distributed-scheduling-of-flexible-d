import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    return mo, np, plt


@app.cell
def _(mo):
    mo.md(r"""
    # TPR approaches a perfect-information scheduler as the community grows

    **Unified verdict: C — partial reproduction success, medium confidence.** A high-utilization sensitivity control measured a
    TPR–oracle gap of **$0.1221 ± $0.0335 per household at $N=5$**, **$0.00373 ±
    $0.00373 at $N=10$**, and numerical zero from **$N=15$**. This is
    decreasing direction consistent with Figure 4 of
    [arXiv:2607.15570](https://www.alphaxiv.org/abs/2607.15570). However, approximate
    relative differences from the paper are 69.5% at $N=5$, 98.1% at $N=10$,
    and nearly 100% at $N=200$, outside the provisional 10% criterion. Only two
    sizes have nonzero means, so the reported exponential rate is not verified.

    This notebook embeds the completed-run summaries. It does **not** rerun the
    remote optimization.
    """)
    return


@app.cell
def _(np):
    # Completed evidence, embedded so the notebook works without repo-relative
    # artifacts or expensive compute.
    n_stress = np.array([5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 175, 200])
    stress_gap = np.array([
        0.1220876820347053, 0.003730374151060367, 1.4210854715202005e-15,
        1.7763568394002505e-15, 9.947598300641404e-16, 1.6579330501069005e-15,
        5.329070518200752e-16, 1.7053025658242406e-15, 2.842170943040401e-15,
        1.4210854715202005e-15, 0.0, 1.7053025658242404e-15,
        1.9489172180848463e-15, 2.2737367544323206e-15,
    ])
    stress_sem = np.array([
        0.03346328544524204, 0.0037303741510579043, 6.80979694255049e-16,
        6.802928764360687e-16, 5.859285502108464e-16, 4.853930953629324e-16,
        2.8642893384395585e-16, 7.338453819646734e-16, 8.05374643242283e-16,
        6.183491098788151e-16, 0.0, 8.288086116269192e-16,
        8.715822764314998e-16, 6.884079889681497e-16,
    ])
    zero_zone = np.array([
        0.064453125, 0.01171875, 0.004557291666666666, 0.0026041666666666665,
        0.0, 0.0006510416666666666, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ])
    paper_n = np.array([5, 50, 200])
    paper_gap_visual = np.array([0.4, 0.004, 1.5e-6])
    return n_stress, paper_gap_visual, paper_n, stress_gap, stress_sem, zero_zone


@app.cell
def _(n_stress, np, paper_gap_visual, paper_n, plt, stress_gap, stress_sem):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    shown = np.maximum(stress_gap, 1e-14)
    ax.errorbar(n_stress, shown, yerr=np.minimum(stress_sem, shown * 0.8),
                color="#2563eb", marker="o", linewidth=2, capsize=3,
                label="Observed high-utilization control (16 seeds)")
    ax.scatter(paper_n, paper_gap_visual, marker="D", s=55, facecolors="white",
               edgecolors="#c2410c", linewidths=1.8,
               label="Paper Figure 4 (approximate visual read)")
    ax.axhline(1e-14, color="#64748b", linestyle="--", linewidth=1.2,
               label="Numerical floor")
    ax.set(xscale="log", yscale="log", xlabel="Community size, N",
           ylabel="TPR − oracle cost per household ($)",
           title="Observed TPR–oracle gap")
    ax.set_ylim(4e-15, 1.2)
    ax.grid(True, color="#dbe3ee", alpha=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Why a three-zone price can work

    At each interval, every active EV has a **mandatory minimum** charge needed
    to meet its deadline and a **feasible maximum** set by charger capacity. TPR
    compares aggregate renewable generation $g_t$ with the sums of those bounds:

    - $g_t < \sum_i m_{i,t}$: broadcast the import price $\pi^+$ and charge only
      mandatory energy.
    - $g_t > \sum_i \bar c_{i,t}$: broadcast the export price $\pi^-$ and charge
      as much as possible.
    - Otherwise: use the NEM price in the net-zero zone and absorb local
      renewable energy.

    The perfect-information oracle solves all charging decisions jointly after
    seeing the future. The experiment measures `(TPR cost − oracle cost) / N`.
    """)
    return


@app.cell
def _(mo):
    view = mo.ui.dropdown(
        options={"Gap to oracle": "gap", "Net-zero-zone frequency": "zone"},
        value="Gap to oracle",
        label="Diagnostic",
    )
    view
    return (view,)


@app.cell
def _(mo, n_stress, np, plt, stress_gap, view, zero_zone):
    if view.value == "gap":
        values = np.maximum(stress_gap, 1e-14)
        ylabel = "Gap per household ($)"
        yscale = "log"
        title = "Finite-size performance gap"
    else:
        values = 100 * zero_zone
        ylabel = "Intervals in net-zero zone (%)"
        yscale = "linear"
        title = "Frequency of the difficult pricing zone"
    interactive_fig, interactive_ax = plt.subplots(figsize=(8, 3.8))
    interactive_ax.plot(n_stress, values, color="#2563eb", marker="o", linewidth=2)
    interactive_ax.set(xscale="log", yscale=yscale, xlabel="Community size, N",
                       ylabel=ylabel, title=title)
    interactive_ax.grid(True, color="#dbe3ee", alpha=0.8)
    interactive_ax.spines[["top", "right"]].set_visible(False)
    interactive_fig.tight_layout()
    mo.vstack([view, interactive_fig])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## What the evidence supports

    | Claim | Assessment | Evidence |
    |---|---|---|
    | TPR gap decreases with community size | **Direction supported only** | Measurable at $N=5$ and $10$; numerical zero from $N=15$ |
    | Revenue adequacy | **Aligned under this setup** | Worst margin $-2.84\times10^{-14}$, within $10^{-10}$ tolerance |
    | Individual rationality | **Aligned under this setup** | Worst saving $-1.42\times10^{-14}$, within tolerance |
    | Paper's magnitudes and exponential rate | **Not verified** | Values differ by far more than 10%; ACN preprocessing and raw Figure 4 values are unavailable |

    The formal runs used a 24-hour, 15-minute horizon, 7.2 kW chargers, a
    six-hour maximum charging window, lognormal renewable generation with mean
    1.6 kWh, and NEM prices of $0.50/$0.20 per kWh. The high-utilization control
    replaces undisclosed ACN preprocessing with jobs that use 85%–100% of their
    feasible charging envelope.
    """)
    return


if __name__ == "__main__":
    app.run()
