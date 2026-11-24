"""Navigation tree: subjects (Hebrew, math) and the activities inside each.

To add an activity later (e.g. a math task), add an entry to "items" and a
Flask route for its url. Activities without a "url" are shown as "coming soon".
"""

WELCOME_TEXT = "שָׁלוֹם! מָה נִלְמַד הַיּוֹם?"

SUBJECTS = [
    {
        "id": "hebrew",
        "title": "עִבְרִית",
        "emoji": "📖",
        "url": "/hebrew",
        "color": "#ff7a59",
        "items": [
            {"id": "syllables", "title": "הֲבָרוֹת", "emoji": "🔤", "url": "/hebrew/syllables"},
            {"id": "syllables-quiz", "title": "חִידוֹן הֲבָרוֹת", "emoji": "🎤", "url": "/hebrew/syllables/quiz"},
        ],
    },
    {
        "id": "math",
        "title": "חֶשְׁבּוֹן",
        "emoji": "🔢",
        "url": "/math",
        "color": "#4aa3df",
        "items": [
            {"id": "math-soon", "title": "בְּקָרוֹב...", "emoji": "🚧", "url": None},
        ],
    },
]


def subject(subject_id):
    return next((s for s in SUBJECTS if s["id"] == subject_id), None)


def audio_items():
    """Spoken labels for the menus, so a kid who can't read yet can hear them."""
    items = [("ui/welcome.mp3", WELCOME_TEXT, "word")]
    for s in SUBJECTS:
        items.append((f"ui/menu_{s['id']}.mp3", s["title"], "word"))
        for it in s["items"]:
            if it["url"]:
                items.append((f"ui/menu_{it['id']}.mp3", it["title"], "word"))
    return items
