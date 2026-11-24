"""Kids learning app (Hebrew, later math) - Flask web app."""
import os
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

import db
import menus
from hebrew_data import LETTERS, VOWELS, syllable_say

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "static" / "audio"

# Activities with a daily task: activity id -> set of item ids to complete.
TASKS = {
    "syllables": {f"{l['id']}_{v['id']}" for l in LETTERS for v in VOWELS},
}

app = Flask(__name__)


def audio_url(rel):
    """URL of the clip if it exists, else None (browser falls back to speechSynthesis)."""
    return f"/static/audio/{rel}" if (AUDIO_DIR / rel).exists() else None


@app.context_processor
def navigation():
    """Every page gets the menu tree for the side bar."""
    return {"subjects": menus.SUBJECTS, "audio_url": audio_url}


# ---------- pages ----------
@app.get("/")
def welcome():
    return render_template("welcome.html", welcome_text=menus.WELCOME_TEXT)


@app.get("/<subject_id>")
def subject_menu(subject_id):
    subj = menus.subject(subject_id)
    if subj is None:
        abort(404)
    return render_template("menu.html", subject=subj, active=(subj["id"], None))


@app.get("/hebrew/syllables")
def syllables_page():
    return render_template("syllables.html", active=("hebrew", "syllables"))


@app.get("/history")
def history_page():
    names = {it["id"]: f"{s['title']} › {it['title']}" for s in menus.SUBJECTS for it in s["items"]}
    rows = db.history()
    for r in rows:
        r["percent"] = round(100 * r["done"] / r["total"]) if r["total"] else 0
        r["activity_name"] = names.get(r["activity"], r["activity"])
        if r["finished_at"]:
            r["status"] = "done"
        elif r["is_latest"] and r["day"] == db.today():
            r["status"] = "open"
        else:
            r["status"] = "unfinished"
    return render_template("history.html", rows=rows, active=("history", None))


# ---------- API ----------
@app.get("/api/lessons")
def lessons():
    data = []
    for letter in LETTERS:
        data.append({
            "id": letter["id"],
            "char": letter["char"],
            "name": letter["name"],
            "audio": audio_url(f"names/{letter['id']}.mp3"),
            "syllables": [{
                "id": f"{letter['id']}_{v['id']}",
                "text": letter["char"] + v["mark"],
                "vowel": v["name"],
                "say": syllable_say(letter, v),
                "audio": audio_url(f"syllables/{letter['id']}_{v['id']}.mp3"),
            } for v in VOWELS],
            "words": [{
                "text": word,
                "emoji": emoji,
                "say": word,
                "audio": audio_url(f"words/{letter['id']}_{i}.mp3"),
            } for i, (word, emoji) in enumerate(letter["words"])],
        })
    return jsonify({"letters": data, "success_audio": audio_url("ui/success.mp3")})


def _activity(activity):
    if activity not in TASKS:
        abort(404)
    return TASKS[activity]


@app.post("/api/task/<activity>/today")
def today_task(activity):
    """Get today's task, creating it on the first visit of the day."""
    return jsonify(db.today_task(activity, len(_activity(activity))))


@app.post("/api/task/<activity>/today/reset")
def reset_today(activity):
    return jsonify(db.reset_today(activity, len(_activity(activity))))


@app.post("/api/session/<int:session_id>/click")
def click(session_id):
    item = (request.get_json(silent=True) or {}).get("item", "")
    valid = set().union(*TASKS.values())
    state, just_finished = db.record_click(session_id, item, valid)
    if state is None:
        abort(404)
    return jsonify({"session": state, "just_finished": just_finished})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
