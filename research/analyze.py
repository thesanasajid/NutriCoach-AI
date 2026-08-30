"""
Statistical analysis of the simulated NutriCoach T2D pilot data.

Demonstrates the pre-specified analysis plan from research/proposal.md:
  1. Baseline characteristics by arm (randomization check)
  2. Primary outcome: 12-week HbA1c change, intervention vs. control
     (Welch two-sample t-test, 95% CI of the difference, Cohen's d)
  3. Secondary outcome: engagement dose-response within the intervention arm
     (linear regression of HbA1c change on messages sent)
  4. Power analysis: required sample size for the definitive trial
     (normal-approximation two-sample design) and achieved power of the pilot
  5. Figures 1-3 (colorblind-safe Okabe-Ito palette)

Run AFTER simulate_data.py:  python research/analyze.py
Outputs: research/output/results.md and fig1-fig3 PNGs.
"""

import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Okabe-Ito colorblind-safe palette; color follows the study arm everywhere.
COL_CONTROL = "#0072B2"       # blue
COL_INTERVENTION = "#E69F00"  # orange
COL_GRID = "#d8dee3"
COL_MUTED = "#5f736e"

FOOTNOTE = "Simulated data (simulate_data.py, seed 42) - methodology demonstration, not clinical evidence."


def style_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(COL_GRID)
    ax.tick_params(colors=COL_MUTED, labelsize=9)
    ax.yaxis.grid(True, color=COL_GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.text(0.01, 0.008, FOOTNOTE, fontsize=7, color=COL_MUTED)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path}")


def welch_ci(a, b, alpha=0.05):
    """Welch t-test with mean difference, 95% CI and Cohen's d (pooled)."""
    t, p = stats.ttest_ind(a, b, equal_var=False)
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    diff = a.mean() - b.mean()
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    ci = (diff - tcrit * se, diff + tcrit * se)
    sp = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = diff / sp
    return {"t": t, "p": p, "df": df, "diff": diff, "ci": ci, "d": d}


def fmt_p(p):
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


# Planning values for the power analysis (documented in proposal §4.3):
# SD of the 12-week HbA1c change, two-sided alpha, target power, dropout reserve.
PLAN_SD, PLAN_ALPHA, PLAN_POWER, PLAN_DROPOUT = 0.6, 0.05, 0.80, 0.20


