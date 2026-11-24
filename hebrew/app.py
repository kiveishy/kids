"""Kids learning app (Hebrew, later math) - Flask web app."""
import json
import os
import threading
from pathlib import Path

import truststore
from flask import Flask, abort, jsonify, render_template, request

truststore.inject_into_ssl()  # Windows certificate store (needed behind corporate proxies)

import db  # noqa: E402
import menus  # noqa: E402
import quiz  # noqa: E402
import speech_match  # noqa: E402
from hebrew_data import LETTERS, VOWELS, syllable_say  # noqa: E402

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


@app.get("/hebrew/syllables/quiz")
def syllables_quiz_page():
    return render_template("quiz.html", active=("hebrew", "syllables-quiz"))


@app.route("/parents", methods=["GET", "POST"])
def parents_page():
    saved = False
    if request.method == "POST":
        db.save_settings(request.form)
        saved = True
    return render_template("parents.html", settings=db.get_settings(), limits=db.SETTINGS,
                           saved=saved, active=("parents", None))


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
    quizzes = db.quiz_history()
    for q in quizzes:
        q["activity_name"] = names.get(q["activity"], q["activity"])
    return render_template("history.html", rows=rows, quizzes=quizzes, active=("history", None))


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


# ---------- quiz API ----------
QUIZ_ID = "syllables-quiz"


@app.post("/api/quiz/syllables/new")
def quiz_new():
    s = db.get_settings()
    return jsonify({
        "questions": quiz.new_quiz(s["quiz_questions"]),
        "retries": s["quiz_retries"],
        "best_today": db.quiz_best_today(QUIZ_ID),
        "model_ready": speech_match.scorer.ready,
        "feedback_audio": {k: audio_url(f"ui/verdict_{k}.mp3") for k in quiz.VERDICT_TEXT},
    })


@app.get("/api/quiz/status")
def quiz_status():
    return jsonify({"model_ready": speech_match.scorer.ready})


@app.post("/api/quiz/syllables/check")
def quiz_check():
    syllable_id = request.form.get("syllable", "")
    upload = request.files.get("audio")
    if syllable_id not in quiz.SYLLABLES or upload is None:
        abort(400)
    return jsonify(quiz.check(syllable_id, upload.stream))


@app.post("/api/quiz/syllables/finish")
def quiz_finish():
    results = (request.get_json(silent=True) or {}).get("results", [])
    verdicts = [r.get("verdict") for r in results if isinstance(r, dict)]
    if not verdicts:
        abort(400)
    score = quiz.score(verdicts)
    best, is_new_best = db.save_quiz_score(QUIZ_ID, score, len(verdicts), json.dumps(results))
    return jsonify({"score": score, "best_today": best, "new_best": is_new_best})


def _warm_up_model():
    try:
        speech_match.scorer.load()
    except Exception as e:  # app still works without the quiz
        print(f"Speech model could not be loaded: {e}")


if __name__ == "__main__":
    threading.Thread(target=_warm_up_model, daemon=True).start()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
