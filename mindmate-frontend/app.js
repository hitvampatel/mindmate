/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║         MindMate — Frontend Application Logic               ║
 * ║         app.js  |  Vanilla JS — no build step needed        ║
 * ╚══════════════════════════════════════════════════════════════╝
 *
 * CONFIGURE: Set API_BASE to your Flask backend URL.
 *   Local dev:    http://localhost:5000/api
 *   Production:   https://yourdomain.com/api
 */

const API_BASE = "https://mindmate-ozom.onrender.com/api"
// ── App state ─────────────────────────────────────────────────
const state = {
  token:        localStorage.getItem("mm_token") || null,
  user:         JSON.parse(localStorage.getItem("mm_user") || "null"),
  currentPage:  "chat",
  selectedMood: null,
  selectedEnergy: null,
  isSending:    false,
  moodChart:    null,
  sentimentChart: null,
};

// ══════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  buildEmotionGrid();
  buildEnergyRating();

  if (state.token && state.user) {
    showApp();
    loadChatHistory();
    checkTodayMood();
    loadDashboardStats();
  } else {
    showAuth();
  }
});

// ══════════════════════════════════════════════════════════════
// API HELPER
// ══════════════════════════════════════════════════════════════
async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  try {
    const res = await fetch(API_BASE + path, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error("API error:", err);
    return { ok: false, status: 0, data: { message: "Could not reach the server. Is the backend running?" } };
  }
}

// ══════════════════════════════════════════════════════════════
// SCREEN MANAGEMENT
// ══════════════════════════════════════════════════════════════
function showAuth() {
  document.getElementById("auth-screen").classList.add("active");
  document.getElementById("app-screen").classList.remove("active");
}

function showApp() {
  document.getElementById("auth-screen").classList.remove("active");
  document.getElementById("app-screen").classList.add("active");
  populateSidebar();
}

function populateSidebar() {
  if (!state.user) return;
  const initial = (state.user.username || "U")[0].toUpperCase();
  document.getElementById("sb-avatar").textContent   = initial;
  document.getElementById("mob-avatar").textContent  = initial;
  document.getElementById("sb-username").textContent = state.user.username || "Student";
}

// ══════════════════════════════════════════════════════════════
// AUTH
// ══════════════════════════════════════════════════════════════
function switchTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("tab-login").classList.toggle("active", isLogin);
  document.getElementById("tab-signup").classList.toggle("active", !isLogin);
  document.getElementById("form-login").classList.toggle("active", isLogin);
  document.getElementById("form-signup").classList.toggle("active", !isLogin);

  const indicator = document.querySelector(".tab-indicator");
  indicator.classList.toggle("right", !isLogin);

  clearErrors();
}

async function handleLogin(e) {
  e.preventDefault();
  const identifier = document.getElementById("login-identifier").value.trim();
  const password   = document.getElementById("login-password").value;

  setLoading("btn-login", true);
  clearErrors();

  const isEmail = identifier.includes("@");
  const body = isEmail
    ? { email: identifier, password }
    : { username: identifier, password };

  const { ok, data } = await api("/auth/login", "POST", body);
  setLoading("btn-login", false);

  if (ok) {
    state.token = data.access_token;
    state.user  = data.user;
    localStorage.setItem("mm_token", state.token);
    localStorage.setItem("mm_user",  JSON.stringify(state.user));
    showApp();
    loadChatHistory();
    checkTodayMood();
    toast("success", `Welcome back, ${state.user.username}! 💙`);
  } else {
    showError("login-error", data.message || "Login failed. Please check your credentials.");
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const username = document.getElementById("signup-username").value.trim();
  const email    = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;

  setLoading("btn-signup", true);
  clearErrors();

  const { ok, data } = await api("/auth/signup", "POST", { username, email, password });
  setLoading("btn-signup", false);

  if (ok) {
    state.token = data.access_token;
    state.user  = data.user;
    localStorage.setItem("mm_token", state.token);
    localStorage.setItem("mm_user",  JSON.stringify(state.user));
    showApp();
    toast("success", `Welcome to MindMate, ${state.user.username}! 🎉`);
  } else {
    const msg = data.errors ? data.errors.join(" ") : (data.message || "Signup failed.");
    showError("signup-error", msg);
  }
}

async function handleLogout() {
  await api("/auth/logout", "POST");
  state.token = null;
  state.user  = null;
  localStorage.removeItem("mm_token");
  localStorage.removeItem("mm_user");

  // Clear chat messages UI
  const msgs = document.getElementById("chat-messages");
  msgs.innerHTML = buildWelcomeHTML();

  showAuth();
  toast("info", "You've been signed out. Take care! 🌟");
}

// Password strength meter
document.getElementById("signup-password").addEventListener("input", function() {
  const pw = this.value;
  const strength = getPasswordStrength(pw);
  const bar = document.getElementById("pw-strength");
  bar.innerHTML = `<div class="pw-strength-fill" style="width:${strength.pct}%; background:${strength.color}"></div>`;
});

function getPasswordStrength(pw) {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const map = [
    { pct: 20, color: "#ef4444" },
    { pct: 40, color: "#f97316" },
    { pct: 60, color: "#eab308" },
    { pct: 80, color: "#84cc16" },
    { pct: 100, color: "#22c55e" },
  ];
  return map[Math.min(score, 4)];
}

// ══════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════
function navigate(page, linkEl) {
  // Hide all pages
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));

  // Show target page
  document.getElementById(`page-${page}`).classList.add("active");
  if (linkEl) linkEl.classList.add("active");

  state.currentPage = page;
  closeSidebar();

  // Lazy-load page data
  if (page === "mood")       { checkTodayMood(); loadMoodHistory(); }
  if (page === "dashboard")  { loadDashboard(); }
}

