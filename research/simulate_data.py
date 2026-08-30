"""
Simulated pilot-study data for the NutriCoach T2D proof of concept.

Design being simulated (see research/proposal.md):
  Two-arm randomized pilot, 12 weeks, N = 120 adults with type 2 diabetes.
  - Intervention arm (n=60): usual care + access to the NutriCoach chatbot
  - Control arm (n=60): usual care only
  Primary outcome:   change in HbA1c (%) from week 0 to week 12
  Secondary outcome: weekly mean fasting glucose (mg/dL); chatbot engagement

IMPORTANT: This is SIMULATED data. Effect sizes are assumptions taken from the
digital-diabetes-intervention literature (typical HbA1c reductions of ~0.3-0.5
percentage points), chosen so the analysis pipeline has something realistic to
work on. The purpose is to demonstrate the evaluation METHODOLOGY - the numbers
are not evidence that this chatbot works.

Assumptions (all encoded below, all changeable):
  * Baseline HbA1c ~ Normal(8.0, 0.8), clipped to 6.5-11.0
  * Control change over 12 weeks   ~ Normal(-0.10, 0.60)   (usual-care drift;
    SD ~0.6 matches the within-arm variability reported in real 12-week trials)
  * Intervention change            ~ Normal(-0.25, 0.55) - 0.005 * messages_sent
    (i.e. an engagement dose-response: ~50 messages adds ~-0.25)
  * Fasting glucose tracks HbA1c via the ADAG relation (~28.7 mg/dL per 1% HbA1c)
  * Reproducible: fixed RNG seed 42

Run:  python research/simulate_data.py
Outputs: research/output/participants.csv, research/output/weekly_glucose.csv
"""

import os

import numpy as np
import pandas as pd

SEED = 42
N_PER_ARM = 60
WEEKS = 12
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def simulate() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    n = 2 * N_PER_ARM

    group = rng.permutation(np.array(["intervention"] * N_PER_ARM + ["control"] * N_PER_ARM))
    age = np.clip(rng.normal(58, 9, n), 35, 79).round(0)
    sex = rng.choice(["female", "male"], n)
    baseline_hba1c = np.clip(rng.normal(8.0, 0.8, n), 6.5, 11.0)

    # Chatbot engagement: total messages over 12 weeks (intervention arm only).
    messages = np.where(
        group == "intervention",
        np.clip(rng.lognormal(mean=np.log(50), sigma=0.6, size=n), 2, 220),
        0.0,
    ).round(0)

    # True 12-week change in HbA1c under the assumptions documented above.
    delta = np.where(
        group == "intervention",
        rng.normal(-0.25, 0.55, n) - 0.005 * messages,
        rng.normal(-0.10, 0.60, n),
    )
    week12_hba1c = np.clip(baseline_hba1c + delta, 5.5, None)
    delta = week12_hba1c - baseline_hba1c  # keep delta consistent after clipping

    participants = pd.DataFrame({
        "participant_id": [f"P{i + 1:03d}" for i in range(n)],
        "group": group,
        "age": age.astype(int),
        "sex": sex,
        "baseline_hba1c": baseline_hba1c.round(2),
        "week12_hba1c": week12_hba1c.round(2),
        "delta_hba1c": delta.round(2),
        "messages_total": messages.astype(int),
    })

    # Weekly fasting glucose that drifts in line with each participant's HbA1c
    # trajectory (ADAG: mean glucose changes ~28.7 mg/dL per 1% HbA1c).
    rows = []
    fg_baseline = 130 + 18 * (baseline_hba1c - 7.0) + rng.normal(0, 10, n)
    for week in range(WEEKS + 1):
        fg_week = fg_baseline + (delta * 28.7) * (week / WEEKS) + rng.normal(0, 6, n)
        rows.append(pd.DataFrame({
            "participant_id": participants["participant_id"],
            "group": group,
            "week": week,
            "fasting_glucose_mgdl": fg_week.round(1),
        }))
    weekly = pd.concat(rows, ignore_index=True)

    return participants, weekly


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    participants, weekly = simulate()
    p_path = os.path.join(OUT_DIR, "participants.csv")
    w_path = os.path.join(OUT_DIR, "weekly_glucose.csv")
    participants.to_csv(p_path, index=False)
    weekly.to_csv(w_path, index=False)

    print(f"Simulated {len(participants)} participants over {WEEKS} weeks (seed {SEED}).")
    print(participants.groupby("group")[["baseline_hba1c", "delta_hba1c", "messages_total"]]
          .mean().round(2).to_string())
    print(f"\nWrote {p_path}\nWrote {w_path}")


if __name__ == "__main__":
    main()
