const DAGESH = "ּ", SHIN_DOT = "ׁ", SIN_DOT = "ׂ";
const isMark = (ch) => /[֑-ׇ]/.test(ch);

let lessons = [];
let current = null;
let audio = null;
let session = null;          // current task from the DB (null = no task yet)
let clicked = new Set();     // syllable ids clicked in this task
let successAudio = null;

const taskActive = () => session && !session.finished_at;

const $ = (id) => document.getElementById(id);

// ---------- sound ----------
function speakFallback(text) {
  // Used only when the MP3 clip was not generated (e.g. no internet at setup).
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "he-IL";
  u.rate = 0.7;
  const he = speechSynthesis.getVoices().find((v) => v.lang.startsWith("he"));
  if (he) u.voice = he;
  speechSynthesis.speak(u);
}

function play(item, el) {
  if (audio) audio.pause();
  if (el) {
    el.classList.add("playing");
    setTimeout(() => el.classList.remove("playing"), 600);
  }
  if (item.audio) {
    audio = new Audio(item.audio);
    audio.play().catch(() => speakFallback(item.say || item.name));
  } else {
    speakFallback(item.say || item.name);
  }
}

// ---------- highlight the lesson letter inside a word ----------
function clusters(word) {
  const out = [];
  for (const ch of word) {
    if (isMark(ch) && out.length) out[out.length - 1] += ch;
    else out.push(ch);
  }
  return out;
}

function matches(cluster, letter) {
  if (cluster[0] !== letter.char[0]) return false;
  const want = letter.char.slice(1);
  if (want === DAGESH) return cluster.includes(DAGESH);
  if (want === SHIN_DOT || want === SIN_DOT) return cluster.includes(want);
  if ("בכפ".includes(letter.char)) return !cluster.includes(DAGESH); // vet/khaf/fe
  return true;
}

function highlighted(word, letter) {
  const frag = document.createDocumentFragment();
  for (const c of clusters(word)) {
    if (matches(c, letter)) {
      const s = document.createElement("span");
      s.className = "hl";
      s.textContent = c;
      frag.appendChild(s);
    } else {
      frag.appendChild(document.createTextNode(c));
    }
  }
  return frag;
}

// ---------- rendering ----------
function tile(className, parts, onClick) {
  const b = document.createElement("button");
  b.className = "tile " + className;
  for (const p of parts) b.appendChild(p);
  b.addEventListener("click", () => onClick(b));
  return b;
}

function span(cls, content) {
  const s = document.createElement("span");
  s.className = cls;
  if (typeof content === "string") s.textContent = content;
  else s.appendChild(content);
  return s;
}

function renderLetterBar() {
  const nav = $("letters");
  nav.innerHTML = "";
  for (const l of lessons) {
    const b = document.createElement("button");
    b.className = "letter-btn";
    b.textContent = l.char;
    b.title = l.name;
    b.dataset.id = l.id;
    b.addEventListener("click", () => select(l, true));
    nav.appendChild(b);
  }
}

function select(letter, speakName) {
  current = letter;
  document.querySelectorAll(".letter-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.id === letter.id));

  $("big-letter").textContent = letter.char;
  $("letter-name").textContent = letter.name;

  const syl = $("syllables");
  syl.innerHTML = "";
  for (const s of letter.syllables) {
    const t = tile("syllable", [
      span("syl-text", s.text),
      span("speaker", "🔊"),
      span("syl-vowel", s.vowel),
    ], (el) => { play(s, el); markClicked(s.id, el); });
    t.dataset.id = s.id;
    t.classList.toggle("done", clicked.has(s.id));
    syl.appendChild(t);
  }

  const words = $("words");
  words.innerHTML = "";
  for (const w of letter.words) {
    words.appendChild(tile("word", [
      span("word-emoji", w.emoji),
      span("word-text", highlighted(w.text, letter)),
      span("speaker", "🔊"),
    ], (el) => play(w, el)));
  }

  if (speakName) play(letter, $("big-letter"));
}

const letterDone = (l) => l.syllables.every((s) => clicked.has(s.id));

function randomLetter() {
  let pool = lessons.filter((l) => l !== current);
  // During a task, prefer letters the kid has not finished yet.
  if (taskActive()) {
    const open = pool.filter((l) => !letterDone(l));
    if (open.length) pool = open;
  }
  select(pool[Math.floor(Math.random() * pool.length)], true);
}

// ---------- today's task ----------
const ACTIVITY = "syllables";

function applySession(s) {
  session = s;
  clicked = new Set(s.clicked);   // a finished task keeps all its marks
  renderProgress();
}

function renderProgress() {
  const finished = !taskActive();
  const done = clicked.size, total = session.total;
  $("progress-fill").style.width = `${(100 * done) / total}%`;
  $("progress-text").textContent = `${done} / ${total}`;
  $("done-badge").hidden = !finished;
  $("reset-task").hidden = !finished;
  document.querySelectorAll(".letter-btn").forEach((b) => {
    const l = lessons.find((x) => x.id === b.dataset.id);
    const n = l.syllables.filter((s) => clicked.has(s.id)).length;
    b.classList.toggle("done", n === l.syllables.length);
    b.classList.toggle("partial", n > 0 && n < l.syllables.length);
  });
  document.querySelectorAll(".tile.syllable").forEach((t) =>
    t.classList.toggle("done", clicked.has(t.dataset.id)));
}

async function markClicked(id, el) {
  if (!taskActive() || clicked.has(id)) return;
  clicked.add(id);
  el.classList.add("done");
  renderProgress();
  try {
    const r = await fetch(`/api/session/${session.id}/click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: id }),
    });
    const { session: s, just_finished } = await r.json();
    if (just_finished) {
      applySession(s);
      showSuccess(s.finished_at);
    }
  } catch (e) {
    console.error("could not save click", e);
  }
}

function showSuccess(when) {
  $("success-date").textContent = when;
  $("success").hidden = false;
  setTimeout(() => {
    if (successAudio) { if (audio) audio.pause(); audio = new Audio(successAudio); audio.play(); }
    else speakFallback("כָּל הַכָּבוֹד! הַמְּשִׂימָה הֻשְׁלְמָה!");
  }, 700);
}

async function resetToday() {
  if (!confirm("לְהַתְחִיל מֵחָדָשׁ אֶת הַמְּשִׂימָה שֶׁל הַיּוֹם?\n(הַמְּשִׂימָה שֶׁהֻשְׁלְמָה תִּשָּׁאֵר בַּהִיסְטוֹרְיָה)")) return;
  const r = await fetch(`/api/task/${ACTIVITY}/today/reset`, { method: "POST" });
  applySession(await r.json());
  select(lessons[0], true);
}

async function init() {
  const data = await (await fetch("/api/lessons")).json();
  lessons = data.letters;
  successAudio = data.success_audio;
  renderLetterBar();
  $("random").addEventListener("click", randomLetter);
  $("big-letter").addEventListener("click", (e) => play(current, e.currentTarget));
  $("reset-task").addEventListener("click", resetToday);
  $("success-close").addEventListener("click", () => { $("success").hidden = true; });
  // Today's task opens automatically (created on the first visit of the day).
  const r = await fetch(`/api/task/${ACTIVITY}/today`, { method: "POST" });
  applySession(await r.json());
  // Continue where the kid stopped: first letter that is not finished yet.
  const start = taskActive() ? lessons.find((l) => !letterDone(l)) : null;
  select(start || lessons[0], false);
}

init();