function openSidebar() {
  document.getElementById("sidebar").classList.add("open");
  document.getElementById("sidebar-overlay").classList.remove("hidden");
}
function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-overlay").classList.add("hidden");
}

// ══════════════════════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════════════════════
async function loadChatHistory() {
  const { ok, data } = await api("/chat/history?limit=30");
  if (!ok || !data.messages?.length) return;

  // Clear welcome, render history
  const container = document.getElementById("chat-messages");
  container.innerHTML = "";
  data.messages.forEach(m => appendMessage(m.role, m.content, m));
  scrollToBottom();
}

function sendQuickPrompt(btn) {
  const text = btn.textContent.replace(/^[^\w]+/, "").trim();
  document.getElementById("chat-input").value = text;
  sendMessage();
}

async function sendMessage() {
  if (state.isSending) return;

  const input = document.getElementById("chat-input");
  const text  = input.value.trim();
  if (!text) return;

  state.isSending = true;
  input.value = "";
  autoResize(input);
  document.getElementById("btn-send").disabled = true;

  // Remove welcome screen
  const container = document.getElementById("chat-messages");
  const welcome = container.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  // Show user message immediately
  appendMessage("user", text);
  scrollToBottom();

  // Show typing
  document.getElementById("typing-indicator").classList.remove("hidden");
  scrollToBottom();

  const { ok, data } = await api("/chat", "POST", { message: text });

  document.getElementById("typing-indicator").classList.add("hidden");
  state.isSending = false;
  document.getElementById("btn-send").disabled = false;

  if (ok) {
    appendMessage("assistant", data.ai_response.content, data.ai_response);

    // Show wellness tip bar
    if (data.ai_response.wellness_tip) {
      const bar = document.getElementById("wellness-tip-bar");
      document.getElementById("wellness-tip-text").textContent = data.ai_response.wellness_tip;
      bar.classList.remove("hidden");
    }

    // Crisis banner
    if (data.crisis_info?.crisis_detected) {
      showCrisisBanner(data.crisis_info);
    }

    // Update live sentiment
    if (data.sentiment) {
      updateLiveSentiment(data.sentiment.label, data.sentiment.emoji);
    }
  } else {
    appendMessage("assistant", "I'm having a little trouble connecting right now. Please try again in a moment. 💙");
  }

  scrollToBottom();
  input.focus();
}

function appendMessage(role, content, meta = {}) {
  const container = document.getElementById("chat-messages");
  const row = document.createElement("div");
  row.className = `msg-row ${role === "user" ? "user-row" : "ai-row"}`;

  const avatarText = role === "user"
    ? (state.user?.username || "U")[0].toUpperCase()
    : "🤖";

  const time = formatTime(meta.timestamp || new Date().toISOString());

  let extras = "";
  if (role === "assistant") {
    if (meta.sentiment_label) {
      const sentimentEmoji = sentimentToEmoji(meta.sentiment_label);
      extras += `<span class="msg-sentiment-badge">${sentimentEmoji} ${meta.sentiment_label || "neutral"}</span>`;
    }
    if (meta.wellness_tip) {
      extras += `<div class="wellness-tip-card">${meta.wellness_tip}</div>`;
    }
    if (meta.follow_up) {
      extras += `<div class="follow-up-text">💬 ${meta.follow_up}</div>`;
    }
  }

  // Sanitize and convert line breaks
  const safeContent = escapeHtml(content).replace(/\n/g, "<br>");

  row.innerHTML = `
    <div class="msg-avatar">${avatarText}</div>
    <div class="msg-content">
      <div class="msg-bubble">${safeContent}${extras}</div>
      <span class="msg-time">${time}</span>
    </div>`;

  container.appendChild(row);
}

