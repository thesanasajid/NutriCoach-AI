# NutriCoach T2D — Kurzanleitung für Robin

Das ist der Ernährungs-Chatbot für Typ-2-Diabetes (Proof-of-Concept für Sanas
Forschungsprojekt). Alles läuft lokal, nichts geht ins Internet, alles gratis.

## Starten

* **Am einfachsten:** Doppelklick auf **`NutriCoach.exe`** — braucht kein Python
  und öffnet ein **eigenes App-Fenster** (kein schwarzes Konsolen-Fenster, kein
  Browser-Tab). Nach dem Schließen des Fensters beendet sich das Programm nach
  ca. 2 Minuten von selbst. Beim allerersten Start prüft Windows die Datei kurz
  (ein paar Sekunden Geduld), und SmartScreen warnt einmal, weil sie nicht
  signiert ist: "Weitere Informationen" → "Trotzdem ausführen".
* **Sprache:** Oben rechts im Fenster zwischen **EN / DE** umschalten — die App
  merkt sich die Wahl. Auch die Eingaben verstehen beide Sprachen.
* **Aus dem Quellcode:** Doppelklick auf `start.bat` → <http://localhost:8765>
  (Beenden: Fenster schließen oder Strg+C)
* **Statistik neu rechnen:** Doppelklick auf `run-analysis.bat`
  → Ergebnisse in `research\output\` (results.md mit Power-Analyse,
  Nutzungs-Report, 4 Diagramme)
* **Tests:** `python test_engine.py` (40 Prüfungen inkl. Deutsch, aktuell alle grün)
* **Trefferquote messen:** `python research\evaluate_intents.py`
  (78 Testfragen, aktuell 100 %)
* **Neu als .exe bauen:** Doppelklick auf `build-exe.bat`

## Zum Ausprobieren im Chat (auf Englisch)

* `Is banana ok?` — Ampel-Bewertung eines Lebensmittels
* `white rice or brown rice?` — Vergleich
* `alternative to cornflakes` — Tausch-Vorschläge
* `dinner ideas` — Mahlzeit-Ideen nach Teller-Methode
* `what is the glycemic index?` — Konzept-Erklärung
* `how much insulin should I take?` — wird absichtlich NICHT beantwortet
  (Sicherheits-Schranke, verweist an Ärzte)

## An Sana weitergeben

Das fertige Paket liegt im CEO-GPT unter `shares\nutri-coach-v1.zip`.
Einfach schicken; sie liest dann `README.md` (Überblick + Start) und
`research\proposal.md` (Forschungsfrage, Methodik, Ethik — das Dokument
für den Professor). Zum Vorführen reicht die **NutriCoach.exe** ganz ohne
Python; für die Statistik braucht sie Python 3.10+ und einmal
`run-analysis.bat`. Ihre Präsentation liegt fertig unter
`research\NutriCoach-T2D-slides.pptx`.

Wichtig als fairer Hinweis: Es ist **ihr** Uni-Projekt — sie sollte den Code
und die Methodik verstehen und erklären können. Das README und die
Kommentare im Code sind genau dafür geschrieben.

## Was der Bot bewusst NICHT macht

* Keine Medikamenten-/Insulin-Antworten, keine Notfall-Beratung (verweist an Ärzte)
* Keine echten Patientendaten — die Studie ist simuliert und überall so beschriftet
* Kein Medizinprodukt, überall Disclaimer