def required_n_per_arm(delta, sd=PLAN_SD, alpha=PLAN_ALPHA, power=PLAN_POWER):
    """Two-sample normal-approximation sample size per arm."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return int(np.ceil(2 * (z * sd / delta) ** 2))


def achieved_power(delta, n_per_arm, sd=PLAN_SD, alpha=PLAN_ALPHA):
    """Power of a two-sample comparison with n per arm for a true difference delta."""
    ncp = delta / (sd * np.sqrt(2 / n_per_arm))
    return float(stats.norm.cdf(ncp - stats.norm.ppf(1 - alpha / 2)))


def main():
    participants = pd.read_csv(os.path.join(OUT_DIR, "participants.csv"))
    weekly = pd.read_csv(os.path.join(OUT_DIR, "weekly_glucose.csv"))
    ctrl = participants[participants.group == "control"]
    intv = participants[participants.group == "intervention"]

    # ---- 1. Baseline characteristics ------------------------------------
    baseline_rows = []
    for label, df in (("Control", ctrl), ("Intervention", intv)):
        baseline_rows.append({
            "Arm": label, "n": len(df),
            "Age, mean (SD)": f"{df.age.mean():.1f} ({df.age.std():.1f})",
            "Female, n (%)": f"{(df.sex == 'female').sum()} ({100 * (df.sex == 'female').mean():.0f}%)",
            "Baseline HbA1c, mean (SD)": f"{df.baseline_hba1c.mean():.2f} ({df.baseline_hba1c.std():.2f})",
        })
    baseline_tbl = pd.DataFrame(baseline_rows)

    # ---- 2. Primary outcome ---------------------------------------------
    res = welch_ci(intv.delta_hba1c, ctrl.delta_hba1c)

    # ---- 3. Engagement dose-response ------------------------------------
    reg = stats.linregress(intv.messages_total, intv.delta_hba1c)

    # ---- 4. Power analysis ----------------------------------------------
    power_rows = [(d, required_n_per_arm(d), int(np.ceil(required_n_per_arm(d) / (1 - PLAN_DROPOUT))))
                  for d in (0.2, 0.3, 0.4, 0.5)]
    pilot_power = achieved_power(0.3, len(intv))

    # ---- Figure 1: HbA1c change by arm (box + jittered points) ----------
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    rng = np.random.default_rng(1)
    data = [ctrl.delta_hba1c, intv.delta_hba1c]
    colors = [COL_CONTROL, COL_INTERVENTION]
    bp = ax.boxplot(data, positions=[0, 1], widths=0.42, showfliers=False,
                    medianprops=dict(color="#1c2b28", linewidth=1.6),
                    boxprops=dict(color=COL_MUTED), whiskerprops=dict(color=COL_MUTED),
                    capprops=dict(color=COL_MUTED))
    for i, (series, col) in enumerate(zip(data, colors)):
        x = rng.normal(i, 0.055, len(series))
        ax.scatter(x, series, s=22, color=col, alpha=0.55, edgecolors="white", linewidths=0.6, zorder=3)
        ax.text(i, series.mean(), "", va="center")
    for i, series in enumerate(data):
        ax.annotate(f"mean {series.mean():+.2f}", (i + 0.26, series.mean()),
                    fontsize=9, color="#1c2b28", va="center")
    ax.axhline(0, color=COL_MUTED, linewidth=0.9, linestyle="--", alpha=0.7)
    ax.set_xticks([0, 1], [f"Control\n(n={len(ctrl)})", f"Intervention\n(n={len(intv)})"])
    ax.set_ylabel("HbA1c change, week 0 to 12 (percentage points)")
    ax.set_title(f"Welch t-test: difference {res['diff']:+.2f} pp, "
                 f"95% CI [{res['ci'][0]:.2f}, {res['ci'][1]:.2f}], p {fmt_p(res['p'])}",
                 fontsize=9, color=COL_MUTED, pad=10)
    fig.suptitle("Primary outcome: HbA1c change after 12 weeks", fontsize=12, fontweight="bold")
    ax.annotate("lower = improvement", (0.99, 0.02), xycoords="axes fraction",
                ha="right", fontsize=8, color=COL_MUTED)
    style_axes(ax)
    save(fig, "fig1_hba1c_change.png")

    # ---- Figure 2: weekly fasting glucose trajectories -------------------
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for label, col in (("control", COL_CONTROL), ("intervention", COL_INTERVENTION)):
        g = weekly[weekly.group == label].groupby("week")["fasting_glucose_mgdl"]
        mean, sem = g.mean(), g.sem()
        ax.plot(mean.index, mean.values, color=col, linewidth=2, label=label.title())
        ax.fill_between(mean.index, mean - 1.96 * sem, mean + 1.96 * sem, color=col, alpha=0.14, linewidth=0)
        ax.annotate(f" {label.title()}  {mean.iloc[-1]:.0f}", (12, mean.iloc[-1]),
                    color=col, fontsize=9.5, fontweight="bold", va="center")
    ax.set_xlim(0, 14.6)
    ax.set_xticks(range(0, 13, 2))
    ax.set_xlabel("Week")
    ax.set_ylabel("Mean fasting glucose (mg/dL)")
    ax.set_title("Group mean with 95% confidence band", fontsize=9, color=COL_MUTED, pad=10)
    fig.suptitle("Secondary outcome: fasting glucose over the study period", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    style_axes(ax)
    save(fig, "fig2_glucose_trajectory.png")

    # ---- Figure 3: engagement dose-response ------------------------------
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    ax.scatter(intv.messages_total, intv.delta_hba1c, s=26, color=COL_INTERVENTION,
               alpha=0.65, edgecolors="white", linewidths=0.6)
    xs = np.linspace(0, intv.messages_total.max(), 50)
    ax.plot(xs, reg.intercept + reg.slope * xs, color="#1c2b28", linewidth=1.6)
    ax.axhline(0, color=COL_MUTED, linewidth=0.9, linestyle="--", alpha=0.7)
    ax.set_xlabel("Chatbot messages sent over 12 weeks")
    ax.set_ylabel("HbA1c change (percentage points)")
    ax.set_title(f"Slope {reg.slope * 10:+.3f} pp per 10 messages, r = {reg.rvalue:.2f}, p {fmt_p(reg.pvalue)}",
                 fontsize=9, color=COL_MUTED, pad=10)
    fig.suptitle("Engagement dose-response (intervention arm)", fontsize=12, fontweight="bold")
    style_axes(ax)
    save(fig, "fig3_engagement.png")

    # ---- results.md -------------------------------------------------------
    md = f"""# Statistical results - simulated NutriCoach T2D pilot

*Generated by `analyze.py` on {date.today().isoformat()}.*

> **Read this first:** the underlying data are **simulated** (`simulate_data.py`,
> seed 42) with assumed effect sizes. This document demonstrates the pre-specified
> analysis pipeline for the proposed pilot study - it is **not** evidence that the
> chatbot improves outcomes.

