"""Check a kid's spoken syllable - fully offline.

Engine: a pretrained multilingual *phoneme recognizer*
(facebook/wav2vec2-xlsr-53-espeak-cv-ft, trained on thousands of speakers in
dozens of languages). It turns audio into per-frame probabilities of IPA
phonemes such as b, a, ʃ, x.

For each candidate sound (the target, e.g. "ba", and similar sounds such as
"bi", "va", "da") we compute how well its phoneme sequence explains the audio
(CTC loss: lower = more likely). The verdict depends on the *margin* between
the target and the best competing sound, which is speaker independent - the
kid's voice is never compared to an adult voice.

Why not compare raw audio with the reference recordings? We measured it:
with voices the system had never heard, plain MFCC+DTW put the right answer
first only ~40% of the time, the phoneme model is far better at separating
right from wrong answers.
"""
import json
import os
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

BASE = Path(__file__).parent
os.environ.setdefault("HF_HOME", str(BASE / "models"))          # keep the model inside the project
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

MODEL_ID = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
SR = 16000
FRAME, HOP = 400, 160    # 25 ms frames, 10 ms hop (for silence trimming)


# ---------- audio helpers ----------
def load_audio(source):
    """Read a file path or file-like object -> float32 mono at 16 kHz."""
    data, sr = sf.read(source, dtype="float32", always_2d=True)
    return resample(data.mean(axis=1), sr)


def resample(x, sr):
    if sr == SR or len(x) == 0:
        return x.astype(np.float32)
    if sr > SR:  # low-pass before downsampling to avoid aliasing
        spec = np.fft.rfft(x)
        spec[int(len(spec) * (SR / 2 * 0.95) / (sr / 2)):] = 0
        x = np.fft.irfft(spec, n=len(x))
    n_out = int(round(len(x) * SR / sr))
    return np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x).astype(np.float32)


def frame_energy_db(x):
    n = max(1, 1 + (len(x) - FRAME) // HOP)
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    frames = np.pad(x, (0, FRAME))[idx]
    return 10 * np.log10((frames ** 2).mean(axis=1) + 1e-10)


def trim_silence(x, drop_db=35.0, pad_frames=8):
    """Keep the part between the first and last frame louder than (peak - drop_db)."""
    if len(x) < FRAME:
        return x
    e = frame_energy_db(x)
    loud = np.where(e > e.max() - drop_db)[0]
    start = max(0, (loud[0] - pad_frames) * HOP)
    end = min(len(x), (loud[-1] + pad_frames) * HOP + FRAME)
    return x[start:end]


def speech_level(x):
    """Peak frame loudness in dBFS - used to detect 'nothing was said'."""
    return float(frame_energy_db(x).max()) if len(x) >= FRAME else -100.0


# ---------- phoneme model ----------
class PhonemeScorer:
    """Lazy-loaded, thread-safe wrapper around the phoneme CTC model."""

    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._vocab = None

    def load(self):
        with self._lock:
            if self._model is None:
                import torch  # noqa: F401  (heavy imports only when needed)
                from huggingface_hub import hf_hub_download
                from transformers import Wav2Vec2ForCTC
                # use_safetensors=False: the repo only ships .bin weights; without it
                # transformers also downloads a converted 1.2 GB safetensors copy.
                self._model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID, use_safetensors=False).eval()
                with open(hf_hub_download(MODEL_ID, "vocab.json"), encoding="utf8") as f:
                    self._vocab = json.load(f)
                self._inv = {v: k for k, v in self._vocab.items()}
                self._blank = self._model.config.pad_token_id
        return self

    @property
    def ready(self):
        return self._model is not None

    def token_ids(self, phonemes):
        """['b', 'a'] -> token ids, or None if the model lacks a phoneme."""
        self.load()
        if not all(p in self._vocab for p in phonemes):
            return None
        return [self._vocab[p] for p in phonemes]

    def log_probs(self, audio):
        import torch
        self.load()
        x = (audio - audio.mean()) / (audio.std() + 1e-7)
        with self._lock, torch.inference_mode():
            return self._model(torch.from_numpy(x)[None]).logits.log_softmax(-1)[0]

    def loss(self, log_probs, token_ids):
        """CTC loss of a phoneme sequence given the audio (lower = more likely)."""
        import torch
        return torch.nn.functional.ctc_loss(
            log_probs[:, None, :], torch.tensor([token_ids]), torch.tensor([log_probs.shape[0]]),
            torch.tensor([len(token_ids)]), blank=self._blank, reduction="sum").item()

    def transcribe(self, log_probs):
        """Greedy IPA transcription - what the model 'heard' (for parents / debugging)."""
        out, prev = [], None
        for i in log_probs.argmax(-1).tolist():
            if i != prev and i != self._blank:
                out.append(self._inv[i])
            prev = i
        return "".join(out)


scorer = PhonemeScorer()


def ensure_model():
    """Download (first time, ~1.2 GB) and load the model. Used by run.cmd."""
    scorer.load()
    print("Speech model ready.")


if __name__ == "__main__":
    ensure_model()
