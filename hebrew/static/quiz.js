// Syllable quiz: show a syllable, record the kid, let the server judge it.
const $ = (id) => document.getElementById(id);
const RANK = { correct: 3, very_close: 2, close: 1, incorrect: 0 };
const EMOJI = { correct: "✅", very_close: "😃", close: "🙂", incorrect: "❌", no_speech: "👂" };

let quiz = null;          // {questions, retries, feedback_audio, ...}
let idx = 0;              // current question
let attempts = 0;         // counted attempts for the current question
let best = null;          // best verdict for the current question
let results = [];         // [{id, verdict, attempts}]
let busy = false;
let player = null;
let autoNext = null;

// ---------- microphone ----------
let stream = null, actx = null, analyser = null;

async function initMic() {
  if (stream) return;
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  actx = new AudioContext();
  analyser = actx.createAnalyser();
  analyser.fftSize = 1024;
  actx.createMediaStreamSource(stream).connect(analyser);
}

// Record until the kid stops talking (or 4 s). Resolves to a 16 kHz WAV Blob.
function record() {
  return new Promise((resolve) => {
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = async () => resolve(await toWav(new Blob(chunks, { type: rec.mimeType })));
    rec.start();

    const buf = new Float32Array(analyser.fftSize);
    const t0 = performance.now();
    let noise = null, started = false, quietSince = null;
    const timer = setInterval(() => {
      analyser.getFloatTimeDomainData(buf);
      const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
      const db = 20 * Math.log10(rms + 1e-9);
      $("q-level").style.width = `${Math.max(0, Math.min(100, (db + 60) * 2))}%`;
      const t = performance.now() - t0;
      if (t < 200) { noise = noise === null ? db : Math.max(noise, db); return; }
      const threshold = Math.max((noise ?? -60) + 12, -50);
      if (db > threshold) { started = true; quietSince = null; }
      else if (started) quietSince = quietSince ?? t;
      if ((started && t - quietSince > 700) || t > 4000) {
        clearInterval(timer);
        $("q-level").style.width = "0";
        rec.stop();
      }
    }, 40);
  });
}

async function toWav(blob) {
  const decoded = await actx.decodeAudioData(await blob.arrayBuffer());
  const rate = 16000;
  const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate);
  const src = off.createBufferSource();
  src.buffer = decoded;
  src.connect(off.destination);
  src.start();
  const pcm = (await off.startRendering()).getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); out.setUint32(4, 36 + pcm.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
  out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true);
  out.setUint16(34, 16, true); str(36, "data"); out.setUint32(40, pcm.length * 2, true);
  pcm.forEach((v, i) => out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true));
  return new Blob([out], { type: "audio/wav" });
}

// ---------- sound ----------
function playUrl(url) {
  if (!url) return;
  if (player) player.pause();
  player = new Audio(url);
  player.play().catch(() => {});
}

// ---------- screens ----------
function show(id) {
  for (const s of ["q-intro", "q-question", "q-summary"]) $(s).hidden = s !== id;
}

function renderDots(el, list, current) {
  el.innerHTML = "";
  quiz.questions.forEach((q, i) => {
    const d = document.createElement("span");
    const r = list[i];
    d.className = "dot " + (r ? r.verdict : "") + (i === current ? " current" : "");
    d.textContent = r ? q.text : "";
    el.appendChild(d);
  });
}

function showQuestion() {
  clearTimeout(autoNext);
  const q = quiz.questions[idx];
  attempts = 0;
  best = null;
  $("q-counter").textContent = `שְׁאֵלָה ${idx + 1} מִתּוֹךְ ${quiz.questions.length}`;
  $("q-syllable").textContent = q.text;
  $("q-feedback").hidden = true;
  $("q-listen").hidden = true;
  $("q-next").hidden = true;
  $("q-skip").hidden = false;
  $("q-mic").disabled = false;
  $("q-mic").classList.remove("recording");
  $("q-hint").textContent = "לְחַץ עַל הַמִּיקְרוֹפוֹן וְתַגִּיד אֶת הַהֲבָרָה";
  updateAttempts();
  renderDots($("q-dots"), results, idx);
}

function updateAttempts() {
  $("q-attempts").textContent = `נִסְיוֹנוֹת: ${attempts} / ${quiz.retries}`;
}

function showVerdict(v, text) {
  $("q-feedback").hidden = false;
  $("q-feedback").className = "q-feedback " + v;
  $("q-verdict-emoji").textContent = EMOJI[v] || "❓";
  $("q-verdict-text").textContent = text;
  playUrl(quiz.feedback_audio[v]);
}

