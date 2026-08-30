"""
Functional evaluation of the NutriCoach T2D engine.

Doubles as the "functional test set" referenced in research/proposal.md:
each case is a realistic user utterance with the expected routing decision.
Run:  python test_engine.py   (no extra packages needed)
"""

import sys

from chatbot.engine import ChatEngine, LIGHT_RANK

engine = ChatEngine()
passed, failed = 0, 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


def route(msg):
    return engine.reply(msg)


print("== intent routing ==")
r = route("hi")
check("greeting", r["intent"] == "greeting", r["intent"])

r = route("Is banana ok?")
check("food lookup: banana", r["intent"] == "food_lookup" and r["card"]["name"] == "Banana", r["intent"])
check("banana card has carbs", r["card"]["carbs_g"] == 23)

r = route("how many carbs are in white rice")
check("food lookup beats concept keyword 'carbs'", r["intent"] == "food_lookup" and r["card"]["name"] == "White Rice", r["intent"])

r = route("is wholemeal bread fine for me")
check("alias: wholemeal bread -> whole grain bread", r["intent"] == "food_lookup" and r["card"]["name"] == "Whole Grain Bread", r["intent"])

r = route("white rice or brown rice?")
check("compare two foods", r["intent"] == "food_compare", r["intent"])
check("compare verdict favors brown rice", r.get("winner") == "Brown Rice", str(r.get("winner")))
check("compare returns two cards for the UI", len(r.get("cards", [])) == 2)

r = route("alternative to cornflakes")
check("swap intent", r["intent"] == "swap", r["intent"])
check("swap suggests a low-GI grain", "Barley" in r["reply"] or "Bulgur" in r["reply"], r["reply"][:200])

r = route("swap for white bread")
check("swap keyword 'swap'", r["intent"] == "swap", r["intent"])

r = route("breakfast ideas please")
check("meal ideas: breakfast", r["intent"] == "meal_ideas" and "Greek yogurt" in r["reply"], r["intent"])

r = route("what is the glycemic index?")
check("concept: glycemic index", r["intent"] == "concept:glycemic_index", r["intent"])

r = route("can i drink alcohol with diabetes")
check("concept: alcohol wins over drinks", r["intent"] == "concept:alcohol", r["intent"])

r = route("thanks!")
check("thanks", r["intent"] == "thanks", r["intent"])

r = route("what can you do")
check("help", r["intent"] == "help", r["intent"])

r = route("xylophone quantum blockchain")
check("fallback on out-of-scope input", r["intent"] == "fallback", r["intent"])

print("== safety layer ==")
r = route("how much insulin should I take with dinner")
check("medication question -> safety (not meal_ideas)", r["intent"] == "safety_medication", r["intent"])
check("medication reply defers to clinicians", "doctor" in r["reply"].lower())

r = route("should I change my metformin dose if I eat low carb")
check("medication beats low-carb topic", r["intent"] == "safety_medication", r["intent"])

r = route("my blood sugar is 300 mg/dl what should i eat")
check("acute reading -> safety_acute", r["intent"] == "safety_acute", r["intent"])

r = route("i feel shaky and dizzy after skipping lunch")
check("acute symptoms -> safety_acute", r["intent"] == "safety_acute", r["intent"])

print("== edge cases ==")
r = route("are sugar free drinks okay")
check("'sugar free' not misread as the food sugar", r["intent"] == "concept:drinks", r["intent"])

r = route("is sugar free cola ok")
check("sugar free cola -> diet cola", r["intent"] == "food_lookup" and r["card"]["name"] == "Diet Cola", r["intent"])

r = route("does banana raise blood sugar")
check("'blood sugar' not misread as the food sugar", r["intent"] == "food_lookup" and r["card"]["name"] == "Banana", r["intent"])

print("== german routing ==")
r = engine.reply("Ist Banane okay?", "de")
check("de: food lookup Banane", r["intent"] == "food_lookup" and r["card"]["name"] == "Banane", r["intent"])
check("de: reply is German", "Kohlenhydrate" in r["reply"], r["reply"][:80])

r = engine.reply("Weißbrot oder Vollkornbrot?", "de")
check("de: compare with umlauts", r["intent"] == "food_compare" and r.get("winner") == "Vollkornbrot", str(r.get("winner")))

r = engine.reply("Alternative zu Cornflakes", "de")
check("de: swap", r["intent"] == "swap", r["intent"])

r = engine.reply("Frühstücksideen", "de")
check("de: breakfast ideas", r["intent"] == "meal_ideas" and "Joghurt" in r["reply"], r["intent"])

r = engine.reply("Was ist der glykämische Index?", "de")
check("de: concept glycemic index", r["intent"] == "concept:glycemic_index", r["intent"])

r = engine.reply("Wie viel Insulin soll ich spritzen?", "de")
check("de: medication -> safety, German reply", r["intent"] == "safety_medication" and "Arzt" in r["reply"], r["intent"])

r = engine.reply("mir ist schwindlig und ich zittere", "de")
check("de: acute symptoms -> safety", r["intent"] == "safety_acute", r["intent"])

r = engine.reply("sind zuckerfreie getränke okay", "de")
check("de: 'zuckerfrei' not misread as food sugar", r["intent"] == "concept:drinks", r["intent"])

r = engine.reply("hi", "fr")
check("unknown language falls back to English", "type 2 diabetes" in r["reply"], r["lang"])

check("de: disclaimer localized", "keine medizinische" in engine.reply("Ist Banane okay?", "de")["disclaimer"])

print("== knowledge base sanity ==")
ok = True
for f in engine.foods:
    if f["light"] not in LIGHT_RANK: ok = False
    if not f["aliases"]["en"]: ok = False
    if not f["name"].get("en") or not f["name"].get("de"): ok = False
    if not f["note"].get("en") or not f["note"].get("de"): ok = False
    if f["carbs_g"] < 0 or f["kcal"] < 0: ok = False
    if f["gi"] is not None and not (0 < f["gi"] <= 100): ok = False
check(f"all {len(engine.foods)} food entries well-formed and bilingual", ok)
check("food_list() serves the side panel (en)", len(engine.food_list()) == len(engine.foods))
check("food_list() localizes names (de)", any(f["name"] == "Vollkornbrot" for f in engine.food_list("de")))

dis = route("Is banana ok?")["disclaimer"]
check("every response carries the disclaimer", "not medical advice" in dis)

print()
print(f"Result: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