## 1. Baseline characteristics (randomization check)

{baseline_tbl.to_markdown(index=False)}

Arms are well balanced at baseline, as expected under randomization.

## 2. Primary outcome - HbA1c change (week 0 to 12)

| Arm | n | Mean change (SD) |
|---|---|---|
| Control | {len(ctrl)} | {ctrl.delta_hba1c.mean():+.2f} ({ctrl.delta_hba1c.std():.2f}) |
| Intervention | {len(intv)} | {intv.delta_hba1c.mean():+.2f} ({intv.delta_hba1c.std():.2f}) |

Welch two-sample t-test (intervention - control):

* Mean difference: **{res['diff']:+.2f} percentage points**
* 95% CI: **[{res['ci'][0]:.2f}, {res['ci'][1]:.2f}]**
* t({res['df']:.1f}) = {res['t']:.2f}, p {fmt_p(res['p'])}
* Effect size (Cohen's d): **{res['d']:.2f}**

Interpretation template: in the simulated data, the intervention arm improved
HbA1c by {abs(res['diff']):.2f} percentage points more than control - a
{'small' if abs(res['d']) < 0.5 else 'moderate' if abs(res['d']) < 0.8 else 'large'}
effect. A reduction of ~0.3-0.5 pp is in the range reported for digital diabetes
interventions and is generally considered clinically relevant.

## 3. Secondary outcome - engagement dose-response (intervention arm)

Linear regression of HbA1c change on total messages sent:

* Slope: **{reg.slope * 10:+.3f} pp per 10 messages** (r = {reg.rvalue:.2f}, r^2 = {reg.rvalue ** 2:.2f}, p {fmt_p(reg.pvalue)})

More engaged participants improved more (by construction of the simulation).
In a real study this association would be observational - engaged users may
differ systematically - so it supports, but cannot prove, a causal dose-response.

## 4. Power analysis - sizing the definitive trial

Planning assumptions: two-sided alpha = {PLAN_ALPHA}, power = {PLAN_POWER:.0%},
SD of the 12-week HbA1c change = {PLAN_SD} pp (planning value, consistent with
this simulation), normal-approximation two-sample formulas.

| Detectable group difference | n per arm | n per arm with {PLAN_DROPOUT:.0%} dropout reserve |
|---|---|---|
""" + "\n".join(f"| {d:.1f} pp | {n} | {n_drop} |" for d, n, n_drop in power_rows) + f"""

For the literature-typical effect of **0.3 pp**, the definitive trial needs about
**{required_n_per_arm(0.3)} participants per arm** (~{int(np.ceil(required_n_per_arm(0.3) / (1 - PLAN_DROPOUT)))}
per arm with dropout reserve). The simulated pilot itself (n = {len(intv)}/arm) has
~{100 * pilot_power:.0f}% power for that effect. (Exact t-based numbers are ~1 higher
per arm than these normal-approximation values.)

## 5. Figures

| File | Shows |
|---|---|
| `fig1_hba1c_change.png` | Primary outcome by arm (box + individual participants) |
| `fig2_glucose_trajectory.png` | Weekly mean fasting glucose with 95% CI bands |
| `fig3_engagement.png` | Engagement vs. HbA1c change with regression line |

## 6. Limitations of this analysis

1. **Simulated data with assumed effects** - the pipeline, not the result, is the contribution.
2. Complete cases only; a real trial needs a dropout/missing-data strategy (e.g. intention-to-treat with multiple imputation).
3. No adjustment for covariates; a real analysis would add baseline-adjusted ANCOVA as sensitivity analysis.
4. Dose-response is correlational even in real data.
"""
    path = os.path.join(OUT_DIR, "results.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {path}")

    print("\n--- Summary (simulated!) ---")
    print(f"dHbA1c control      {ctrl.delta_hba1c.mean():+.2f}")
    print(f"dHbA1c intervention {intv.delta_hba1c.mean():+.2f}")
    print(f"difference {res['diff']:+.2f} pp, 95% CI [{res['ci'][0]:.2f}, {res['ci'][1]:.2f}], "
          f"p {fmt_p(res['p'])}, d = {res['d']:.2f}")
    print(f"dose-response slope {reg.slope * 10:+.3f} pp / 10 messages, p {fmt_p(reg.pvalue)}")
    print(f"power: definitive trial needs ~{required_n_per_arm(0.3)}/arm for 0.3 pp "
          f"(~{int(np.ceil(required_n_per_arm(0.3) / (1 - PLAN_DROPOUT)))} with dropout); "
          f"pilot power for 0.3 pp: {100 * pilot_power:.0f}%")


if __name__ == "__main__":
    main()