function showCrisisBanner(crisisInfo) {
  const banner = document.getElementById("crisis-banner");
  document.getElementById("crisis-msg").textContent = crisisInfo.safe_message || "";
  banner.classList.remove("hidden");

  const resourcesEl = document.getElementById("crisis-resources");
  resourcesEl.innerHTML = "";
  if (crisisInfo.resources) {
    crisisInfo.resources.forEach(r => {
      const a = document.createElement("a");
      a.className = "crisis-resource-btn";
      a.textContent = `${r.name}: ${r.contact}`;
      if (r.type === "web") { a.href = r.contact; a.target = "_blank"; }
      else                   { a.href = `tel:${r.contact.replace(/\D/g, "")}`; }
      resourcesEl.appendChild(a);
    });
  }
}

async function clearChat() {
  if (!confirm("Clear your entire conversation history? This cannot be undone.")) return;
  const { ok } = await api("/chat/history", "DELETE", { confirm: true });
  if (ok) {
    document.getElementById("chat-messages").innerHTML = buildWelcomeHTML();
    document.getElementById("crisis-banner").classList.add("hidden");
    document.getElementById("wellness-tip-bar").classList.add("hidden");
    toast("info", "Conversation history cleared.");
  }
}

// Live sentiment as user types
let sentimentDebounce;
function handleInputChange(el) {
  autoResize(el);
  clearTimeout(sentimentDebounce);
  if (el.value.length < 8) return;
  sentimentDebounce = setTimeout(async () => {
    const { ok, data } = await api("/sentiment-score", "POST", { text: el.value });
    if (ok && data.sentiment) {
      updateLiveSentiment(data.sentiment.label, data.sentiment.emoji);
    }
  }, 600);
}

function updateLiveSentiment(label, emoji) {
  document.getElementById("live-emoji").textContent = emoji || "😐";
  document.getElementById("live-label").textContent = label || "neutral";
}

function handleChatKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ══════════════════════════════════════════════════════════════
// MOOD CHECK-IN
// ══════════════════════════════════════════════════════════════
const EMOTIONS = [
  { key: "happy",       emoji: "😊" },
  { key: "calm",        emoji: "😌" },
  { key: "neutral",     emoji: "😐" },
  { key: "anxious",     emoji: "😰" },
  { key: "sad",         emoji: "😢" },
  { key: "angry",       emoji: "😠" },
  { key: "stressed",    emoji: "😤" },
  { key: "excited",     emoji: "🤩" },
  { key: "grateful",    emoji: "🙏" },
  { key: "lonely",      emoji: "🥺" },
  { key: "overwhelmed", emoji: "😵" },
  { key: "hopeful",     emoji: "🌱" },
  { key: "tired",       emoji: "😴" },
  { key: "motivated",   emoji: "💪" },
  { key: "confused",    emoji: "😕" },
];

function buildEmotionGrid() {
  const grid = document.getElementById("emotion-grid");
  EMOTIONS.forEach(em => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "emotion-chip";
    chip.dataset.key = em.key;
    chip.textContent = `${em.emoji} ${em.key}`;
    chip.onclick = () => selectEmotion(em.key, chip);
    grid.appendChild(chip);
  });
}

function selectEmotion(key, el) {
  document.querySelectorAll(".emotion-chip").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
  state.selectedMood = key;
}

function buildEnergyRating() {
  const wrap = document.getElementById("energy-rating");
  for (let i = 1; i <= 5; i++) {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "rating-dot";
    dot.dataset.val = i;
    dot.textContent = i;
    dot.onclick = () => selectEnergy(i, dot);
    wrap.appendChild(dot);
  }
}

function selectEnergy(val, el) {
  document.querySelectorAll(".rating-dot").forEach(d => d.classList.remove("selected"));
  el.classList.add("selected");
  state.selectedEnergy = val;
}

