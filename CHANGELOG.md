# Changelog

## 1.0.1 (2026-08-27) - never fail silently

Triggered by a real failed hand-off: a recipient received only the .exe and
"nothing happened" - with `--noconsole` there was no way to see why.

* **Splash screen** while the exe unpacks, so the first (slow) launch shows
  immediate feedback instead of looking dead.
* **Visible error dialogs** instead of silent exits: startup failures and
  "could not open a window" now show a message box naming the cause and the
  `error.log` path.
* **Double-launch protection**: starting the app twice no longer spawns a
  second server - it just shows the window of the running instance.
* **`START-HIER.txt`** (EN/DE): unpack-first warning, SmartScreen steps,
  the "Unblock" checkbox, and the cross-platform Python fallback.
* Distribution: a second package without the .exe for mail providers that
  block executables (the source version runs on Windows, macOS and Linux).

## 1.0.0 (2026-08-27) - first release-ready version

* **Desktop app**: `NutriCoach.exe` now opens its own app window (no browser
  tabs, no address bar, no console window), with its own icon. The app shuts
  itself down automatically ~2 minutes after the last window is closed.
* **Bilingual**: full English/German support - UI toggle (EN/DE, remembered),
  localized knowledge base (79 foods, 14 topics, meals, safety replies), and
  input understanding in both languages at once (including the safety layer).
* **Visual explainers**: GI position scale (0-100 with low/medium/high zones),
  macro bars (carbs incl. sugar share, fiber, protein) on every food card,
  side-by-side compare cards with a "friendlier choice" marker, and a
  plate-method graphic on meal suggestions.
* **Robustness**: automatic free-port fallback, safe behaviour without a
  console, crash notes to `error.log`, graceful handling of malformed input.
* Licensing (MIT + health notice) and this changelog.

## 0.9 (2026-08-26/27) - proof of concept

* Rule-based bilingual-ready engine with safety-first routing; 79-food
  traffic-light knowledge base; 14 guideline topics.
* Functional evaluation (unit checks + 78-utterance routing accuracy),
  usage-log analysis, simulated pilot study with pre-specified statistics
  (Welch t-test, dose-response, power analysis) and figures.
* Research proposal and presentation slides.
