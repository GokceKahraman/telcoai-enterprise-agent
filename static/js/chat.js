"use strict";

const API_URL = "/api/v1/chat";
const SESSION_KEY = "demotel.session_id";
const LANGUAGE_KEY = "demotel.locale";
const UI = {
  "tr-TR": {
    lang:"SOHBET DİLİ", agent:"DemoTel Asistan", status:"Çevrimiçi · Sana yardımcı olmaya hazır", close:"Sohbeti kapat", fresh:"Yeni sohbet başlat", eyebrow:"DEMOTEL ASİSTAN",
    welcome:"Merhaba! Size nasıl yardımcı olabilirim?", intro:"Paketler, fatura veya bağlantı sorunları hakkında bana yazın. Size doğru bilgiyi bulayım.", note:"Bilgi tabanına dayalı yanıtlar · Kaynaklarıyla birlikte", privacy:"DemoTel kurgusal bir operatördür. Kişisel bilgilerinizi paylaşmayın.", keyboard:"Enter ile gönder",
    placeholder:"DemoTel hakkında bir soru sorun…", input:"Destek sorunuz", send:"Mesajı gönder", loading:"Yanıt hazırlanıyor…", author:"DemoTel Asistan", you:"Siz: ", source:"Bilgi kaynağı",
    fallback:"DemoTel bilgi tabanında bu soruya güvenilir bir yanıt bulamadım. Paketler, fatura veya teknik destek hakkında daha belirgin bir soru sorabilirsiniz.", handoff:"Uzman desteği gerekli", more:"Ek bilgi gerekli", masked:"Kişisel bilgiler maskelendi",
    category:{internet_paketleri:"İnternet paketleri",fiyatlandirma:"Fiyatlandırma",fatura:"Fatura ve ödemeler",teknik_destek:"Teknik destek",taahhut:"Taahhüt",genel:"Genel bilgiler",billing:"Fatura ve ödemeler",technical:"Teknik destek",packages:"Paketler",general:"Genel bilgiler"},
    intent:{billing:"Fatura",technical:"Teknik destek",packages:"Paketler",general:"Genel destek"}, label:{topic:"Destek konusu",latency:"Yanıt süresi",cache:"Önbellek",privacy:"Gizlilik filtresi",source:"Kaynak kimliği",trace:"İşlem kimliği",steps:"İşlem adımları"},
    details:"Yanıt ayrıntıları",cached:"Önbellekten yanıtlandı",new:"Yeni yanıt",redacted:"Maskeleme uygulandı",noPattern:"Desteklenen veri örüntüsü bulunmadı",auth:"Servis erişim anahtarı gerektiriyor. Sağ üstteki bağlantı ayarlarından anahtarı girip yeniden deneyin.",
    errors:["Kısa sürede çok fazla istek gönderdiniz. Biraz bekleyip tekrar deneyin.","Mesajınızı kontrol edip tekrar gönderin. En fazla 2000 karakter kullanabilirsiniz.","Yanıt şu anda hazırlanamadı. Lütfen biraz sonra tekrar deneyin."], unavailable:"Servise ulaşılamadı veya yanıt süresi aşıldı. Bağlantınızı kontrol edip tekrar deneyin.",
    historyExpired:"Önceki sohbetin süresi dolmuş. Yeni bir sohbet başlatabilirsiniz.",historyError:"Sohbet geçmişi şu anda yüklenemiyor. Yeni bir soru sorabilir veya tekrar deneyebilirsiniz.",
    suggestions:["Ev internet paketleriniz nelerdir?","Faturamı nereden ödeyebilirim?","İnternetim yavaş, ne yapabilirim?","Kurulum ve aktivasyon ücreti var mı?"],
    followupTitle:"Buradan devam edebiliriz", anotherQuestion:"Başka bir soru sor", endChat:"Sohbeti bitir",
    followups:{
      greeting:["Ev internet paketleriniz nelerdir?","Faturamla ilgili yardım alabilir miyim?","İnternetim yavaş, ne yapabilirim?"],
      billing:["Fatura kalemlerimi nasıl inceleyebilirim?","Fatura tutarım neden değişmiş olabilir?","Fatura itirazı için nasıl ilerlerim?"],
      technical:["Modemi yeniden başlattım, sırada ne var?","Wi-Fi çekim alanını nasıl iyileştirebilirim?","Sorun devam ederse nasıl destek alırım?"],
      packages:["İhtiyacıma uygun internet hızını nasıl seçerim?","Taahhüt ve cayma koşulları neler?","Kurulum süreci nasıl ilerliyor?"],
      general:["Mobil paket seçenekleri nelerdir?","Fatura ödeme kanalları neler?","Teknik destek için nereden başlayabilirim?"]
    }
  },
  "en-US": {
    lang:"CHAT LANGUAGE", agent:"DemoTel Assistant", status:"Online · Here to help", close:"Close chat", fresh:"Start a new chat", eyebrow:"DEMOTEL ASSISTANT",
    welcome:"Hello! How can I help you today?", intro:"Ask me about plans, billing or connection issues. I’ll help you find the right information.", note:"Knowledge-based answers · Sources included", privacy:"DemoTel is a fictional operator. Please do not share personal information.", keyboard:"Press Enter to send",
    placeholder:"Ask a question about DemoTel…", input:"Your support question", send:"Send message", loading:"Preparing an answer…", author:"DemoTel Assistant", you:"You: ", source:"Knowledge source",
    fallback:"I could not find a reliable answer in the DemoTel knowledge base. Try a more specific question about plans, billing or technical support.", handoff:"Customer support may be needed", more:"More details needed", masked:"Personal information was masked",
    category:{internet_paketleri:"Internet plans",fiyatlandirma:"Pricing",fatura:"Billing and payments",teknik_destek:"Technical support",taahhut:"Commitments",genel:"General information",billing:"Billing and payments",technical:"Technical support",packages:"Plans",general:"General support"},
    intent:{billing:"Billing",technical:"Technical support",packages:"Plans",general:"General support"}, label:{topic:"Support topic",latency:"Response time",cache:"Cache",privacy:"Privacy filter",source:"Source ID",trace:"Trace ID",steps:"Workflow steps"},
    details:"Response details",cached:"Answered from cache",new:"Fresh answer",redacted:"Masking applied",noPattern:"No known sensitive pattern found",auth:"This service requires an access key. Enter it under connection settings above and try again.",
    errors:["You’ve sent too many requests. Please wait a moment and try again.","Please check your message and try again. Messages can be up to 2,000 characters.","I couldn’t prepare a response just now. Please try again shortly."], unavailable:"I couldn’t reach the service or the request timed out. Check your connection and try again.",
    historyExpired:"Your previous chat has expired. You can start a new conversation.",historyError:"Your chat history could not be loaded. Ask a new question or try again.",
    suggestions:["What home internet plans do you offer?","Where can I pay my bill?","My internet is slow. What can I try?","Is there an installation fee?"],
    followupTitle:"You can continue with", anotherQuestion:"Ask another question", endChat:"End chat",
    followups:{
      greeting:["What home internet plans do you offer?","Can you help me with my bill?","My internet is slow. What can I try?"],
      billing:["How can I review my bill items?","Why might my bill have changed?","How do I dispute a bill?"],
      technical:["I restarted my modem. What should I try next?","How can I improve Wi-Fi coverage?","How can I get help if this continues?"],
      packages:["How do I choose the right internet speed?","What are the commitment and cancellation terms?","How does installation work?"],
      general:["What mobile plans are available?","How can I pay my bill?","Where should I start with a technical issue?"]
    }
  }
};
let locale = (() => { try { return localStorage.getItem(LANGUAGE_KEY) === "en-US" ? "en-US" : "tr-TR"; } catch { return "tr-TR"; } })();
const t = () => UI[locale];
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
document.querySelector(".widget-controls").appendChild(settingsEl);
const newChatBtnVisible = document.getElementById("widget-new-chat");
const chatWidget = document.getElementById("chat-widget");
const chatBackdrop = document.getElementById("chat-backdrop");
const chatLauncher = document.getElementById("chat-launcher");
const chatClose = document.getElementById("chat-close");
const promptButtons = [...document.querySelectorAll("[data-prompt]")];
const chatPromptButtons = [...document.querySelectorAll(".widget-body [data-prompt]")];
const languageButtons = [...document.querySelectorAll(".language-option")];
const newChatWidgetButton = document.getElementById("widget-new-chat");
const AUTH_NOTICE = () => t().auth;
let activeSessionKey = SESSION_KEY + "." + locale;
let sessionId = readSession();
let apiToken = "";
let busy = false;
let statusBusy = false;
let turnCount = 0;
let chatWasOpened = false;