function updateMoodScore(val) {
  document.getElementById("score-display").textContent = val;
  // Update slider track colour
  const pct = ((val - 1) / 9) * 100;
  const slider = document.getElementById("mood-score");
  slider.style.background =
    `linear-gradient(to right, var(--purple) ${pct}%, var(--bg-deep) ${pct}%)`;
}

document.getElementById("mood-note").addEventListener("input", function() {
  document.getElementById("mood-char").textContent = `${this.value.length} / 500`;
});

async function handleMoodSubmit(e) {
  e.preventDefault();

  const score    = parseInt(document.getElementById("mood-score").value);
  const note     = document.getElementById("mood-note").value.trim();
  const sleepRaw = document.getElementById("sleep-hrs").value;
  const sleep    = sleepRaw ? parseFloat(sleepRaw) : null;

  setLoading("btn-mood-submit", true);
  document.getElementById("mood-error").classList.add("hidden");
  document.getElementById("mood-success").classList.add("hidden");

  const body = {
    mood_score: score,
    mood_label: state.selectedMood || undefined,
    note:       note || undefined,
    energy:     state.selectedEnergy || undefined,
    sleep_hrs:  sleep || undefined,
  };

  const { ok, data } = await api("/mood-submit", "POST", body);
  setLoading("btn-mood-submit", false);

  if (ok) {
    showSuccess("mood-success", `✅ ${data.message}`);
    toast("success", "Mood check-in saved! 🌱");
    updateSidebarScore();
    loadMoodHistory();
    // Mark as checked in
    setTimeout(() => {
      const card = document.getElementById("mood-already-in");
      document.getElementById("checkedin-summary").textContent =
        `Mood: ${score}/10${state.selectedMood ? ` · ${state.selectedMood}` : ""}`;
      card.classList.remove("hidden");
    }, 800);
  } else {
    const msg = data.message || "Could not save mood. Please try again.";
    showError("mood-error", msg);
  }
}

async function checkTodayMood() {
  const { ok, data } = await api("/mood-today");
  if (!ok) return;

  const badge = document.getElementById("mood-badge");
  if (!data.checked_in) {
    badge.classList.remove("hidden");  // Show "!" nudge badge
  } else {
    badge.classList.add("hidden");
    document.getElementById("checkedin-summary").textContent =
      `Mood: ${data.entry.mood_score}/10${data.entry.mood_label ? ` · ${data.entry.mood_label}` : ""}`;
    document.getElementById("mood-already-in").classList.remove("hidden");
  }
}

function showMoodForm() {
  document.getElementById("mood-already-in").classList.add("hidden");
  document.getElementById("mood-success").classList.add("hidden");
}

