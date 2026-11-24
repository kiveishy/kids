"""Hebrew syllables for first grade - Flask web app."""
import os
from pathlib import Path

from flask import Flask, jsonify, render_template

from hebrew_data import LETTERS, VOWELS, syllable_say

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "static" / "audio"

app = Flask(__name__)


def audio_url(rel):
    """URL of the clip if it exists, else None (browser falls back to speechSynthesis)."""
    return f"/static/audio/{rel}" if (AUDIO_DIR / rel).exists() else None


@app.get("/")
def index():
    return render_template("index.html")


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
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