function localizedPrompt(prompt) {
  if (locale !== "en-US") return prompt;
  const known = {
    "İnternetim akşamları yavaşlıyor, nereden başlamalıyım?": "My internet is slow in the evening. Where should I start?",
    "Faturam beklediğimden yüksek, nasıl inceleyeyim?": "My bill is higher than expected. How should I review it?",
    "Numaramı taşımayı düşünüyorum, nelere dikkat etmeliyim?": "What should I know before transferring my number?",
    "Kişisel bilgilerimi sohbette paylaşmalı mıyım?": "Should I share personal information in this chat?"
  };
  return known[prompt] || prompt;
}

function openChat(prompt = "") {
  chatWidget.classList.add("is-open");
  chatWidget.setAttribute("aria-hidden", "false");
  chatWidget.inert = false;
  chatBackdrop.hidden = false;
  document.body.classList.add("chat-open");
  chatLauncher.setAttribute("aria-expanded", "true");
  chatWasOpened = true;
  if (prompt && !busy) {
    input.value = localizedPrompt(prompt);
    input.dispatchEvent(new Event("input"));
  }
  window.setTimeout(() => input.focus(), 160);
}

function closeChat() {
  chatWidget.classList.remove("is-open");
  chatWidget.setAttribute("aria-hidden", "true");
  chatWidget.inert = true;
  chatBackdrop.hidden = true;
  document.body.classList.remove("chat-open");
  chatLauncher.setAttribute("aria-expanded", "false");
  if (chatWasOpened) chatLauncher.focus();
}