async function loadMoodHistory() {
  const { ok, data } = await api("/mood-history?days=14&limit=14");
  if (!ok || !data.entries?.length) return;

  const container = document.getElementById("mood-mini-chart");
  container.innerHTML = "";

  // Reverse so oldest first
  const entries = [...data.entries].reverse();
  const maxScore = 10;

  entries.forEach(entry => {
    const date    = new Date(entry.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const pct     = (entry.mood_score / maxScore) * 100;
    const color   = moodColor(entry.mood_score);
    container.innerHTML += `
      <div class="mood-bar-item">
        <span class="mood-bar-date">${date}</span>
        <div class="mood-bar-wrap">
          <div class="mood-bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="mood-bar-score">${entry.mood_score}</span>
      </div>`;
  });

  // Stats
  if (data.stats) {
    const s = data.stats;
    document.getElementById("mood-stats-row").innerHTML = `
      <div class="stat-chip"><span class="stat-chip-val">${s.avg_mood}</span><span class="stat-chip-label">Avg Mood</span></div>
      <div class="stat-chip"><span class="stat-chip-val">${s.max_mood}</span><span class="stat-chip-label">Best Day</span></div>
      <div class="stat-chip"><span class="stat-chip-val">${s.total_logs}</span><span class="stat-chip-label">Check-ins</span></div>
      <div class="stat-chip"><span class="stat-chip-val" style="font-size:14px;text-transform:capitalize">${s.trend}</span><span class="stat-chip-label">Trend</span></div>`;
  }
}

// ══════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════
async function loadDashboardStats() {
  const { ok, data } = await api("/dashboard-stats");
  if (!ok) return;

  document.getElementById("sb-streak").textContent = `🔥 ${data.streak} day streak`;

  const score = data.avg_mood_week ? Math.round((data.avg_mood_week / 10) * 100) : 0;
  document.getElementById("sb-score-fill").style.width = `${score}%`;
  document.getElementById("sb-score-val").textContent  = `${score}`;
}

async function loadDashboard() {
  const { ok, data } = await api("/dashboard-data");
  if (!ok) { toast("error", "Could not load dashboard data."); return; }

  // KPI cards
  document.getElementById("kpi-wellness-val").textContent = `${data.wellness_score || 0}/100`;
  document.getElementById("kpi-wellness-bar").style.width = `${data.wellness_score || 0}%`;
  document.getElementById("kpi-mood-val").textContent     = data.user_summary?.avg_mood_week  || (data.mood_chart?.at(-1)?.mood_score ?? "—");
  document.getElementById("kpi-streak-val").textContent   = `${data.streak} day${data.streak !== 1 ? "s" : ""}`;
  document.getElementById("kpi-chats-val").textContent    = data.user_summary?.total_chat_messages || 0;

  // Sidebar score
  document.getElementById("sb-streak").textContent       = `🔥 ${data.streak} day streak`;
  document.getElementById("sb-score-fill").style.width   = `${data.wellness_score || 0}%`;
  document.getElementById("sb-score-val").textContent    = `${data.wellness_score || 0}`;

  // Charts
  renderMoodChart(data.mood_chart || []);
  renderSentimentChart(data.sentiment_chart || []);

  // Insights
  renderInsights(data.insights || []);

  // Mood distribution
  renderMoodDistribution(data.mood_distribution || {});

  // Recent messages
  renderRecentMessages(data.recent_messages || []);
}

function renderMoodChart(chartData) {
  const canvas = document.getElementById("chart-mood");
  const empty  = document.getElementById("mood-chart-empty");

  if (!chartData.length) {
    canvas.classList.add("hidden");
    empty.classList.remove("hidden");
    return;
  }

  canvas.classList.remove("hidden");
  empty.classList.add("hidden");

  if (state.moodChart) state.moodChart.destroy();

  state.moodChart = new Chart(canvas, {
    type: "line",
    data: {
      labels:   chartData.map(d => d.date),
      datasets: [{
        label:           "Mood",
        data:            chartData.map(d => d.mood_score),
        borderColor:     "#7B6FE8",
        backgroundColor: "rgba(123,111,232,0.15)",
        borderWidth:     2.5,
        pointBackgroundColor: "#7B6FE8",
        pointBorderColor:     "#0F0E1F",
        pointBorderWidth:     2,
        pointRadius:     5,
        tension:         0.4,
        fill:            true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          min: 1, max: 10,
          grid:  { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#6B6A8A", stepSize: 2, font: { size: 11 } },
        },
        x: {
          grid:  { display: false },
          ticks: { color: "#6B6A8A", font: { size: 11 } },
        }
      }
    }
  });
}

function renderSentimentChart(chartData) {
  const canvas = document.getElementById("chart-sentiment");
  const empty  = document.getElementById("sentiment-chart-empty");

  if (!chartData.length) {
    canvas.classList.add("hidden");
    empty.classList.remove("hidden");
    return;
  }

  canvas.classList.remove("hidden");
  empty.classList.add("hidden");

  if (state.sentimentChart) state.sentimentChart.destroy();

  state.sentimentChart = new Chart(canvas, {
    type: "line",
    data: {
      labels:   chartData.map(d => d.date),
      datasets: [{
        label:           "Sentiment",
        data:            chartData.map(d => d.avg_polarity),
        borderColor:     "#3EC9C9",
        backgroundColor: "rgba(62,201,201,0.12)",
        borderWidth:     2.5,
        pointBackgroundColor: "#3EC9C9",
        pointBorderColor:     "#0F0E1F",
        pointBorderWidth:     2,
        pointRadius:     5,
        tension:         0.4,
        fill:            true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          min: -1, max: 1,
          grid:  { color: "rgba(255,255,255,0.05)" },
          ticks: {
            color: "#6B6A8A", font: { size: 11 },
            callback: v => v > 0 ? `+${v}` : v,
          },
        },
        x: {
          grid:  { display: false },
          ticks: { color: "#6B6A8A", font: { size: 11 } },
        }
      }
    }
  });
}

function renderInsights(insights) {
  const list = document.getElementById("insights-list");
  if (!insights.length) {
    list.innerHTML = `<p class="empty-state">Start using MindMate to generate personal insights.</p>`;
    return;
  }
  list.innerHTML = insights.map((ins, i) =>
    `<div class="insight-item" style="animation-delay:${i * 0.1}s">${escapeHtml(ins)}</div>`
  ).join("");
}

function renderMoodDistribution(dist) {
  const container = document.getElementById("mood-dist-list");
  const entries   = Object.entries(dist).sort((a, b) => b[1] - a[1]);

  if (!entries.length) {
    container.innerHTML = `<p class="empty-state">No mood labels logged yet.</p>`;
    return;
  }

  const max = entries[0][1];
  container.innerHTML = entries.map(([label, count]) => {
    const pct = Math.round((count / max) * 100);
    const em  = EMOTIONS.find(e => e.key === label)?.emoji || "🔵";
    return `
      <div class="dist-item">
        <span class="dist-label">${em} ${label}</span>
        <div class="dist-bar-wrap"><div class="dist-bar-fill" style="width:${pct}%"></div></div>
        <span class="dist-count">${count}</span>
      </div>`;
  }).join("");
}

function renderRecentMessages(messages) {
  const container = document.getElementById("recent-messages-list");
  if (!messages.length) {
    container.innerHTML = `<p class="empty-state">No conversations yet. Start chatting!</p>`;
    return;
  }

  container.innerHTML = messages.map(m => {
    const roleClass = m.role === "user" ? "role-user" : "role-assistant";
    const label     = m.role === "user" ? "You" : "MindMate";
    const preview   = (m.content || "").slice(0, 120) + (m.content?.length > 120 ? "..." : "");
    const time      = formatTime(m.timestamp);
    const sentColor = m.sentiment_label ? sentimentColor(m.sentiment_label) : "transparent";

    return `
      <div class="recent-msg-item">
        <span class="recent-msg-role ${roleClass}">${label}</span>
        <span class="recent-msg-text">${escapeHtml(preview)}</span>
        ${m.sentiment_label ? `<span class="recent-msg-sentiment" style="background:${sentColor}20;color:${sentColor}">${sentimentToEmoji(m.sentiment_label)} ${m.sentiment_label}</span>` : ""}
        <span class="recent-msg-time">${time}</span>
      </div>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ══════════════════════════════════════════════════════════════
function buildWelcomeHTML() {
  return `
    <div class="chat-welcome">
      <div class="welcome-icon">💙</div>
      <h3>Hey there, I'm MindMate.</h3>
      <p>This is a safe, private space just for you. Share how you're feeling — there's no right or wrong answer here.</p>
      <div class="quick-prompts">
        <button class="quick-prompt" onclick="sendQuickPrompt(this)">😰 I'm stressed about exams</button>
        <button class="quick-prompt" onclick="sendQuickPrompt(this)">😴 I haven't been sleeping well</button>
        <button class="quick-prompt" onclick="sendQuickPrompt(this)">😔 I've been feeling lonely</button>
        <button class="quick-prompt" onclick="sendQuickPrompt(this)">🙂 I just want to check in</button>
      </div>
    </div>`;
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function scrollToBottom() {
  const container = document.getElementById("chat-messages");
  container.scrollTop = container.scrollHeight;
}

function setLoading(btnId, loading) {
  const btn  = document.getElementById(btnId);
  if (!btn) return;
  const text = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = loading;
  if (text)   text.classList.toggle("hidden", loading);
  if (loader) loader.classList.toggle("hidden", !loading);
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}

function showSuccess(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}

function clearErrors() {
  document.querySelectorAll(".form-error, .form-success").forEach(el => el.classList.add("hidden"));
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function moodColor(score) {
  if (score >= 8) return "#22c55e";
  if (score >= 6) return "#84cc16";
  if (score >= 4) return "#eab308";
  if (score >= 2) return "#f97316";
  return "#ef4444";
}

function sentimentColor(label) {
  const map = {
    very_positive: "#22c55e", positive: "#84cc16",
    neutral:       "#94a3b8",
    negative:      "#f59e0b", very_negative: "#ef4444",
  };
  return map[label] || "#94a3b8";
}

function sentimentToEmoji(label) {
  const map = {
    very_positive: "😊", positive: "🙂",
    neutral:       "😐",
    negative:      "😟", very_negative: "😢",
  };
  return map[label] || "😐";
}

function updateSidebarScore() { loadDashboardStats(); }

function togglePw(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === "password") { input.type = "text";  btn.textContent = "🙈"; }
  else                           { input.type = "password"; btn.textContent = "👁"; }
}

// Toast notifications
function toast(type, message, duration = 3500) {
  const container = document.getElementById("toast-container");
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  const icons = { success: "✅", error: "❌", info: "💙" };
  t.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

// Init mood slider visual
updateMoodScore(5);
