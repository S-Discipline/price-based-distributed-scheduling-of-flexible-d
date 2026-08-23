# Reproducing TPR's asymptotic scheduling claim

This repository tests the main illustrative claim in [Price-Based Distributed Scheduling of Flexible Demands in Energy Communities (arXiv:2607.15570)](https://www.alphaxiv.org/abs/2607.15570): the Threshold Pricing Rule's community cost per household approaches a perfect-information oracle as community size grows.

**Assessment: partially aligned.** The disclosed-parameter baseline reached the numerical zero-gap floor at every tested size. A harder synthetic-demand control measured **$0.1221 ± $0.0335 per household at N=5**, **$0.00373 ± $0.00373 at N=10**, and numerical zero from **N=15** onward. The paper's Figure 4 falls from roughly **$0.4** at its smallest community to about **$1.5×10⁻⁶ at N=200** by visual read. The direction and rapid convergence align; the observed decay is faster, and the exact paper rate remains inconclusive without the authors' ACN preprocessing and raw plot data.

We preserved the paper's 24-hour/15-minute horizon, 7.2 kW charger, six-hour maximum charging window, five-hour mean truncated-Gaussian duration, lognormal renewable mean of 1.6 kWh, boundary arrival rate, and NEM prices of $0.50/$0.20 per kWh. We substituted seeded synthetic EV energy because ACN session filtering and preprocessing are not disclosed. Formal runs executed on `root@ssh3.vast.ai:15694`, verified with two RTX 3090 GPUs; the sparse-optimization workload itself is CPU-bound.

- [Read the illustrated claim-by-claim report](reports/tpr-figure4/report.md)
- [Open the self-contained marimo tutorial](notebooks/tpr_figure4_tutorial.py)
- Private-repository notebook commands: `uvx marimo edit notebooks/tpr_figure4_tutorial.py` or `uvx marimo run notebooks/tpr_figure4_tutorial.py`

## Experiment log

| Branch / experiment | Purpose or change | Exact run command | Assessment / outcome | Compute |
|---|---|---|---|---|
| [`main`](https://github.com/S-Discipline/price-based-distributed-scheduling-of-flexible-d/tree/main) | Public landing page, report, figures, data extracts, and notebook | Not run as an experiment (publication surface) | Presentation-only | — |
| [`orx/seeded-synthetic-scaling-evaluation`](https://github.com/S-Discipline/price-based-distributed-scheduling-of-flexible-d/tree/orx/seeded-synthetic-scaling-evaluation) | Formal Figure 4 evaluation with 16 seeds at N=4…256 | `python3 -m pip install --disable-pip-version-check -r requirements.txt && python3 reproduce.py` | Gap at numerical zero for every size; feasibility diagnostics aligned | SSH RTX 3090 host, 21 s |
| [`orx/baseline-full-telemetry-repeat`](https://github.com/S-Discipline/price-based-distributed-scheduling-of-flexible-d/tree/orx/baseline-full-telemetry-repeat) | Instrumentation-only repeat that logs every per-size result | `python3 -m pip install --disable-pip-version-check -r requirements.txt && python3 reproduce.py` | Two identical seeded evaluations confirmed ≤$2.9×10⁻¹⁵ mean gaps and net-zero-zone disappearance | SSH RTX 3090 host, 11 s initial + 8 s confirmation |
| [`orx/high-utilization-finite-gap-control`](https://github.com/S-Discipline/price-based-distributed-scheduling-of-flexible-d/tree/orx/high-utilization-finite-gap-control) | Sensitivity control using 85%–100% of each EV charging envelope | `python3 -m pip install --disable-pip-version-check -r requirements.txt && python3 reproduce.py` | Rapid finite-size decay: $0.1221 → $0.00373 → numerical zero | SSH RTX 3090 host, 16 s |

The detailed report separates paper evidence, observed evidence, substitutions, unattempted claims, compute cost, and the remaining requirements for a full-data reproduction.
