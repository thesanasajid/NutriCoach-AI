"""
Usage analysis from the local chat log - real "user data" statistics.

The chatbot appends every message (text + detected intent, local only) to
data/logs/chat-YYYY-MM-DD.jsonl. This script turns those logs into the
process metrics named in research/proposal.md:

  * intent-category distribution (what people actually ask)
  * fallback rate  - share of messages the bot could not route (key coverage metric)
  * safety rate    - share of messages deflected to human care
  * distinct fallback utterances - concrete knowledge-base gaps to fix next

Unlike the intent evaluation (developer-authored set), these numbers come from
real usage, so they complement the accuracy score with a coverage measure.

Run:  python research/usage_analysis.py
Outputs: research/output/usage_report.md + fig4_usage.png
(Needs matplotlib; runs fine with an empty log - it will just say so.)
"""

import glob
import json
import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

COL_BAR = "#0e7c66"
COL_GRID = "#d8dee3"
COL_MUTED = "#5f736e"

BUCKETS = [
    ("food_lookup", "Food lookup"),
    ("food_compare", "Food comparison"),
    ("swap", "Swap suggestion"),
    ("meal_ideas", "Meal ideas"),
    ("concept", "Concept education"),
    ("safety", "Safety deflection"),
    ("smalltalk", "Small talk"),
    ("fallback", "Not understood (fallback)"),
]


def bucket(intent: str) -> str:
    if intent.startswith("safety"):
        return "safety"
    if intent.startswith("concept"):
        return "concept"
    if intent in ("greeting", "help", "thanks"):
        return "smalltalk"
    if intent in ("food_lookup", "food_compare", "swap", "meal_ideas"):
        return intent
    return "fallback"


def load_entries() -> list:
    entries = []
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "chat-*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip malformed lines rather than fail
    return entries


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    entries = load_entries()
    report_path = os.path.join(OUT_DIR, "usage_report.md")

    if not entries:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Usage report - NutriCoach T2D\n\nNo chat logs found yet "
                    "(`data/logs/`). Use the chatbot for a while, then re-run "
                    "`python research/usage_analysis.py`.\n")
        print("No chat logs yet - use the chatbot first, then re-run. "
              f"Wrote placeholder {report_path}")
        return

    total = len(entries)
    days = sorted({e.get("ts", "")[:10] for e in entries if e.get("ts")})
    counts = {key: 0 for key, _ in BUCKETS}
    fallback_texts = []
    for e in entries:
        b = bucket(str(e.get("intent", "fallback")))
        counts[b] += 1
        if b == "fallback":
            text = str(e.get("message", "")).strip()
            if text and text.lower() not in (t.lower() for t in fallback_texts):
                fallback_texts.append(text)

    fallback_rate = 100 * counts["fallback"] / total
    safety_rate = 100 * counts["safety"] / total

    # ---- figure: intent distribution -------------------------------------
    labels = [label for key, label in BUCKETS if counts[key] > 0]
    values = [counts[key] for key, _ in BUCKETS if counts[key] > 0]
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig, ax = plt.subplots(figsize=(7.0, 0.6 + 0.5 * len(labels)))
    bars = ax.barh(labels, values, color=COL_BAR, height=0.62)
    for bar, v in zip(bars, values):
        ax.annotate(f" {v}", (v, bar.get_y() + bar.get_height() / 2),
                    va="center", fontsize=9.5, color="#1c2b28")
    ax.set_xlabel("Messages")
    ax.set_title(f"{total} messages, {len(days)} day(s) of local logs",
                 fontsize=9, color=COL_MUTED, pad=10)
    fig.suptitle("How the chatbot was used", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(COL_GRID)
    ax.tick_params(colors=COL_MUTED, labelsize=9)
    ax.xaxis.grid(True, color=COL_GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.008, "Local usage log (data/logs) - never leaves this machine.",
             fontsize=7, color=COL_MUTED)
    fig.savefig(os.path.join(OUT_DIR, "fig4_usage.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---- report -----------------------------------------------------------
    lines = [
        "# Usage report - NutriCoach T2D",
        "",
        f"*Generated by `usage_analysis.py` on {date.today().isoformat()} from the local log "
        f"(`data/logs/`, {len(days)} day(s): {days[0]} to {days[-1]}).*",
        "",
        f"**Total messages: {total}**",
        "",
        "| Category | Messages | Share |",
        "|---|---|---|",
    ]
    for key, label in BUCKETS:
        if counts[key]:
            lines.append(f"| {label} | {counts[key]} | {100 * counts[key] / total:.0f}% |")
    lines += [
        "",
        f"* **Fallback rate: {fallback_rate:.1f}%** - share of messages the bot could not route. "
        "This is the key real-world coverage metric (proposal §6, limitation 2).",
        f"* **Safety rate: {safety_rate:.1f}%** - messages deflected to human care as designed.",
        "",
        "## Knowledge-base gaps (distinct fallback utterances)",
        "",
    ]
    if fallback_texts:
        lines += [f"* \"{t}\"" for t in fallback_texts[:10]]
        lines.append("")
        lines.append("Each of these is a concrete candidate for a new food entry or topic.")
    else:
        lines.append("None recorded - no message has hit the fallback yet.")
    lines += ["", "![Usage](fig4_usage.png)"]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{total} messages across {len(days)} day(s); "
          f"fallback rate {fallback_rate:.1f}%, safety rate {safety_rate:.1f}%")
    print(f"Wrote {report_path}")
    print(f"Wrote {os.path.join(OUT_DIR, 'fig4_usage.png')}")


if __name__ == "__main__":
    main()
