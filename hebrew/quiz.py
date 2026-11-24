"""Syllable quiz: question generation, answer checking and scoring."""
import random

import speech_match as sm
from hebrew_data import LETTERS, VOWELS, syllable_sound

# IPA phonemes the model may output for each Hebrew consonant / vowel sound.
# Several spellings are accepted (e.g. Israeli r is usually ʁ).
CONSONANT_IPA = {
    "": [[]], "b": [["b"]], "v": [["v"]], "g": [["ɡ"], ["g"]], "d": [["d"]], "h": [["h"]],
    "z": [["z"]], "kh": [["x"], ["χ"]], "t": [["t"]], "y": [["j"]], "k": [["k"]], "l": [["l"]],
    "m": [["m"]], "n": [["n"]], "s": [["s"]], "p": [["p"]], "f": [["f"]],
    "ts": [["t", "s"], ["ts"], ["s"]], "r": [["ʁ"], ["r"], ["ɾ"], ["ʀ"]], "sh": [["ʃ"]],
}
VOWEL_IPA = {
    "a": [["a"], ["aː"]], "e": [["e"], ["ɛ"], ["eː"]], "i": [["i"], ["iː"]],
    "o": [["o"], ["ɔ"], ["oː"]], "u": [["u"], ["uː"]],
}

# Pairs that are very hard to tell apart on a short recording. Confusing them
# is never judged worse than "close".
SIMILAR = {frozenset(p) for p in [("b", "v"), ("p", "f"), ("k", "kh"), ("h", "kh"), ("h", ""),
                                   ("ts", "s"), ("t", "d"), ("o", "u"), ("e", "i")]}

# Margin = (loss of best competing sound) - (loss of target). >= 0 means the
# target was the most likely sound. Calibrated on recordings of 9 voices.
THRESHOLDS = {"correct": 0.0, "very_close": -2.0, "close": -4.5}
MIN_SPEECH_DB = -50.0    # quieter than this = "I didn't hear you"

# Points per question for the best verdict reached.
POINTS = {"correct": 1.0, "very_close": 0.75, "close": 0.5, "incorrect": 0.0}

VERDICT_TEXT = {
    "correct": "נָכוֹן! כָּל הַכָּבוֹד!",
    "very_close": "קָרוֹב מְאוֹד!",
    "close": "קָרוֹב!",
    "incorrect": "לֹא נָכוֹן, נְנַסֶּה שׁוּב.",
    "no_speech": "לֹא שָׁמַעְתִּי, נְנַסֶּה שׁוּב.",
}

SYLLABLES = {f"{l['id']}_{v['id']}": (l, v) for l in LETTERS for v in VOWELS}
SOUNDS = sorted({syllable_sound(l, v) for l, v in SYLLABLES.values()})


def split_sound(sound):
    return sound[:-1], sound[-1]


def competitors(target):
    """Sounds a kid could confuse with the target: same consonant + other vowel,
    or same vowel + other consonant."""
    cons, vow = split_sound(target)
    return [s for s in SOUNDS if s != target and (split_sound(s)[0] == cons or split_sound(s)[1] == vow)]


def similar(a, b):
    (ca, va), (cb, vb) = split_sound(a), split_sound(b)
    if va == vb:
        return frozenset((ca, cb)) in SIMILAR
    if ca == cb:
        return frozenset((va, vb)) in SIMILAR
    return False


def _variants(sound):
    cons, vow = split_sound(sound)
    out = []
    for c in CONSONANT_IPA[cons]:
        for v in VOWEL_IPA[vow]:
            ids = sm.scorer.token_ids(c + v)
            if ids:
                out.append(ids)
    return out


def _sound_loss(log_probs, sound):
    return min(sm.scorer.loss(log_probs, ids) for ids in _variants(sound))


def verdict_for(margin, target, best_other):
    for name in ("correct", "very_close", "close"):
        if margin >= THRESHOLDS[name]:
            return name
    return "close" if similar(target, best_other) else "incorrect"


def check(syllable_id, wav_file):
    """Judge a recording of a syllable. Returns a dict for the API."""
    letter, vowel = SYLLABLES[syllable_id]
    target = syllable_sound(letter, vowel)
    try:
        audio = sm.load_audio(wav_file)
    except Exception:
        return {"verdict": "no_speech", "text": VERDICT_TEXT["no_speech"]}
    if sm.speech_level(audio) < MIN_SPEECH_DB:
        return {"verdict": "no_speech", "text": VERDICT_TEXT["no_speech"]}
    lp = sm.scorer.log_probs(sm.trim_silence(audio))
    heard = sm.scorer.transcribe(lp)
    if not heard:
        return {"verdict": "no_speech", "text": VERDICT_TEXT["no_speech"], "heard": ""}
    losses = {s: _sound_loss(lp, s) for s in [target, *competitors(target)]}
    best_other = min((s for s in losses if s != target), key=losses.get)
    margin = losses[best_other] - losses[target]
    verdict = verdict_for(margin, target, best_other)
    return {"verdict": verdict, "text": VERDICT_TEXT[verdict], "heard": heard,
            "target": target, "closest_other": best_other, "margin": round(margin, 2)}


def new_quiz(n_questions):
    ids = list(SYLLABLES)
    random.shuffle(ids)
    picked = (ids * (n_questions // len(ids) + 1))[:n_questions]
    return [{"id": sid, "text": SYLLABLES[sid][0]["char"] + SYLLABLES[sid][1]["mark"],
             "audio": f"/static/audio/syllables/{sid}.mp3"} for sid in picked]


def score(verdicts):
    """Quiz score 0-100 from the best verdict of every question."""
    if not verdicts:
        return 0
    return round(100 * sum(POINTS.get(v, 0.0) for v in verdicts) / len(verdicts))


def audio_items():
    """Spoken feedback clips: (path, text, kind)."""
    return [(f"ui/verdict_{k}.mp3", t, "word") for k, t in VERDICT_TEXT.items()]