document.querySelectorAll("[data-open-chat]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (button.tagName === "A") event.preventDefault();
    openChat(button.dataset.prompt || "");
  });
});
chatLauncher.addEventListener("click", () => openChat());
chatClose.addEventListener("click", closeChat);
chatBackdrop.addEventListener("click", closeChat);

function readSession() {
  try {
    const value = sessionStorage.getItem(activeSessionKey);
    return value && UUID_PATTERN.test(value) ? value : null;
  } catch {
    return null;
  }
}

function saveSession(value) {
  sessionId = typeof value === "string" && UUID_PATTERN.test(value) ? value : null;
  try {
    if (sessionId) sessionStorage.setItem(activeSessionKey, sessionId);
    else sessionStorage.removeItem(activeSessionKey);
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

function applyLocale() {
  const copy = t();
  document.documentElement.lang = locale === "en-US" ? "en" : "tr";
  chatWidget.setAttribute("aria-label", locale === "en-US" ? "DemoTel Assistant chat" : "DemoTel Asistan sohbeti");
  document.querySelector(".widget-body>.skip-link").textContent = locale === "en-US" ? "Skip to message field" : "Mesaj alanına geç";
  document.getElementById("chat-scroll").setAttribute("aria-label", locale === "en-US" ? "Conversation" : "Sohbet alanı");
  messagesEl.setAttribute("aria-label", locale === "en-US" ? "Chat messages" : "Sohbet mesajları");
  settingsEl.querySelector("summary").setAttribute("aria-label", locale === "en-US" ? "Connection settings" : "Bağlantı ve sohbet ayarları");
  settingsEl.querySelector("summary").title = locale === "en-US" ? "Connection settings" : "Bağlantı ve sohbet ayarları";
  document.getElementById("language-label").textContent = copy.lang;
  document.querySelector(".language-switch").setAttribute("aria-label", copy.lang);
  languageButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.locale === locale)));
  document.getElementById("agent-name").textContent = copy.agent;
  document.getElementById("agent-status").lastChild.textContent = " " + copy.status;
  chatClose.setAttribute("aria-label", copy.close);
  newChatBtnVisible.setAttribute("aria-label", copy.fresh);
  newChatBtnVisible.title = copy.fresh;
  document.getElementById("welcome-eyebrow").textContent = copy.eyebrow;
  document.getElementById("welcome-title").textContent = copy.welcome;
  document.getElementById("welcome-description").textContent = copy.intro;
  document.getElementById("welcome-note").textContent = copy.note;
  document.getElementById("privacy-note").textContent = copy.privacy;
  document.getElementById("keyboard-hint").textContent = copy.keyboard;
  input.placeholder = copy.placeholder;
  input.labels[0].textContent = copy.input;
  sendBtn.setAttribute("aria-label", copy.send);
  loadingEl.lastElementChild.textContent = copy.loading;
  chatPromptButtons.filter((button) => button.classList.contains("prompt-card")).forEach((button, index) => {
    button.dataset.prompt = copy.suggestions[index];
    const englishText = button.querySelectorAll("[data-en]");
    if (locale === "en-US") englishText.forEach((element) => { element.textContent = element.dataset.en; });
    else {
      const trStrong = ["Ev internet paketleri","Fatura ve ödeme","Bağlantı desteği","Kurulum ve aktivasyon"];
      const trDetail = ["Hangi seçenekler var?","Nereden ödeme yapabilirim?","İnternetim yavaşlıyor.","Kurulum ücreti var mı?"];
      englishText.forEach((element) => { element.textContent = element.tagName === "STRONG" ? trStrong[index] : trDetail[index]; });
    }
  });
  const settings = document.querySelector("#connection-form");
  if (locale === "en-US") {
    settings.querySelector("label").childNodes[0].textContent = "API access key ";
    settings.querySelector("label span").textContent = "Optional";
    tokenInput.placeholder = "For protected services";
    document.getElementById("token-hint").textContent = "The key is kept only while this page is open. Demo mode does not require one.";
    settings.querySelector("button").textContent = "Reconnect";
    mobileHistoryBtn.textContent = "Refresh chat history";
    mobileClearBtn.textContent = "Delete chat history";
  } else {
    settings.querySelector("label").childNodes[0].textContent = "API erişim anahtarı ";
    settings.querySelector("label span").textContent = "İsteğe bağlı";
    tokenInput.placeholder = "Korumalı servisler için";
    document.getElementById("token-hint").textContent = "Anahtar yalnızca bu sayfa açıkken tutulur. Varsayılan demo anahtar gerektirmez.";
    settings.querySelector("button").textContent = "Bağlantıyı yenile";
    mobileHistoryBtn.textContent = "Sohbet geçmişini yenile";
    mobileClearBtn.textContent = "Sohbet geçmişini sil";
  }
  document.getElementById("session-summary").textContent = turnCount ? (locale === "en-US" ? turnCount + " messages · This browser session" : turnCount + " mesaj · Bu tarayıcı oturumu") : (locale === "en-US" ? "A fresh start" : "Yeni bir başlangıç");
}

