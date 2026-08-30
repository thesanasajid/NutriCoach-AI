"""
NutriCoach T2D - rule-based, bilingual (EN/DE) chat engine.

Design rationale (relevant for the research write-up):
This engine is deliberately rule/retrieval-based rather than an LLM. Every answer
is grounded in a curated knowledge base (data/foods.json, data/guidelines.json),
the routing decision is transparent (each response reports its detected intent
and source), behaviour is deterministic and reproducible, and a safety layer
guarantees that medication/emergency questions are never answered with content.
These properties - explainability, groundedness, safety by construction - are
hard to guarantee with generative models and are a core argument of the
proof of concept (see research/proposal.md).

Internationalization: the knowledge base stores every user-facing text in both
languages ({"en": ..., "de": ...}); matching (food aliases, topic keywords,
safety patterns) always runs over BOTH languages, while the response is rendered
in the language requested per message (reply(message, lang)). Adding another
language = adding keys in the JSON files plus one STR block below.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

LANGS = ("en", "de")
LIGHT_RANK = {"green": 0, "yellow": 1, "red": 2}

# ------------------------------------------------------------------ templates

STR = {
    "en": {
        "disclaimer": ("Research prototype for education only - not medical advice. "
                       "Always consult your doctor or a registered dietitian for personal guidance."),
        "light_word": {"green": "GREEN", "yellow": "YELLOW", "red": "RED"},
        "light_label": {"green": "GREEN - good everyday choice",
                        "yellow": "YELLOW - fine in moderate portions",
                        "red": "RED - occasional treat, keep portions small"},
        "gi_negligible": "Glycemic index: negligible (little to no available carbohydrate).",
        "gi_line": "Glycemic index: {gi} ({band}).",
        "gi_short_negligible": "GI negligible",
        "gi_short": "GI {gi} ({band})",
        "band": {"low": "low", "medium": "medium", "high": "high"},
        "card": ("**{name}** ({cat}), per 100 g: {carbs} g carbs (of which {sugar} g sugar), "
                 "{fiber} g fiber, {protein} g protein, {kcal} kcal. {gi}"),
        "compare_head": "Comparing per 100 g:",
        "compare_win": "**{name}** is the friendlier choice for blood glucose here.",
        "compare_tie": "Both are in the same league - portion size matters more than the choice here.",
        "swap_head": "Gentler alternatives to **{name}** (same category, lower glucose impact):",
        "swap_tail": "Swapping one habitual food is more sustainable than overhauling everything at once.",
        "swap_none": "**{name}** is already {word} - no swap needed. {note}",
        "meal_more": "Ask for a specific meal (breakfast, lunch, dinner, snack) for more options.",
        "meal_label": {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "snack": "Snack"},
        "greeting": ("Hi! I'm **NutriCoach T2D**, a research prototype for nutrition questions around type 2 diabetes.\n\n"
                     "You can ask me things like:\n"
                     "• *\"Is banana ok?\"* - traffic-light check for a food\n"
                     "• *\"White rice or brown rice?\"* - compare two foods\n"
                     "• *\"Swap for white bread\"* - gentler alternatives\n"
                     "• *\"Breakfast ideas\"* - meal suggestions\n"
                     "• *\"What is the glycemic index?\"* - concepts explained\n\n"
                     "I don't answer medication or emergency questions - those belong with your care team."),
        "thanks": "You're welcome! Small consistent steps beat perfect plans - come back anytime.",
        "fallback": ("I didn't find that in my knowledge base - I'm a small prototype with a limited menu. I can:\n"
                     "• Rate a food: *\"Is banana ok?\"*\n"
                     "• Compare: *\"white rice or brown rice?\"*\n"
                     "• Suggest swaps: *\"alternative to cornflakes\"*\n"
                     "• Give meal ideas: *\"dinner ideas\"*\n"
                     "• Explain concepts: *carbs, glycemic index, fiber, plate method, fruit, drinks, alcohol, exercise, weight...*"),
        "src_kb": "Food knowledge base (USDA-derived approximations; GI: Atkinson et al.)",
        "src_plate": "ADA Diabetes Plate Method",
        "sugg_greeting": ["Is banana ok?", "Breakfast ideas", "What is the glycemic index?", "Swap for white rice"],
        "sugg_food": ["Swap for {name}", "Show meal ideas", "What is the glycemic index?"],
        "sugg_compare": ["Swap for {a}", "Is {b} ok?", "Show meal ideas"],
        "sugg_swap": ["Is {name} ok?", "Show meal ideas"],
        "sugg_meal": ["Breakfast ideas", "Lunch ideas", "Dinner ideas", "Snack ideas"],
        "sugg_fallback": ["Is banana ok?", "Dinner ideas", "What is the glycemic index?"],
        "sugg_safety": ["Is banana ok?", "What is the glycemic index?", "Dinner ideas"],
        "sugg_acute": ["What is the plate method?", "Breakfast ideas"],
        "sugg_topic": {
            "glycemic_index": ["Is watermelon ok?", "Swap for white bread", "What is fiber?"],
            "carbs": ["What is the glycemic index?", "What is the plate method?", "Lentils or white rice?"],
            "plate_method": ["Dinner ideas", "Is broccoli ok?", "How much fruit is ok?"],
            "fruit": ["Is banana ok?", "Are dates ok?", "Snack ideas"],
            "drinks": ["Is orange juice ok?", "Cola or diet cola?"],
            "_default": ["Is banana ok?", "Meal ideas", "What is the plate method?"],
        },
    },
    "de": {
        "disclaimer": ("Forschungs-Prototyp, nur zur Bildung - keine medizinische Beratung. "
                       "Besprich persönliche Fragen immer mit Arzt/Ärztin oder Ernährungsberatung."),
        "light_word": {"green": "GRÜN", "yellow": "GELB", "red": "ROT"},
        "light_label": {"green": "GRÜN - gute Alltagswahl",
                        "yellow": "GELB - okay in moderaten Portionen",
                        "red": "ROT - Ausnahme, Portion klein halten"},
        "gi_negligible": "Glykämischer Index: vernachlässigbar (kaum verwertbare Kohlenhydrate).",
        "gi_line": "Glykämischer Index: {gi} ({band}).",
        "gi_short_negligible": "GI vernachlässigbar",
        "gi_short": "GI {gi} ({band})",
        "band": {"low": "niedrig", "medium": "mittel", "high": "hoch"},
        "card": ("**{name}** ({cat}), pro 100 g: {carbs} g Kohlenhydrate (davon {sugar} g Zucker), "
                 "{fiber} g Ballaststoffe, {protein} g Eiweiß, {kcal} kcal. {gi}"),
        "compare_head": "Vergleich pro 100 g:",
        "compare_win": "**{name}** ist hier die freundlichere Wahl für den Blutzucker.",
        "compare_tie": "Beide liegen in derselben Liga - die Portionsgröße zählt hier mehr als die Auswahl.",
        "swap_head": "Sanftere Alternativen zu **{name}** (gleiche Kategorie, weniger Blutzucker-Wirkung):",
        "swap_tail": "Ein einzelnes Gewohnheits-Lebensmittel zu tauschen ist nachhaltiger, als alles auf einmal umzustellen.",
        "swap_none": "**{name}** ist schon {word} - kein Tausch nötig. {note}",
        "meal_more": "Frag nach einer bestimmten Mahlzeit (Frühstück, Mittagessen, Abendessen, Snack) für mehr Ideen.",
        "meal_label": {"breakfast": "Frühstück", "lunch": "Mittagessen", "dinner": "Abendessen", "snack": "Snack"},
        "greeting": ("Hallo! Ich bin **NutriCoach T2D**, ein Forschungs-Prototyp für Ernährungsfragen rund um Typ-2-Diabetes.\n\n"
                     "Du kannst mich zum Beispiel fragen:\n"
                     "• *\"Ist Banane okay?\"* - Ampel-Check für ein Lebensmittel\n"
                     "• *\"Reis oder Vollkornreis?\"* - zwei Lebensmittel vergleichen\n"
                     "• *\"Tausch für Weißbrot\"* - sanftere Alternativen\n"
                     "• *\"Frühstücksideen\"* - Mahlzeiten-Vorschläge\n"
                     "• *\"Was ist der glykämische Index?\"* - Konzepte erklärt\n\n"
                     "Medikamenten- und Notfall-Fragen beantworte ich nicht - die gehören zu deinem Behandlungsteam."),
        "thanks": "Gern! Kleine, beständige Schritte schlagen perfekte Pläne - komm jederzeit wieder.",
        "fallback": ("Das habe ich in meiner Wissensbasis nicht gefunden - ich bin ein kleiner Prototyp mit begrenztem Menü. Ich kann:\n"
                     "• Ein Lebensmittel bewerten: *\"Ist Banane okay?\"*\n"
                     "• Vergleichen: *\"Reis oder Vollkornreis?\"*\n"
                     "• Tausch-Ideen geben: *\"Alternative zu Cornflakes\"*\n"
                     "• Mahlzeiten vorschlagen: *\"Ideen fürs Abendessen\"*\n"
                     "• Konzepte erklären: *Kohlenhydrate, glykämischer Index, Ballaststoffe, Teller-Methode, Obst, Getränke, Alkohol, Bewegung, Gewicht...*"),
        "src_kb": "Lebensmittel-Wissensbasis (USDA-Näherungen; GI: Atkinson et al.)",
        "src_plate": "ADA-Teller-Methode",
        "sugg_greeting": ["Ist Banane okay?", "Frühstücksideen", "Was ist der glykämische Index?", "Tausch für Weißbrot"],
        "sugg_food": ["Tausch für {name}", "Zeig mir Essensideen", "Was ist der glykämische Index?"],
        "sugg_compare": ["Tausch für {a}", "Ist {b} okay?", "Zeig mir Essensideen"],
        "sugg_swap": ["Ist {name} okay?", "Zeig mir Essensideen"],
        "sugg_meal": ["Frühstücksideen", "Ideen fürs Mittagessen", "Ideen fürs Abendessen", "Snack-Ideen"],
        "sugg_fallback": ["Ist Banane okay?", "Ideen fürs Abendessen", "Was ist der glykämische Index?"],
        "sugg_safety": ["Ist Banane okay?", "Was ist der glykämische Index?", "Ideen fürs Abendessen"],
        "sugg_acute": ["Was ist die Teller-Methode?", "Frühstücksideen"],
        "sugg_topic": {
            "glycemic_index": ["Ist Wassermelone okay?", "Tausch für Weißbrot", "Was sind Ballaststoffe?"],
            "carbs": ["Was ist der glykämische Index?", "Was ist die Teller-Methode?", "Linsen oder Reis?"],
            "plate_method": ["Ideen fürs Abendessen", "Ist Brokkoli okay?", "Wie viel Obst ist okay?"],
            "fruit": ["Ist Banane okay?", "Sind Datteln okay?", "Snack-Ideen"],
            "drinks": ["Ist Orangensaft okay?", "Cola oder Cola Zero?"],
            "_default": ["Ist Banane okay?", "Essensideen", "Was ist die Teller-Methode?"],
        },
    },
}

DISCLAIMER = STR["en"]["disclaimer"]  # backwards-compatible export

# ------------------------------------------------------- matching vocabulary
# All patterns below are written in normalized form (see _norm: lowercase,
# umlauts transliterated, punctuation stripped). Matching runs over BOTH
# languages at once, so mixed input still routes correctly.

GREETING_WORDS = {"hi", "hello", "hey", "hallo", "good morning", "good evening", "good afternoon", "yo", "hiya",
                  "guten morgen", "guten tag", "guten abend", "moin", "servus", "gruess gott"}
THANKS_WORDS = {"thanks", "thank you", "thx", "danke", "great thanks", "cool thanks", "vielen dank", "dankeschoen", "danke schoen"}
HELP_WORDS = {"help", "what can you do", "who are you", "what are you", "how do you work", "menu", "options",
              "hilfe", "was kannst du", "wer bist du", "wie funktionierst du"}

SWAP_KEYWORDS = ["instead of", "alternative to", "alternatives to", "alternative for", "alternative", "swap",
                 "replace", "substitute", "healthier than", "better option than",
                 "statt", "anstatt", "anstelle", "ersatz", "ersetzen", "tausch", "tauschen", "austauschen",
                 "alternativen", "gesuender als"]
MEAL_KEYWORDS = {
    "breakfast": ["breakfast", "morning meal", "fruehstueck", "fruehstuecksideen", "morgens"],
    "lunch": ["lunch", "midday meal", "mittagessen", "mittag"],
    "dinner": ["dinner", "supper", "evening meal", "abendessen", "abendbrot"],
    "snack": ["snack", "snacks", "snacking", "between meals", "craving", "cravings",
              "zwischenmahlzeit", "zwischendurch", "heisshunger", "snack ideen"],
}
GENERIC_MEAL_KEYWORDS = ["meal", "meals", "what should i eat", "what can i eat", "what to eat", "meal plan",
                         "recipe", "recipes", "ideas", "hungry", "cook",
                         "mahlzeit", "mahlzeiten", "rezept", "rezepte", "ideen", "hungrig",
                         "was soll ich essen", "was kann ich essen", "essensideen", "kochen"]

# Safety layer - checked before anything else, in both languages.
CRISIS_PATTERNS = ["suicide", "suicidal", "self harm", "kill myself", "end my life", "hurt myself",
                   "selbstmord", "suizid", "umbringen", "selbstverletzung", "nicht mehr leben", "ritzen"]
MEDICATION_PATTERNS = [
    "insulin", "metformin", "medication", "medications", "medicine", "meds",
    "dose", "doses", "dosage", "units", "tablet", "tablets", "pill", "pills",
    "ozempic", "semaglutide", "wegovy", "trulicity", "glipizide", "gliclazide",
    "jardiance", "empagliflozin", "sitagliptin", "prescription", "injection",
    "medikament", "medikamente", "tablette", "tabletten", "dosis", "dosierung",
    "einheiten", "spritze", "spritzen", "verschrieben", "verschreibung",
]
ACUTE_PATTERNS = [
    "hypo", "hypoglycemia", "hypoglycaemia", "hyperglycemia", "shaky", "shaking",
    "dizzy", "sweaty", "sweating a lot", "confused", "passed out", "unconscious",
    "faint", "fainted", "chest pain", "emergency", "blurry", "blurry vision",
    "mg/dl", "mmol",
    "unterzucker", "unterzuckerung", "ueberzucker", "zittrig", "zittern",
    "schwindlig", "schwindel", "ohnmaechtig", "bewusstlos", "brustschmerzen",
    "notfall", "verschwommen",
]

# Phrases in which the word "sugar"/"Zucker" does not refer to the food.
SUGAR_GUARDS = ["sugar free", "no sugar", "without sugar", "unsweetened", "blood sugar", "sugar level",
                "sugar levels", "zuckerfrei", "zuckerfreie", "zuckerfreier", "zuckerfreies", "ohne zucker"]

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _norm(text: str) -> str:
    """Lowercase, transliterate German umlauts, strip punctuation, collapse spaces."""
    text = text.lower().translate(_UMLAUTS)
    text = re.sub(r"[^a-z0-9%/ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_phrase(text: str, phrase: str) -> bool:
    """Whole-word phrase match ('rice' should not match 'price')."""
    return f" {phrase} " in f" {text} "


def _lang(lang: str) -> str:
    return lang if lang in LANGS else "en"


class ChatEngine:
    def __init__(self, data_dir: str = DATA_DIR):
        with open(os.path.join(data_dir, "foods.json"), encoding="utf-8") as f:
            self.foods = json.load(f)["foods"]
        with open(os.path.join(data_dir, "guidelines.json"), encoding="utf-8") as f:
            g = json.load(f)
        self.topics = g["topics"]
        self.meals = g["meals"]
        self.safety = g["safety"]
        self.categories = g["categories"]

        # Alias lookup over BOTH languages, longest alias first so
        # "peanut butter" wins over "peanut" and "vollkornreis" over "reis".
        self._aliases = []
        for food in self.foods:
            seen = set()
            for lang in LANGS:
                for alias in food["aliases"].get(lang, []):
                    a = _norm(alias)
                    for variant in {a, a + "s"} if lang == "en" and not a.endswith("s") else {a}:
                        if variant and variant not in seen:
                            seen.add(variant)
                            self._aliases.append((variant, food))
        self._aliases.sort(key=lambda pair: len(pair[0]), reverse=True)

        # Topic keywords, normalized, both languages merged per topic.
        self._topic_keywords = {
            t["id"]: sorted({_norm(k) for lang in LANGS for k in t["keywords"].get(lang, [])})
            for t in self.topics
        }

    # ------------------------------------------------------------------ public

    def reply(self, message: str, lang: str = "en") -> dict:
        """Route a user message to an intent and build a grounded response in `lang`."""
        lang = _lang(lang)
        text = _norm(message or "")
        if not text:
            return self._fallback(lang)

        # 1. Safety layer first - it must win over every other route.
        if any(_has_phrase(text, p) for p in CRISIS_PATTERNS):
            return self._resp(lang, "safety_crisis", self.safety["crisis"][lang], sources=[])
        if any(_has_phrase(text, p) for p in ACUTE_PATTERNS):
            return self._resp(lang, "safety_acute", self.safety["acute"][lang], sources=[],
                              suggestions=STR[lang]["sugg_acute"])
        if any(_has_phrase(text, p) for p in MEDICATION_PATTERNS):
            return self._resp(lang, "safety_medication", self.safety["medication"][lang], sources=[],
                              suggestions=STR[lang]["sugg_safety"])

        # 2. Small talk.
        if text in GREETING_WORDS or (len(text.split()) <= 3 and any(text.startswith(w) for w in GREETING_WORDS)):
            return self._greeting(lang)
        if text in THANKS_WORDS or any(_has_phrase(text, w) for w in THANKS_WORDS):
            return self._resp(lang, "thanks", STR[lang]["thanks"], sources=[],
                              suggestions=STR[lang]["sugg_fallback"])
        if text in HELP_WORDS or any(w in text for w in ("what can you do", "how do you work", "was kannst du", "wie funktionierst du")):
            return self._greeting(lang, intent="help")

        # 3. Food-centric intents.
        found = self._find_foods(text)
        if found and any(_has_phrase(text, g) for g in SUGAR_GUARDS):
            found = [f for f in found if f["id"] != "sugar"]
        if found and any(k in f" {text} " for k in SWAP_KEYWORDS):
            return self._swap(found[0], lang)
        if len(found) >= 2:
            return self._compare(found[0], found[1], lang)
        if len(found) == 1:
            return self._food_card(found[0], lang)

        # 4. Meal ideas.
        for meal, kws in MEAL_KEYWORDS.items():
            if any(_has_phrase(text, k) for k in kws):
                return self._meal_ideas(meal, lang)
        if any(_has_phrase(text, k) or (" " in k and k in text) for k in GENERIC_MEAL_KEYWORDS):
            return self._meal_ideas(None, lang)

        # 5. Concept/topic questions - score by total matched keyword length.
        best, best_score = None, 0
        for topic in self.topics:
            score = sum(len(k) for k in self._topic_keywords[topic["id"]]
                        if _has_phrase(text, k) or (" " in k and k in text))
            if score > best_score:
                best, best_score = topic, score
        if best:
            sugg = STR[lang]["sugg_topic"].get(best["id"], STR[lang]["sugg_topic"]["_default"])
            return self._resp(lang, "concept:" + best["id"], best["reply"][lang],
                              sources=[best["source"]], suggestions=sugg)

        return self._fallback(lang)

    def food_list(self, lang: str = "en") -> list:
        """Full food table for the UI side panel, localized."""
        lang = _lang(lang)
        return [
            {"name": self._name(f, lang), "category": self.categories[f["category"]][lang],
             "carbs_g": f["carbs_g"], "gi": f["gi"], "light": f["light"]}
            for f in sorted(self.foods, key=lambda f: (LIGHT_RANK[f["light"]], f["category"], f["name"]["en"]))
        ]

    # ----------------------------------------------------------------- intents

    def _greeting(self, lang: str, intent: str = "greeting") -> dict:
        return self._resp(lang, intent, STR[lang]["greeting"], sources=[],
                          suggestions=STR[lang]["sugg_greeting"])

    def _food_card(self, food: dict, lang: str) -> dict:
        t = STR[lang]
        name = self._name(food, lang)
        reply = t["card"].format(
            name=name, cat=self.categories[food["category"]][lang],
            carbs=self._fmt(food["carbs_g"]), sugar=self._fmt(food["sugar_g"]),
            fiber=self._fmt(food["fiber_g"]), protein=self._fmt(food["protein_g"]),
            kcal=round(food["kcal"]), gi=self._gi_text(food, lang),
        ) + f"\n\n{t['light_label'][food['light']]}.\n\n{food['note'][lang]}"
        return self._resp(lang, "food_lookup", reply, sources=[t["src_kb"]],
                          card=self._card(food, lang),
                          suggestions=[s.format(name=name) for s in t["sugg_food"]])

    def _compare(self, a: dict, b: dict, lang: str) -> dict:
        t = STR[lang]

        def line(f):
            return (f"• **{self._name(f, lang)}**: {self._fmt(f['carbs_g'])} g "
                    f"{'carbs' if lang == 'en' else 'KH'} / 100 g, {self._gi_short(f, lang)}, "
                    f"{t['light_word'][f['light']]}")

        winner = self._better(a, b)
        if winner is None:
            verdict = t["compare_tie"]
        else:
            verdict = t["compare_win"].format(name=self._name(winner, lang)) + f"\n\n{winner['note'][lang]}"
        reply = f"{t['compare_head']}\n{line(a)}\n{line(b)}\n\n{verdict}"
        resp = self._resp(lang, "food_compare", reply, sources=[t["src_kb"]],
                          suggestions=[s.format(a=self._name(a, lang), b=self._name(b, lang))
                                       for s in t["sugg_compare"]])
        resp["cards"] = [self._card(a, lang), self._card(b, lang)]  # for the UI's compare visual
        if winner is not None:
            resp["winner"] = self._name(winner, lang)
        return resp

    def _swap(self, food: dict, lang: str) -> dict:
        t = STR[lang]
        candidates = [
            f for f in self.foods
            if f["category"] == food["category"] and f["id"] != food["id"]
            and (LIGHT_RANK[f["light"]] < LIGHT_RANK[food["light"]]
                 or (LIGHT_RANK[f["light"]] == LIGHT_RANK[food["light"]] and (f["gi"] or 0) < (food["gi"] or 0)))
        ]
        candidates.sort(key=lambda f: (LIGHT_RANK[f["light"]], f["gi"] if f["gi"] is not None else 0))
        if not candidates:
            reply = t["swap_none"].format(name=self._name(food, lang),
                                          word=t["light_word"][food["light"]], note=food["note"][lang])
            return self._resp(lang, "swap", reply, sources=[t["src_kb"]],
                              suggestions=STR[lang]["sugg_topic"]["_default"])
        lines = [f"• **{self._name(f, lang)}** - {self._gi_short(f, lang)}, {t['light_word'][f['light']]}. "
                 f"{f['note'][lang].split('.')[0]}." for f in candidates[:3]]
        reply = t["swap_head"].format(name=self._name(food, lang)) + "\n" + "\n".join(lines) + "\n\n" + t["swap_tail"]
        return self._resp(lang, "swap", reply, sources=[t["src_kb"]],
                          suggestions=[s.format(name=self._name(candidates[0], lang)) for s in t["sugg_swap"]])

    def _meal_ideas(self, meal, lang: str) -> dict:
        t = STR[lang]
        intro = self.meals["intro"][lang]
        if meal:
            ideas = self.meals[meal][lang]
            reply = f"{intro}\n\n**{t['meal_label'][meal]}:**\n" + "\n".join(f"• {i}" for i in ideas)
        else:
            reply = (intro + "\n\n"
                     + "\n".join(f"**{t['meal_label'][m]}:** {self.meals[m][lang][0]}"
                                 for m in ("breakfast", "lunch", "dinner", "snack"))
                     + "\n\n" + t["meal_more"])
        return self._resp(lang, "meal_ideas", reply, sources=[t["src_plate"]],
                          suggestions=t["sugg_meal"])

    def _fallback(self, lang: str) -> dict:
        return self._resp(lang, "fallback", STR[lang]["fallback"], sources=[],
                          suggestions=STR[lang]["sugg_fallback"])

    # ----------------------------------------------------------------- helpers

    def _name(self, food: dict, lang: str) -> str:
        return food["name"]["en"].title() if lang == "en" else food["name"]["de"]

    def _find_foods(self, text: str) -> list:
        found, working = [], f" {text} "
        for alias, food in self._aliases:
            if f" {alias} " in working and food not in found:
                found.append(food)
                working = working.replace(f" {alias} ", " ")
        return found

    def _better(self, a: dict, b: dict):
        ra, rb = LIGHT_RANK[a["light"]], LIGHT_RANK[b["light"]]
        if ra != rb:
            return a if ra < rb else b
        ga = a["gi"] if a["gi"] is not None else 0
        gb = b["gi"] if b["gi"] is not None else 0
        if abs(ga - gb) < 5:
            return None
        return a if ga < gb else b

    def _gi_text(self, food: dict, lang: str) -> str:
        t = STR[lang]
        if food["gi"] is None:
            return t["gi_negligible"]
        return t["gi_line"].format(gi=food["gi"], band=t["band"][self._gi_band(food["gi"])])

    def _gi_short(self, food: dict, lang: str) -> str:
        t = STR[lang]
        if food["gi"] is None:
            return t["gi_short_negligible"]
        return t["gi_short"].format(gi=food["gi"], band=t["band"][self._gi_band(food["gi"])])

    @staticmethod
    def _gi_band(gi: int) -> str:
        return "low" if gi <= 55 else ("medium" if gi <= 69 else "high")

    @staticmethod
    def _fmt(x) -> str:
        return str(int(x)) if float(x).is_integer() else f"{x:.1f}"

    def _card(self, food: dict, lang: str) -> dict:
        return {"name": self._name(food, lang), "category": self.categories[food["category"]][lang],
                "kcal": food["kcal"], "carbs_g": food["carbs_g"], "sugar_g": food["sugar_g"],
                "fiber_g": food["fiber_g"], "protein_g": food["protein_g"],
                "gi": food["gi"], "light": food["light"]}

    @staticmethod
    def _resp(lang: str, intent: str, reply: str, sources: list,
              card: dict | None = None, suggestions: list | None = None) -> dict:
        return {"reply": reply, "intent": intent, "lang": lang, "sources": sources,
                "card": card, "suggestions": suggestions or [], "disclaimer": STR[lang]["disclaimer"]}
