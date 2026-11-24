"""Generate the MP3 clips for every letter name, syllable and word.

Uses Microsoft neural text-to-speech (he-IL) via the free `edge-tts` package.
Needs internet only while generating; the app itself plays local files.

Existing files are never overwritten, so you can replace any clip in
static/audio with your own recording (same file name) and it will be kept.
Use --force to regenerate everything.
"""
import argparse
import asyncio
import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # use the Windows certificate store (corporate proxies)

import edge_tts  # noqa: E402

from hebrew_data import audio_items  # noqa: E402

AUDIO_DIR = Path(__file__).parent / "static" / "audio"
VOICE = "he-IL-HilaNeural"          # alternative male voice: he-IL-AvriNeural
RATE = {"syllable": "-25%", "name": "-15%", "word": "-15%"}


async def make(sem, path, text, kind):
    async with sem:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        await edge_tts.Communicate(text, VOICE, rate=RATE[kind]).save(str(tmp))
        tmp.replace(path)


async def main(force):
    todo = [(AUDIO_DIR / rel, text, kind) for rel, text, kind in audio_items()
            if force or not (AUDIO_DIR / rel).exists()]
    if not todo:
        print("Audio: all clips present.")
        return 0
    print(f"Audio: generating {len(todo)} clip(s) with {VOICE} ...")
    sem = asyncio.Semaphore(6)
    results = await asyncio.gather(*(make(sem, *t) for t in todo), return_exceptions=True)
    failed = [(t, r) for t, r in zip(todo, results) if isinstance(r, Exception)]
    for (path, text, _), err in failed[:5]:
        print(f"  failed: {path.name} ({text}): {err}")
    print(f"Audio: {len(todo) - len(failed)} created, {len(failed)} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate existing clips")
    sys.exit(asyncio.run(main(ap.parse_args().force)))
