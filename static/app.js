const introSection = document.getElementById("intro");
const quizSection = document.getElementById("quiz");
const resultsSection = document.getElementById("results");
const progress = document.getElementById("progress");
const questionText = document.getElementById("question");
const answerTexts = [document.getElementById("answer0"), document.getElementById("answer1")];
const answersBox = document.querySelector(".answers");
const answerTabs = [...document.querySelectorAll(".tab")];
const hint = document.getElementById("hint");
const voteButtons = [...document.querySelectorAll("[data-choice]")];
const startButton = document.getElementById("start");
const restartButton = document.getElementById("restart");
const snapshotButton = document.getElementById("snapshot");

const STORAGE_KEY = "rag-arena-index";
const TYPE_SPEED = 12;

let current = null;
let total = 0;
let lastResults = null;
let viewed = new Set();
let typed = false;
let busy = false;

const fa = (value) => value.toLocaleString("fa-IR");
const isMobile = () => window.matchMedia("(max-width: 640px)").matches;

function show(section) {
  for (const element of [introSection, quizSection, resultsSection]) {
    element.classList.toggle("hidden", element !== section);
  }
  window.scrollTo(0, 0);
}

function updateVoting() {
  // on desktop both answers are on screen, on mobile both must be opened first
  const ready = typed && !busy && (!isMobile() || viewed.size === 2);
  for (const button of voteButtons) {
    button.disabled = !ready;
  }
  hint.classList.toggle("hidden", !isMobile() || viewed.size === 2);
}

// fake the generation: reveal the precomputed text character by character
function type(element, text) {
  return new Promise((resolve) => {
    element.textContent = "";
    element.classList.add("typing");
    let position = 0;
    const timer = setInterval(() => {
      position += 1;
      element.textContent = text.slice(0, position);
      if (position >= text.length) {
        clearInterval(timer);
        element.classList.remove("typing");
        resolve();
      }
    }, TYPE_SPEED);
  });
}

async function showQuestion(index) {
  const response = await fetch(`/question?index=${index}`);
  if (!response.ok) {
    await showResults();
    return;
  }

  current = await response.json();
  total = current.total;

  progress.textContent = `سوال ${fa(index + 1)} از ${fa(total)}`;
  questionText.textContent = current.question;
  for (const element of answerTexts) {
    element.textContent = "";
  }
  viewed = new Set([0]);
  typed = false;
  busy = false;
  answersBox.dataset.active = "0";
  for (const tab of answerTabs) {
    tab.classList.toggle("is-active", tab.dataset.answer === "0");
  }
  updateVoting();
  show(quizSection);

  await Promise.all([
    type(answerTexts[0], current.answers[0].text),
    type(answerTexts[1], current.answers[1].text),
  ]);
  typed = true;
  updateVoting();
}

async function recordVote(choice) {
  busy = true;
  updateVoting();
  await fetch("/vote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: current.id, choice: choice }),
  });

  const next = current.index + 1;
  localStorage.setItem(STORAGE_KEY, String(next));

  if (next >= total) {
    await showResults();
  } else {
    await showQuestion(next);
  }
}

function renderScore(container, name, value) {
  const votes = value.wins + value.losses + value.ties;
  const winRate = votes === 0 ? 0 : Math.round((value.wins / votes) * 100);

  const row = document.createElement("div");
  row.className = "score-row";
  row.innerHTML = `
    <div class="score-head">
      <span class="score-name">${name}</span>
      <span class="score-rate">${fa(winRate)}٪ برد</span>
    </div>
    <span class="score-bar"><span style="width: ${winRate}%"></span></span>
    <div class="score-detail">${fa(value.wins)} برد، ${fa(value.losses)} باخت، ${fa(value.ties)} مساوی</div>
  `;
  container.appendChild(row);
}

async function showResults() {
  const response = await fetch("/results");
  lastResults = await response.json();

  document.getElementById("summary").textContent =
    `${fa(lastResults.votes)} رأی از ${fa(lastResults.rounds)} سوال`;

  const container = document.getElementById("score-rows");
  container.innerHTML = "";
  renderScore(container, "سامانه A", lastResults.score.api_a);
  renderScore(container, "سامانه B", lastResults.score.api_b);

  show(resultsSection);
}

