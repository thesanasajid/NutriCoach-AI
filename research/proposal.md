# NutriCoach T2D — Research Proposal & Proof of Concept

**Working title:** *Rule-based conversational AI for nutrition self-management support in type 2 diabetes: a proof of concept with a simulated evaluation pipeline*

**Author:** Sana Sajid
**Version:** 1.0 (proof-of-concept stage)

---

## 1. Background & motivation

Type 2 diabetes (T2D) affects over 500 million people worldwide, and nutrition
is a first-line, continuously relevant part of its management. Yet access to
dietitians is limited, questions arise daily ("Can I eat this? What instead?"),
and generic leaflets do not answer them in the moment. Conversational agents
(chatbots) can close this gap: they are available 24/7, scale at near-zero cost,
and can deliver guideline-based education interactively.

Large language models (LLMs) make such agents easy to build but hard to trust
in a health context: they can hallucinate, their answers are not reproducible,
and their safety cannot be guaranteed by construction. This project therefore
explores the opposite corner of the design space: a **fully rule- and
knowledge-based agent** whose every answer is grounded in a curated,
guideline-derived knowledge base, whose routing decisions are transparent,
and whose safety behaviour (never answering medication or emergency
questions) is guaranteed by code rather than by prompt.

## 2. Research questions

**RQ1 (feasibility/artifact):** Can a lightweight rule-based conversational
agent deliver guideline-concordant, explainable nutrition guidance for adults
with T2D across the most common everyday question types (food evaluation,
food comparison, substitution, meal ideas, concept education)?

**RQ2 (safety by construction):** Can a deterministic safety layer reliably
detect and deflect out-of-scope requests (medication dosing, acute symptoms,
crisis situations) to human care?

**RQ3 (evaluation methodology):** How should the effect of such an agent on
glycemic control be evaluated in a pilot randomized controlled trial, and what
does the corresponding statistical analysis pipeline look like end-to-end?
*(Answered here on simulated data.)*

## 3. Hypotheses (for the simulated pilot, RQ3)

* **H1:** Participants with chatbot access show a larger 12-week reduction in
  HbA1c than usual-care controls.
* **H2:** Within the intervention arm, higher engagement (messages sent) is
  associated with larger HbA1c reduction (dose-response).

## 4. Methodology

The project follows a **design-science approach**: build the artifact, evaluate
it functionally, and demonstrate the clinical evaluation methodology on
simulated data.

### 4.1 The artifact (chatbot)

| Component | Implementation |
|---|---|
| Knowledge base | `data/foods.json`: 79 foods with macronutrients per 100 g, glycemic index (GI), and a traffic-light rating (green/yellow/red) curated for T2D everyday choices; `data/guidelines.json`: 14 education topics + meal templates, worded along ADA/NHS/Diabetes UK patient guidance |
| NLU / routing | Deterministic intent routing (`chatbot/engine.py`): normalized whole-phrase matching over food aliases and topic keywords, with a fixed priority order (safety → small talk → food intents → meal ideas → concepts → fallback) |
| Response generation | Template-based, grounded exclusively in the knowledge base; every response reports its detected **intent** and **source** in the UI (explainability) |
| Safety layer | Keyword/pattern detectors for medication, acute-symptom and crisis inputs, checked **before** all other routing; these intents return referral messages only, never content |
| Interface | Local web app (Python standard library server + single-page UI) with persistent disclaimer, traffic-light food browser, suggestion chips, bilingual UI (EN/DE, remembered toggle) and visual explainers (GI position scale, macro bars, compare cards, plate-method graphic); also packaged as a windowed desktop executable |
| Privacy | Fully local; no cloud calls; optional local-only usage log for interaction analysis |

Rationale for rule-based over LLM: reproducibility (same input → same output),
zero hallucination risk, auditable knowledge, safety by construction, and no
data leaving the device — properties that map directly onto the requirements
of health-adjacent software. The trade-off (limited coverage) is measured by
the fallback rate and discussed in §6.

### 4.2 Functional evaluation (RQ1, RQ2)

Two complementary layers:

1. **Unit checks** (`test_engine.py`, 40 checks): correct routing per question
   type in both languages, alias robustness (incl. "sugar free" / "blood sugar"
   disambiguation and German umlaut handling), priority of the safety layer
   over all content intents (e.g. *"how much insulin should I take with
   dinner"* must route to safety, not meal ideas), knowledge-base integrity
   and bilingual completeness, disclaimer on every response.
   **Current result: 40/40 passed.**
2. **Intent-routing accuracy** on a 78-utterance evaluation set spanning all
   intent families (`research/evaluation_set.json`, runner
   `research/evaluate_intents.py`; report in `research/output/evaluation.md`).
   **Current result: 78/78 = 100%.** Honest caveat: the set is
   developer-authored, not held out from real users, so this is an upper
   bound; the real-world complement is the **fallback rate** computed from the
   local usage log (`research/usage_analysis.py`).

### 4.3 Simulated pilot & statistical analysis plan (RQ3)

**Design being simulated:** two-arm randomized pilot, N = 120 (60/60),
12 weeks. Intervention: usual care + chatbot access; control: usual care.

**Outcomes:** primary — HbA1c change week 0→12; secondary — weekly fasting
glucose; process — engagement (messages sent).

**Simulation:** `research/simulate_data.py` (fixed seed, all assumptions
documented in-file). Assumed effects are taken from the digital diabetes
intervention literature (≈ −0.3 to −0.5 percentage points HbA1c) with
realistic between-subject variability (SD ≈ 0.6).

**Pre-specified analysis** (`research/analyze.py`):

1. Baseline characteristics by arm (randomization check)
2. **H1:** Welch two-sample t-test on ΔHbA1c, 95% CI of the group difference, Cohen's d
3. **H2:** linear regression of ΔHbA1c on messages sent (intervention arm)
4. Power analysis: required sample size for the definitive trial (normal
   approximation), achieved power of the pilot
5. Figures: outcome distribution by arm, glucose trajectories with 95% CI bands, dose-response scatter

Results of the demonstration run: `research/output/results.md`
(difference −0.37 pp, 95% CI [−0.59, −0.16], p < 0.001, d = −0.63;
dose-response slope −0.064 pp per 10 messages, p = 0.005 — **simulated**).
Trial sizing: a definitive trial needs **~63 participants per arm** to detect
0.3 pp (α = 0.05, power 80%, SD 0.6; ~79 per arm with 20% dropout reserve);
the pilot itself has ~78% power for that effect.

## 5. Deliverables

Working local chatbot + knowledge base (also packaged as a standalone Windows
executable that runs without Python), 27-check test suite, 78-utterance
routing evaluation with accuracy report, usage-log analysis (fallback/safety
rates), simulation + analysis pipeline with power calculation and figures,
presentation slides, and this proposal.

## 6. Limitations

1. **The pilot data are simulated.** The contribution of §4.3 is the
   *methodology and pipeline*, not evidence of efficacy. Any real effect claim
   requires the actual trial.
2. **Coverage:** a rule-based agent only answers what its knowledge base
   contains; out-of-vocabulary foods and free-form questions hit the fallback.
   The fallback rate on real user input is a key metric for the next stage.
3. **Nutrition values are approximations** compiled for demonstration; a real
   deployment would use a maintained source (e.g. USDA FoodData Central API).
4. **No personalization:** guidance is population-level education; individual
   targets, comorbidities and medication interactions are explicitly out of scope.
5. Two languages (English/German; further locales are a JSON-plus-strings
   addition); single-user, no authentication — appropriate for a PoC only.
6. In a real trial, the dose-response analysis (H2) is observational and
   confounded by user motivation; causal claims require design-level answers
   (e.g. randomized encouragement).

## 7. Ethics & privacy

* **No real patient data** are used anywhere in this project; all study data are simulated.
* The prototype displays a persistent disclaimer, is not a medical device, and
  refuses medication/emergency questions by construction.
* All processing is local; no user input leaves the device. A real study would
  additionally require: ethics-board approval, informed consent, GDPR-compliant
  data handling, clinical review of all content by a qualified professional,
  and a defined adverse-event pathway.

## 8. Future work

1. Real-user pilot (with the governance of §7) measuring fallback rate,
   satisfaction and guideline concordance rated by dietitians.
2. Hybrid architecture: LLM for language understanding **constrained to** the
   curated knowledge base for content (retrieval-augmented, with the same
   safety layer) — enabling a rule-based vs. hybrid comparison study.
3. Integration of a maintained food database (USDA FoodData Central) and
   additional languages beyond the shipped EN/DE.
4. The actual RCT designed in §4.3.

## 9. References (indicative)

* American Diabetes Association. *Standards of Care in Diabetes.* (annual)
* ADA — *Diabetes Plate Method* patient education materials.
* Davies MJ et al. *Management of hyperglycaemia in type 2 diabetes — ADA/EASD consensus report.* Diabetologia/Diabetes Care, 2022.
* Atkinson FS, Foster-Powell K, Brand-Miller JC. *International tables of glycemic index and glycemic load values.* Diabetes Care, 2008 (updated 2021).
* Evert AB et al. *Nutrition therapy for adults with diabetes or prediabetes: a consensus report.* Diabetes Care, 2019.
* Lean MEJ et al. *Primary care-led weight management for remission of type 2 diabetes (DiRECT).* Lancet, 2018.
* Nathan DM et al. *Translating the A1C assay into estimated average glucose values (ADAG).* Diabetes Care, 2008.
* Greenwood DA et al. *A systematic review of reviews evaluating technology-enabled diabetes self-management education and support.* J Diabetes Sci Technol, 2017.