async function changeLocale(nextLocale) {
  if (busy || !["tr-TR", "en-US"].includes(nextLocale) || nextLocale === locale) return;
  locale = nextLocale;
  activeSessionKey = SESSION_KEY + "." + locale;
  try { localStorage.setItem(LANGUAGE_KEY, locale); } catch { /* Keep language in memory. */ }
  sessionId = readSession();
  messagesEl.replaceChildren();
  turnCount = 0;
  welcomeEl.classList.remove("hidden");
  showNotice();
  applyLocale();
  updateSessionSummary();
  await restoreConversation();
}

function scrollToLatest() {
  scrollEl.scrollTop = scrollEl.scrollHeight;
}

function updateSessionSummary() {
  document.getElementById("session-summary").textContent = turnCount ? (locale === "en-US" ? `${turnCount} messages · This browser session` : `${turnCount} mesaj · Bu tarayıcı oturumu`) : (locale === "en-US" ? "A fresh start" : "Yeni bir başlangıç");
  clearChatBtn.disabled = busy || !sessionId;
  mobileClearBtn.disabled = busy || !sessionId;
  historyBtn.disabled = busy;
  mobileHistoryBtn.disabled = busy || !sessionId;
}

function appendSource(content, source) {
  if (!source || typeof source.matched_question !== "string") return;
  const card = node("div", "source-card");
  const heading = node("div", "source-heading");
  heading.append(node("span", "source-number", "1"), node("span", "", `${t().source} · ${t().category[source.category] || (locale === "en-US" ? "DemoTel knowledge base" : "DemoTel bilgi tabanı")}`));
  card.append(heading, node("p", "source-question", source.matched_question));
  content.appendChild(card);
}