async function onMic() {
  if (busy) return;
  busy = true;
  clearTimeout(autoNext);
  $("q-mic").classList.add("recording");
  $("q-hint").textContent = "🔴 מַקְשִׁיב...";
  $("q-feedback").hidden = true;
  try {
    const wav = await record();
    $("q-mic").classList.remove("recording");
    $("q-hint").textContent = "🤔 בּוֹדֵק...";
    const form = new FormData();
    form.append("syllable", quiz.questions[idx].id);
    form.append("audio", wav, "answer.wav");
    const res = await (await fetch("/api/quiz/syllables/check", { method: "POST", body: form })).json();
    handleResult(res);
  } catch (e) {
    console.error(e);
    $("q-hint").textContent = "⚠️ מַשֶּׁהוּ הִשְׁתַּבֵּשׁ, נְנַסֶּה שׁוּב";
  } finally {
    $("q-mic").classList.remove("recording");
    busy = false;
  }
}

function handleResult(res) {
  const v = res.verdict;
  if (v === "no_speech" || v === "error") {          // does not count as an attempt
    showVerdict("no_speech", res.text || "לֹא שָׁמַעְתִּי");
    $("q-hint").textContent = "לְחַץ שׁוּב עַל הַמִּיקְרוֹפוֹן וְדַבֵּר חָזָק יוֹתֵר";
    return;
  }
  attempts += 1;
  if (best === null || RANK[v] > RANK[best]) best = v;
  updateAttempts();
  showVerdict(v, res.text);
  if (v === "correct" || attempts >= quiz.retries) {
    finishQuestion();
    if (v === "correct") autoNext = setTimeout(nextQuestion, 2200);
  } else {
    $("q-listen").hidden = false;     // learning aid after a miss
    $("q-hint").textContent = `נְנַסֶּה שׁוּב! (נִשְׁאֲרוּ ${quiz.retries - attempts} נִסְיוֹנוֹת)`;
  }
}

function finishQuestion() {
  results[idx] = { id: quiz.questions[idx].id, verdict: best || "incorrect", attempts };
  renderDots($("q-dots"), results, idx);
  $("q-mic").disabled = true;
  $("q-skip").hidden = true;
  $("q-listen").hidden = false;
  $("q-next").hidden = false;
  $("q-hint").textContent = idx + 1 < quiz.questions.length ? "" : "זוֹ הָיְתָה הַשְּׁאֵלָה הָאַחֲרוֹנָה!";
}

function nextQuestion() {
  clearTimeout(autoNext);
  if (!results[idx]) finishQuestion();    // skipped
  idx += 1;
  if (idx < quiz.questions.length) showQuestion();
  else finishQuiz();
}

async function finishQuiz() {
  const r = await (await fetch("/api/quiz/syllables/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results }),
  })).json();
  $("q-score").textContent = r.score;
  const stars = r.score >= 90 ? 3 : r.score >= 70 ? 2 : r.score >= 40 ? 1 : 0;
  $("q-stars").textContent = "⭐".repeat(stars) + "☆".repeat(3 - stars);
  $("q-summary-best").textContent = r.new_best
    ? "🏆 שִׂיא חָדָשׁ לְהַיּוֹם!"
    : `הַצִּיּוּן הֲכִי טוֹב הַיּוֹם: ${r.best_today}`;
  renderDots($("q-summary-dots"), results, -1);
  show("q-summary");
  if (r.score >= 70) playUrl(quiz.feedback_audio.correct);
}

// ---------- start ----------
async function loadQuiz() {
  quiz = await (await fetch("/api/quiz/syllables/new", { method: "POST" })).json();
  $("q-info").textContent = `${quiz.questions.length} שְׁאֵלוֹת · עַד ${quiz.retries} נִסְיוֹנוֹת לְכָל שְׁאֵלָה`;
  $("q-best").textContent = quiz.best_today
    ? `🏆 הַצִּיּוּן הֲכִי טוֹב הַיּוֹם: ${quiz.best_today.best_score}`
    : "";
  waitForModel(quiz.model_ready);
}

function waitForModel(ready) {
  $("q-model").hidden = ready;
  $("q-start").disabled = !ready;
  if (!ready) {
    setTimeout(async () => {
      const s = await (await fetch("/api/quiz/status")).json();
      waitForModel(s.model_ready);
    }, 2000);
  }
}

async function start() {
  $("q-mic-error").hidden = true;
  try {
    await initMic();
    if (actx.state === "suspended") await actx.resume();
  } catch (e) {
    $("q-mic-error").hidden = false;
    return;
  }
  idx = 0;
  results = [];
  show("q-question");
  showQuestion();
}

$("q-start").addEventListener("click", start);
$("q-mic").addEventListener("click", onMic);
$("q-skip").addEventListener("click", nextQuestion);
$("q-next").addEventListener("click", nextQuestion);
$("q-listen").addEventListener("click", () => playUrl(quiz.questions[idx].audio));
$("q-again").addEventListener("click", async () => { await loadQuiz(); show("q-intro"); });
loadQuiz();
