"use strict";

const API_URL = "/api/v1/chat";
const SESSION_KEY = "demotel.session_id";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messagesEl = document.getElementById("messages");
const scrollEl = document.getElementById("chat-scroll");
const loadingEl = document.getElementById("loading");
const sendBtn = document.getElementById("send-btn");
const welcomeEl = document.getElementById("welcome");
const noticeEl = document.getElementById("notice");
const newChatBtn = document.getElementById("new-chat");
const clearChatBtn = document.getElementById("clear-chat");
const historyBtn = document.getElementById("session-history");
const mobileClearBtn = document.getElementById("mobile-clear");
const mobileHistoryBtn = document.getElementById("mobile-history");
const statusBtn = document.getElementById("service-status");
const connectionForm = document.getElementById("connection-form");
const tokenInput = document.getElementById("api-token");
const settingsEl = document.getElementById("connection-settings");
const promptButtons = [...document.querySelectorAll("[data-prompt]")];
const CATEGORY_LABELS = {
  internet_paketleri: "İnternet paketleri",
  fiyatlandirma: "Fiyatlandırma",
  fatura: "Fatura ve ödemeler",
  teknik_destek: "Teknik destek",
  taahhut: "Taahhüt",
  genel: "Genel bilgiler",
  billing: "Fatura ve ödemeler",
  technical: "Teknik destek",
  packages: "Paketler",
  general: "Genel bilgiler",
};
const INTENT_LABELS = { billing: "Fatura", technical: "Teknik destek", packages: "Paketler", general: "Genel destek" };
const AUTH_NOTICE = "Servis erişim anahtarı gerektiriyor. Sağ üstteki bağlantı ayarlarından anahtarı girip yeniden deneyin.";
let sessionId = readSession();
let apiToken = "";
let busy = false;
let statusBusy = false;
let turnCount = 0;

function readSession() {
  try {
    const value = sessionStorage.getItem(SESSION_KEY);
    return value && UUID_PATTERN.test(value) ? value : null;
  } catch {
    return null;
  }
}