function appendResponseDetails(content, data) {
  const tags = node("div", "response-tags");
  if (data.handoff) tags.appendChild(node("span", "response-tag handoff", t().handoff));
  else if (data.fallback) tags.appendChild(node("span", "response-tag handoff", t().more));
  if (data.pii_redacted) tags.appendChild(node("span", "response-tag", t().masked));
  if (tags.childElementCount) content.appendChild(tags);

  const rows = [];
  if (t().intent[data.intent]) rows.push([t().label.topic, t().intent[data.intent]]);
  if (typeof data.latency_ms === "number" && Number.isFinite(data.latency_ms)) rows.push([t().label.latency, `${Math.round(data.latency_ms)} ms`]);
  if (typeof data.cache_hit === "boolean") rows.push([t().label.cache, data.cache_hit ? t().cached : t().new]);
  if (typeof data.pii_redacted === "boolean") rows.push([t().label.privacy, data.pii_redacted ? t().redacted : t().noPattern]);
  if (data.source && typeof data.source.entry_id === "string") rows.push([t().label.source, data.source.entry_id]);
  if (typeof data.trace_id === "string") rows.push([t().label.trace, data.trace_id]);
  if (Array.isArray(data.steps)) {
    const steps = data.steps.filter((step) => typeof step === "string").slice(0, 12);
    if (steps.length) rows.push([t().label.steps, steps.join(" → ")]);
  }
  if (!rows.length) return;
  const details = node("details", "response-details");
  const definition = node("dl");
  rows.forEach(([label, value]) => definition.append(node("dt", "", label), node("dd", "", value)));
  details.append(node("summary", "", t().details), definition);
  content.appendChild(details);
}

function appendFollowups(content, data = null) {
  if (!content) return;
  const intent = data?.handoff || data?.fallback ? "general" : data?.intent || "general";
  const questions = t().followups[intent] || t().followups.general;
  const panel = node("div", "followup-panel");
  panel.appendChild(node("p", "followup-title", t().followupTitle));
  const options = node("div", "followup-options");
  questions.forEach((question) => {
    const button = node("button", "followup-chip", question);
    button.type = "button";
    button.addEventListener("click", () => {
      if (busy) return;
      input.value = question;
      input.dispatchEvent(new Event("input"));
      form.requestSubmit();
    });
    options.appendChild(button);
  });
  panel.appendChild(options);
  const actions = node("div", "followup-actions");
  const another = node("button", "followup-action", t().anotherQuestion);
  another.type = "button";
  another.addEventListener("click", () => input.focus());
  const finish = node("button", "followup-action", t().endChat);
  finish.type = "button";
  finish.addEventListener("click", closeChat);
  actions.append(another, finish);
  panel.appendChild(actions);
  content.appendChild(panel);
}