async function saveSnapshot() {
  if (!lastResults) {
    return;
  }
  await document.fonts.ready;

  const width = 720;
  const height = 520;
  const scale = 2;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;

  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.direction = "rtl";
  ctx.textAlign = "right";

  const right = width - 48;
  const barLeft = right - 480;

  // paper and grid
  ctx.fillStyle = "#fbfaf6";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#e4e2da";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x <= width; x += 24) {
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
  }
  for (let y = 0; y <= height; y += 24) {
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
  }
  ctx.stroke();

  // header
  ctx.fillStyle = "#222";
  ctx.font = "400 24px Vazirmatn, sans-serif";
  ctx.fillText("دفترچه‌ی مقایسه", right, 72);

  ctx.fillStyle = "#3b5bdb";
  ctx.font = "300 14px Vazirmatn, sans-serif";
  ctx.fillText(new Date().toLocaleDateString("fa-IR"), right, 100);

  ctx.strokeStyle = "#b9b6aa";
  ctx.setLineDash([6, 6]);
  ctx.beginPath();
  ctx.moveTo(48, 132);
  ctx.lineTo(right, 132);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = "#222";
  ctx.font = "300 15px Vazirmatn, sans-serif";
  ctx.fillText(`مجموع رأی‌ها: ${fa(lastResults.votes)} از ${fa(lastResults.rounds)} سوال`, right, 168);

  // scores
  const rows = [
    ["سامانه A", lastResults.score.api_a],
    ["سامانه B", lastResults.score.api_b],
  ];

  let y = 224;
  for (const [name, value] of rows) {
    const votes = value.wins + value.losses + value.ties;
    const winRate = votes === 0 ? 0 : Math.round((value.wins / votes) * 100);
    const filled = 480 * (winRate / 100);

    ctx.fillStyle = "#222";
    ctx.font = "400 17px Vazirmatn, sans-serif";
    ctx.fillText(name, right, y);

    ctx.fillStyle = "#3b5bdb";
    ctx.font = "400 15px Vazirmatn, sans-serif";
    ctx.fillText(`${fa(winRate)}٪ برد`, barLeft, y);

    ctx.strokeStyle = "#222";
    ctx.strokeRect(barLeft, y + 16, 480, 18);
    ctx.fillStyle = "#3b5bdb";
    ctx.globalAlpha = 0.25;
    ctx.fillRect(right - filled, y + 17, filled, 16);
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#5f5d55";
    ctx.font = "300 14px Vazirmatn, sans-serif";
    ctx.fillText(`${fa(value.wins)} برد، ${fa(value.losses)} باخت، ${fa(value.ties)} مساوی`, right, y + 64);

    y += 120;
  }

  ctx.fillStyle = "#5f5d55";
  ctx.font = "300 13px Vazirmatn, sans-serif";
  ctx.fillText("تصویر ذخیره‌شده را برای من بفرست.", right, height - 48);

  canvas.toBlob((blob) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "rag-arena-results.png";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }, "image/png");
}

for (const button of voteButtons) {
  button.addEventListener("click", () => recordVote(button.dataset.choice));
}

for (const tab of answerTabs) {
  tab.addEventListener("click", () => {
    answersBox.dataset.active = tab.dataset.answer;
    viewed.add(Number(tab.dataset.answer));
    for (const other of answerTabs) {
      other.classList.toggle("is-active", other === tab);
    }
    updateVoting();
  });
}

window.addEventListener("resize", updateVoting);

snapshotButton.addEventListener("click", saveSnapshot);

restartButton.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
});

async function init() {
  const saved = Number(localStorage.getItem(STORAGE_KEY) || 0);
  const response = await fetch(`/question?index=${saved}`);

  if (response.ok) {
    const data = await response.json();
    total = data.total;
    if (saved === 0) {
      startButton.addEventListener("click", () => showQuestion(0));
    } else {
      startButton.textContent = `ادامه از سوال ${fa(saved + 1)}`;
      startButton.addEventListener("click", () => showQuestion(saved));
    }
  } else if (saved > 0) {
    await showResults();
  } else {
    startButton.addEventListener("click", () => showQuestion(0));
  }
}

init();
