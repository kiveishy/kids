const DAGESH = "ּ", SHIN_DOT = "ׁ", SIN_DOT = "ׂ";
const isMark = (ch) => /[֑-ׇ]/.test(ch);

let lessons = [];
let current = null;
let audio = null;

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
    syl.appendChild(tile("syllable", [
      span("syl-text", s.text),
      span("speaker", "🔊"),
      span("syl-vowel", s.vowel),
    ], (el) => play(s, el)));
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

function randomLetter() {
  const pool = lessons.filter((l) => l !== current);
  select(pool[Math.floor(Math.random() * pool.length)], true);
}

async function init() {
  lessons = await (await fetch("/api/lessons")).json();
  renderLetterBar();
  $("random").addEventListener("click", randomLetter);
  $("big-letter").addEventListener("click", (e) => play(current, e.currentTarget));
  select(lessons[Math.floor(Math.random() * lessons.length)], false);
}

init();