function saveSession(value) {
  sessionId = typeof value === "string" && UUID_PATTERN.test(value) ? value : null;
  try {
    if (sessionId) sessionStorage.setItem(SESSION_KEY, sessionId);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // The session still works in memory when browser storage is unavailable.
  }
  updateSessionSummary();
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function showNotice(text = "") {
  noticeEl.textContent = text;
  noticeEl.classList.toggle("hidden", !text);
}

function scrollToLatest() {
  scrollEl.scrollTop = scrollEl.scrollHeight;
}

function updateSessionSummary() {
  document.getElementById("session-summary").textContent = turnCount ? `${turnCount} mesaj · Bu tarayıcı oturumu` : "Yeni bir başlangıç";
  clearChatBtn.disabled = busy || !sessionId;
  mobileClearBtn.disabled = busy || !sessionId;
  historyBtn.disabled = busy;
  mobileHistoryBtn.disabled = busy || !sessionId;
}

function appendSource(content, source) {
  if (!source || typeof source.matched_question !== "string") return;
  const card = node("div", "source-card");
  const heading = node("div", "source-heading");
  heading.append(node("span", "source-number", "1"), node("span", "", `Bilgi kaynağı · ${CATEGORY_LABELS[source.category] || "DemoTel bilgi tabanı"}`));
  card.append(heading, node("p", "source-question", source.matched_question));
  content.appendChild(card);
}

function appendResponseDetails(content, data) {
  const tags = node("div", "response-tags");
  if (data.handoff) tags.appendChild(node("span", "response-tag handoff", "Uzman desteği gerekli"));
  else if (data.fallback) tags.appendChild(node("span", "response-tag handoff", "Ek bilgi gerekli"));
  if (data.pii_redacted) tags.appendChild(node("span", "response-tag", "Kişisel bilgiler maskelendi"));
  if (tags.childElementCount) content.appendChild(tags);

  const rows = [];
  if (INTENT_LABELS[data.intent]) rows.push(["Destek konusu", INTENT_LABELS[data.intent]]);
  if (typeof data.latency_ms === "number" && Number.isFinite(data.latency_ms)) rows.push(["Yanıt süresi", `${Math.round(data.latency_ms)} ms`]);
  if (typeof data.cache_hit === "boolean") rows.push(["Önbellek", data.cache_hit ? "Önbellekten yanıtlandı" : "Yeni yanıt"]);
  if (typeof data.pii_redacted === "boolean") rows.push(["Gizlilik filtresi", data.pii_redacted ? "Maskeleme uygulandı" : "Desteklenen veri örüntüsü bulunmadı"]);
  if (data.source && typeof data.source.entry_id === "string") rows.push(["Kaynak kimliği", data.source.entry_id]);
  if (typeof data.trace_id === "string") rows.push(["İşlem kimliği", data.trace_id]);
  if (Array.isArray(data.steps)) {
    const steps = data.steps.filter((step) => typeof step === "string").slice(0, 12);
    if (steps.length) rows.push(["İşlem adımları", steps.join(" → ")]);
  }
  if (!rows.length) return;
  const details = node("details", "response-details");
  const definition = node("dl");
  rows.forEach(([label, value]) => definition.append(node("dt", "", label), node("dd", "", value)));
  details.append(node("summary", "", "Yanıt ayrıntıları"), definition);
  content.appendChild(details);
}

function appendMessage(text, role, data = null, isError = false) {
  welcomeEl.classList.add("hidden");
  const item = node("li", `message ${role}${isError ? " error" : ""}`);
  const content = node("div", "message-content");
  if (role === "assistant") {
    const avatar = node("span", "assistant-avatar", "D");
    avatar.setAttribute("aria-hidden", "true");
    item.appendChild(avatar);
    content.appendChild(node("span", "message-author", "DemoTel Asistan"));
  } else {
    content.appendChild(node("span", "sr-only", "Siz: "));
  }
  const body = node("div", "message-text", text);
  content.appendChild(body);
  if (data && role === "assistant") {
    appendSource(content, data.source);
    appendResponseDetails(content, data);
  }
  item.appendChild(content);
  messagesEl.appendChild(item);
  turnCount += 1;
  updateSessionSummary();
  scrollToLatest();
  return body;
}

function setBusy(value, withLoading = true) {
  busy = value;
  loadingEl.classList.toggle("hidden", !value || !withLoading);
  messagesEl.setAttribute("aria-busy", String(value));
  sendBtn.disabled = value;
  input.disabled = value;
  newChatBtn.disabled = value;
  tokenInput.disabled = value;
  connectionForm.querySelector("button").disabled = value;
  promptButtons.forEach((button) => { button.disabled = value; });
  updateSessionSummary();
  if (value && withLoading) scrollToLatest();
}

async function request(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  const headers = new Headers(options.headers || {});
  if (apiToken) headers.set("Authorization", `Bearer ${apiToken}`);
  try {
    return await fetch(url, { ...options, headers, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

function resetConversation() {
  saveSession(null);
  messagesEl.replaceChildren();
  turnCount = 0;
  welcomeEl.classList.remove("hidden");
  input.value = "";
  input.style.height = "";
  showNotice();
  updateSessionSummary();
  scrollEl.scrollTop = 0;
  input.focus();
}

async function restoreConversation() {
  if (!sessionId || busy) return;
  setBusy(true, false);
  try {
    const response = await request(`/api/v1/sessions/${encodeURIComponent(sessionId)}`);
    if (response.status === 404 || response.status === 410) {
      resetConversation();
      showNotice("Önceki sohbetin süresi dolmuş. Yeni bir sohbet başlatabilirsiniz.");
      return;
    }
    if (response.status === 401 || response.status === 403) {
      showNotice(AUTH_NOTICE);
      return;
    }
    if (!response.ok) throw new Error("session_unavailable");
    const data = await response.json();
    if (!Array.isArray(data.messages)) throw new Error("invalid_history");
    messagesEl.replaceChildren();
    turnCount = 0;
    welcomeEl.classList.remove("hidden");
    data.messages.forEach((message) => {
      if (["user", "assistant"].includes(message.role) && typeof message.content === "string") appendMessage(message.content, message.role);
    });
    updateSessionSummary();
    showNotice();
  } catch {
    showNotice("Sohbet geçmişi şu anda yüklenemiyor. Yeni bir soru sorabilir veya tekrar deneyebilirsiniz.");
  } finally {
    setBusy(false, false);
  }
}

async function updateServiceStatus() {
  if (statusBusy) return;
  statusBusy = true;
  statusBtn.disabled = true;
  statusBtn.className = "status-pill checking";
  const statusLabel = document.getElementById("status-label");
  statusLabel.textContent = "Denetleniyor…";
  try {
    const response = await request("/api/v1/status");
    if (response.status === 401 || response.status === 403) {
      statusBtn.className = "status-pill offline";
      statusLabel.textContent = "Erişim anahtarı gerekli";
      statusBtn.setAttribute("aria-label", "Erişim anahtarı gerekli. Bağlantı ayarlarını aç");
      const row = node("div");
      row.append(node("dt", "", "Erişim"), node("dd", "", "Anahtar gerekli"));
      document.getElementById("service-info").replaceChildren(row);
      showNotice(AUTH_NOTICE);
      return;
    }
    if (!response.ok) throw new Error("status_unavailable");
    const data = await response.json();
    const readiness = await request("/ready");
    if (!readiness.ok) throw new Error("dependencies_unavailable");
    statusBtn.className = "status-pill";
    statusLabel.textContent =
      data.generation === "llm"
        ? "Hazır · LLM seçili"
        : data.mode === "demo"
          ? "Hazır · Demo modu"
          : "Servis hazır";
    statusBtn.setAttribute("aria-label", "Servis hazır. Durumu yenile");
    const rows = [
      ["Çalışma modu", data.mode],
      ["Arama", data.retrieval],
      ["Yanıt üretimi", data.generation === "llm" ? "LLM" : "FAQ"],
      ["Oturum deposu", data.storage],
      ["Gizlilik filtresi", data.pii],
      ["İş akışı", data.orchestration],
      ["Yeniden sıralama", data.reranker],
      ["Bilgi kaydı", data.knowledge_entries],
    ];
    const info = document.getElementById("service-info");
    info.replaceChildren();
    rows.forEach(([label, value]) => {
      if (typeof value !== "string" && typeof value !== "number") return;
      const row = node("div");
      row.append(node("dt", "", label), node("dd", "", String(value).slice(0, 120)));
      info.appendChild(row);
    });
    if (typeof data.version === "string") document.getElementById("app-version").textContent = `v${data.version.slice(0, 25)}`;
  } catch {
    statusBtn.className = "status-pill offline";
    statusLabel.textContent = "Bağlantı bekleniyor";
    statusBtn.setAttribute("aria-label", "Servise ulaşılamıyor. Yeniden dene");
    const row = node("div");
    row.append(node("dt", "", "Durum"), node("dd", "", "Servise ulaşılamıyor"));
    document.getElementById("service-info").replaceChildren(row);
  } finally {
    statusBusy = false;
    statusBtn.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || busy) return;
  showNotice();
  const userBody = appendMessage(message, "user");
  input.value = "";
  input.style.height = "";
  setBusy(true);
  try {
    const payload = { message };
    if (sessionId) payload.session_id = sessionId;
    const response = await request(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = response.status === 401 || response.status === 403
        ? AUTH_NOTICE
        : response.status === 429
          ? "Kısa sürede çok fazla istek gönderdiniz. Biraz bekleyip tekrar deneyin."
          : response.status === 422
            ? "Mesajınızı kontrol edip tekrar gönderin. En fazla 2000 karakter kullanabilirsiniz."
            : "Yanıt şu anda hazırlanamadı. Lütfen biraz sonra tekrar deneyin.";
      appendMessage(error, "assistant", null, true);
      return;
    }
    const data = await response.json();
    if (typeof data.answer !== "string") throw new Error("invalid_response");
    if (typeof data.safe_message === "string") userBody.textContent = data.safe_message;
    if (typeof data.session_id === "string" && UUID_PATTERN.test(data.session_id)) saveSession(data.session_id);
    appendMessage(data.answer, "assistant", data);
  } catch {
    appendMessage("Servise ulaşılamadı veya yanıt süresi aşıldı. Bağlantınızı kontrol edip tekrar deneyin.", "assistant", null, true);
  } finally {
    setBusy(false);
    input.focus();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
promptButtons.forEach((button) => button.addEventListener("click", () => {
  if (busy) return;
  input.value = button.dataset.prompt;
  input.dispatchEvent(new Event("input"));
  input.focus();
}));
newChatBtn.addEventListener("click", () => { if (!busy) resetConversation(); });
historyBtn.addEventListener("click", restoreConversation);
mobileHistoryBtn.addEventListener("click", async () => { await restoreConversation(); settingsEl.open = false; });
statusBtn.addEventListener("click", () => {
  if (document.getElementById("status-label").textContent === "Erişim anahtarı gerekli") {
    settingsEl.open = true;
    tokenInput.focus();
  } else updateServiceStatus();
});
connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  apiToken = tokenInput.value.trim();
  settingsEl.open = false;
  showNotice();
  await updateServiceStatus();
  await restoreConversation();
});

async function clearConversation() {
  if (!sessionId || busy) return;
  setBusy(true, false);
  try {
    const response = await request(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    if (response.status === 401 || response.status === 403) {
      showNotice(AUTH_NOTICE);
      return;
    }
    if (!response.ok && response.status !== 404) throw new Error("delete_failed");
    resetConversation();
    showNotice("Bu sohbetin sunucudaki geçmişi silindi.");
    settingsEl.open = false;
  } catch {
    showNotice("Sohbet geçmişi silinemedi. Lütfen tekrar deneyin.");
  } finally {
    setBusy(false, false);
    input.focus();
  }
}
clearChatBtn.addEventListener("click", clearConversation);
mobileClearBtn.addEventListener("click", clearConversation);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && settingsEl.open) {
    settingsEl.open = false;
    settingsEl.querySelector("summary").focus();
  }
});
document.addEventListener("click", (event) => {
  if (settingsEl.open && !settingsEl.contains(event.target) && !statusBtn.contains(event.target)) settingsEl.open = false;
});

updateSessionSummary();
updateServiceStatus();
restoreConversation();