function appendMessage(text, role, data = null, isError = false, includeFollowups = true) {
  if (role === "user") messagesEl.querySelectorAll(".followup-panel").forEach((panel) => panel.remove());
  welcomeEl.classList.add("hidden");
  const item = node("li", `message ${role}${isError ? " error" : ""}`);
  const content = node("div", "message-content");
  if (role === "assistant") {
    const avatar = node("span", "assistant-avatar", "D");
    avatar.setAttribute("aria-hidden", "true");
    item.appendChild(avatar);
    content.appendChild(node("span", "message-author", t().author));
  } else {
    content.appendChild(node("span", "sr-only", t().you));
  }
  const body = node("div", "message-text", text);
  content.appendChild(body);
  if (data && role === "assistant") {
    appendSource(content, data.source);
    appendResponseDetails(content, data);
  }
  if (includeFollowups && role === "assistant" && !isError) appendFollowups(content, data);
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
  newChatBtnVisible.disabled = value;
  tokenInput.disabled = value;
  connectionForm.querySelector("button").disabled = value;
  promptButtons.forEach((button) => { button.disabled = value; });
  languageButtons.forEach((button) => { button.disabled = value; });
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
      showNotice(t().historyExpired);
      return;
    }
    if (response.status === 401 || response.status === 403) {
      showNotice(AUTH_NOTICE());
      return;
    }
    if (!response.ok) throw new Error("session_unavailable");
    const data = await response.json();
    if (!Array.isArray(data.messages)) throw new Error("invalid_history");
    messagesEl.replaceChildren();
    turnCount = 0;
    welcomeEl.classList.remove("hidden");
    data.messages.forEach((message) => {
      if (["user", "assistant"].includes(message.role) && typeof message.content === "string") {
        appendMessage(message.content, message.role, null, false, false);
      }
    });
    const lastAssistant = [...messagesEl.children].reverse().find((message) => message.classList.contains("assistant"));
    if (lastAssistant) {
      appendFollowups(lastAssistant.querySelector(".message-content"));
      scrollToLatest();
    }
    updateSessionSummary();
    showNotice();
  } catch {
    showNotice(t().historyError);
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
      showNotice(AUTH_NOTICE());
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
    const payload = { message, locale };
    if (sessionId) payload.session_id = sessionId;
    const response = await request(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = response.status === 401 || response.status === 403
        ? AUTH_NOTICE()
        : response.status === 429
          ? t().errors[0]
          : response.status === 422
            ? t().errors[1]
            : t().errors[2];
      appendMessage(error, "assistant", null, true);
      return;
    }
    const data = await response.json();
    if (typeof data.answer !== "string") throw new Error("invalid_response");
    if (typeof data.safe_message === "string") userBody.textContent = data.safe_message;
    if (typeof data.session_id === "string" && UUID_PATTERN.test(data.session_id)) saveSession(data.session_id);
    appendMessage(data.answer, "assistant", data);
  } catch {
    appendMessage(t().unavailable, "assistant", null, true);
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
  input.value = localizedPrompt(button.dataset.prompt);
  input.dispatchEvent(new Event("input"));
  input.focus();
}));
newChatBtn.addEventListener("click", () => { if (!busy) resetConversation(); });
newChatBtnVisible.addEventListener("click", () => { if (!busy) resetConversation(); });
languageButtons.forEach((button) => button.addEventListener("click", () => changeLocale(button.dataset.locale)));
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
      showNotice(AUTH_NOTICE());
      return;
    }
    if (!response.ok && response.status !== 404) throw new Error("delete_failed");
    resetConversation();
      showNotice(locale === "en-US" ? "This chat history was deleted from the server." : "Bu sohbetin sunucudaki geçmişi silindi.");
    settingsEl.open = false;
  } catch {
    showNotice(locale === "en-US" ? "The chat history could not be deleted. Please try again." : "Sohbet geçmişi silinemedi. Lütfen tekrar deneyin.");
  } finally {
    setBusy(false, false);
    input.focus();
  }
}
clearChatBtn.addEventListener("click", clearConversation);
mobileClearBtn.addEventListener("click", clearConversation);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !chatWidget.inert) {
    closeChat();
    return;
  }
  if (event.key === "Escape" && settingsEl.open) {
    settingsEl.open = false;
    settingsEl.querySelector("summary").focus();
  }
});
document.addEventListener("click", (event) => {
  if (event.target.closest("[data-prompt]") && !event.target.closest(".prompt-card, .topic-button")) {
    const button = event.target.closest("[data-prompt]");
    if (button && button.hasAttribute("data-open-chat")) openChat(button.dataset.prompt || "");
  }
  if (settingsEl.open && !settingsEl.contains(event.target) && !statusBtn.contains(event.target)) settingsEl.open = false;
});

updateSessionSummary();
applyLocale();
updateServiceStatus();
restoreConversation();
