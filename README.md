# NutriCoach T2D 🥗

A **proof-of-concept AI chatbot for nutrition support in type 2 diabetes** —
rule-based, explainable, bilingual (English/German), fully local, with visual
explainers and a complete simulated-study evaluation pipeline. Ships as a
windowed desktop app for Windows. Built as a small research project.
**Version 1.0.1** · MIT license (see `LICENSE`) · changes in `CHANGELOG.md`.
New here? Read `START-HIER.txt` first (EN/DE launch instructions).

> ⚠️ **Educational prototype only.** Not medical advice, not a medical device.
> It deliberately refuses medication and emergency questions. For personal
> guidance, always consult a doctor or registered dietitian.

## What's inside

| Part | What it does |
|---|---|
| **Chatbot app** | Ask about foods ("Is banana ok?" / "Ist Banane okay?"), compare ("white rice or brown rice?"), get swaps, meal ideas, and concept explanations (glycemic index, plate method, …). Every answer shows its intent and source. Visual explainers: GI position scale, macro bars (carbs/sugar/fiber/protein), compare cards, and a plate-method graphic — plus a traffic-light food browser. |
| **Two languages** | Full English/German support: UI toggle (top right, remembered), localized knowledge base and replies, and input understanding in both languages at once — the safety layer included. Adding a language = adding keys in the JSON files plus one string block in `chatbot/engine.py`. |
| **Safety layer** | Medication, acute-symptom and crisis inputs are detected *before* anything else and answered only with a referral to human care. |
| **Knowledge base** | `data/foods.json` (79 foods: carbs, sugar, fiber, protein, GI, traffic light) and `data/guidelines.json` (14 topics + meal templates, worded along ADA/NHS/Diabetes UK patient guidance). Both are plain JSON — easy to extend. |
| **Research pipeline** | `research/simulate_data.py` generates a simulated 120-person, 12-week randomized pilot; `research/analyze.py` runs the pre-specified statistics (Welch t-test, 95% CI, Cohen's d, dose-response regression, power analysis) and produces publication-style figures. |
| **Evaluation & metrics** | 27 unit checks (`test_engine.py`), a 78-utterance intent-routing evaluation with accuracy report (`research/evaluate_intents.py`), and a usage-log analysis with fallback/safety rates (`research/usage_analysis.py`). |
| **Research proposal** | `research/proposal.md` — research questions, methodology, limitations, ethics. Start reading there. |

## Quick start

**Fastest (Windows, no Python needed):** double-click **`NutriCoach.exe`** —
it opens its own app window (no browser tabs, no console) and quits by itself
about 2 minutes after you close the window. It's an unsigned build, so Windows
may scan it on first launch (a few seconds) and SmartScreen may warn once
("More info" → "Run anyway"). Rebuild it anytime with `build-exe.bat`.

**From source** (Python 3.10+ standard library only):

```
python app.py
```

then open <http://localhost:8765> (it picks the next free port if 8765 is
taken). On Windows you can just double-click `start.bat`.

**Statistics pipeline** (needs the packages from `requirements.txt`):

```
python -m pip install -r requirements.txt
python research/simulate_data.py
python research/analyze.py
python research/usage_analysis.py
```

or double-click `run-analysis.bat`. Results land in `research/output/`
(`results.md` incl. power analysis, `usage_report.md`, four PNG figures,
and the simulated CSV datasets).

**Tests & evaluation** (no extra packages needed):

```
python test_engine.py                     # 40 unit checks incl. German routing (currently 40/40)
python research/evaluate_intents.py       # 78-utterance routing accuracy (currently 100%)
```

## Project structure

```
nutri-coach/
├── NutriCoach.exe          # standalone desktop app (Windows, no Python needed)
├── app.py                  # local server + desktop app shell (stdlib only)
├── icon.ico                # app icon (regenerate: see build-exe.bat)
├── LICENSE / CHANGELOG.md  # MIT + health notice / version history
├── start.bat               # double-click start from source (Windows)
├── run-analysis.bat        # double-click statistics pipeline (Windows)
├── build-exe.bat           # rebuild NutriCoach.exe (uses PyInstaller)
├── test_engine.py          # 40 unit checks (EN + DE)
├── chatbot/
│   └── engine.py           # intent routing + response generation + safety layer
├── data/
│   ├── foods.json          # food knowledge base (traffic lights, GI)
│   ├── guidelines.json     # topics, meal templates, safety replies
│   └── logs/               # local-only usage log (delete anytime; NUTRICOACH_LOG=0 disables)
├── web/
│   └── index.html          # chat UI (single file, no frameworks)
└── research/
    ├── proposal.md         # research questions, methodology, ethics
    ├── evaluation_set.json # 78 utterances with expected routing
    ├── evaluate_intents.py # routing-accuracy report
    ├── usage_analysis.py   # fallback/safety rates from the local chat log
    ├── simulate_data.py    # simulated pilot study (seed 42, assumptions documented)
    ├── analyze.py          # pre-specified statistics + power analysis + figures
    ├── NutriCoach-T2D-slides.pptx  # presentation deck
    └── output/             # generated: CSVs, results.md, evaluation.md, usage_report.md, fig1-4
```

## Why rule-based instead of an LLM?

That question *is* the research angle: in a health context, a curated
rule/knowledge-based agent gives you reproducibility, zero hallucinations,
auditable content, privacy (fully offline) and safety **by construction** —
at the cost of coverage. The proposal (§4.1, §8) frames the natural next step:
a hybrid where an LLM handles language while the curated knowledge base and
safety layer keep control of content.

## Honest labels

* The study data are **simulated** (assumptions documented in
  `simulate_data.py`); they demonstrate the evaluation methodology, not efficacy.
* Nutrition values are approximations compiled from public sources (USDA-style
  tables, international GI tables) for demonstration purposes.

## Extending it

* Add a food: append an object to `data/foods.json` (with `en`/`de` name,
  aliases and note) — it immediately shows up in chat and the side panel.
* Add a topic: append to `topics` in `data/guidelines.json`.
* Add a language: add its key next to `en`/`de` in both JSON files, one STR
  block in `chatbot/engine.py`, and one entry in the `L` object of
  `web/index.html`.
* Change study assumptions: edit the constants at the top of
  `research/simulate_data.py`, re-run both scripts.

## Publishing checklist (before making this public)

1. Have the nutrition content reviewed by a qualified professional (dietitian/clinician).
2. Keep the disclaimer and safety layer intact — they are part of the design, not decoration.
3. The exe is unsigned; for wider distribution consider code signing, or ship the source + `start.bat`.
4. `LICENSE` (MIT + health notice) travels with every copy; update `CHANGELOG.md` per release.
5. Nutrition values are curated approximations — for production, switch to a maintained source (USDA FoodData Central).

*License: free for personal and educational use.*
