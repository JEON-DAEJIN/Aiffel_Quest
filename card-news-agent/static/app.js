const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "card_news_run_id";

let currentRunId = null;
let currentTopic = null; // { selection_range, ... } for the running run's topic
let pollTimer = null;

async function loadTopics() {
  const topics = await fetch("/topics").then((r) => r.json());
  const select = $("topic-select");
  select.innerHTML = "";
  for (const t of topics) {
    const opt = document.createElement("option");
    opt.value = t.topic_id;
    opt.textContent = t.display_name;
    opt.dataset.selectionRange = JSON.stringify(t.selection_range);
    opt.dataset.inputMode = t.input_mode;
    opt.dataset.ctaCard = t.cta_card ? "1" : "";
    select.appendChild(opt);
  }
  return topics;
}

function updateSourceTextVisibility() {
  const select = $("topic-select");
  const opt = select.options[select.selectedIndex];
  $("source-text-box").hidden = !opt || opt.dataset.inputMode !== "source_text";
  $("source-url-box").hidden = !opt || !opt.dataset.ctaCard;
}

function showSection(name) {
  const views = [
    "researching-view",
    "selection-view",
    "verifying-view",
    "storyboard-view",
    "generating-images-view",
    "review-view",
    "completed-view",
    "failed-view",
  ];
  for (const v of views) $(v).hidden = v !== name;
}

function setBadge(status) {
  const el = $("status-badge");
  el.textContent = status;
  el.className = "status-badge status-" + status;
}

function renderCandidates(run, topics) {
  const topic = topics.find((t) => t.topic_id === run.topic_id);
  currentTopic = topic;
  const [lo, hi] = topic ? topic.selection_range : [1, 3];
  $("selection-range-text").textContent = lo === hi ? `${lo}` : `${lo}~${hi}`;

  const container = $("candidates-list");
  container.innerHTML = "";
  const candidates = (run.candidates && run.candidates.candidates) || [];
  for (const c of candidates) {
    const div = document.createElement("div");
    div.className = "candidate";
    const sourceLine = c.source_url
      ? `<div class="meta">${escapeHtml(c.date)} · <a href="${c.source_url}" target="_blank">출처</a></div>`
      : "";
    div.innerHTML = `
      <label>
        <input type="checkbox" value="${c.candidate_id}">
        <span>
          <strong>${escapeHtml(c.title)}</strong>
          ${sourceLine}
          <div>${escapeHtml(c.summary)}</div>
          <div class="meta">선정 이유: ${escapeHtml(c.why_worth_choosing)}</div>
        </span>
      </label>`;
    container.appendChild(div);
  }
}

function renderStoryboard(run) {
  const container = $("storyboard-list");
  container.innerHTML = "";
  const data = run.verification || {};
  const cards = data.storyboard || [];
  const verifications = data.verifications || [];

  const unverified = verifications.filter((v) => !v.confirmed_facts || v.confirmed_facts.length === 0);
  if (unverified.length) {
    const warn = document.createElement("div");
    warn.className = "error-box";
    warn.style.marginBottom = "12px";
    warn.textContent =
      "검증되지 않은 후보가 있어 스토리보드에서 제외됐을 수 있습니다: " +
      unverified.map((v) => v.candidate_id).join(", ");
    container.appendChild(warn);
  }

  for (const card of cards) {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <strong>${card.card_number}. ${escapeHtml(card.headline)}</strong>
      <p>${escapeHtml(card.body)}</p>
      <p class="meta">이미지: ${escapeHtml(card.image_role)} · 출처: ${escapeHtml(card.source)}</p>`;
    container.appendChild(div);
  }

  if (data.caption || (data.hashtags && data.hashtags.length)) {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <strong>인스타그램 캡션</strong>
      <p>${escapeHtml(data.caption || "")}</p>
      <p class="meta">${(data.hashtags || []).map((h) => "#" + h.replace(/^#/, "")).join(" ")}</p>`;
    container.appendChild(div);
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

function renderReview(run) {
  const container = $("review-cards");
  container.innerHTML = "";
  const images = run.images || [];
  for (const img of images) {
    const div = document.createElement("div");
    div.className = "card review-card";
    if (img.status === "ok") {
      div.innerHTML = `
        <img src="/media/${run.id}/${img.final_path.split(/[\\/]/).pop()}" alt="card ${img.card_number}">
        <div class="review-meta">
          <strong>${img.card_number}. ${escapeHtml(img.headline)}</strong>
          <p>${escapeHtml(img.body)}</p>
          <p class="status-ok">생성 완료</p>
          <button class="secondary regen-btn" data-card="${img.card_number}">이 카드 재생성</button>
        </div>`;
    } else {
      div.innerHTML = `
        <div class="review-meta">
          <strong>${img.card_number}. ${escapeHtml(img.headline)}</strong>
          <p class="status-failed">생성 실패: ${escapeHtml(img.error || "알 수 없는 오류")}</p>
          <button class="regen-btn" data-card="${img.card_number}">재생성</button>
        </div>`;
    }
    container.appendChild(div);
  }
  container.querySelectorAll(".regen-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cardNumber = parseInt(btn.dataset.card, 10);
      await fetch(`/runs/${currentRunId}/regenerate_card`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_number: cardNumber }),
      });
      poll();
    });
  });
}

async function renderRun(run, topics) {
  $("run-section").hidden = false;
  $("start-section").hidden = true;
  $("run-id-line").textContent = `run: ${run.id}`;
  setBadge(run.status);

  if (run.status === "running" && run.stage === "research") {
    showSection("researching-view");
  } else if (run.status === "waiting_for_user" && run.stage === "await_selection") {
    showSection("selection-view");
    renderCandidates(run, topics);
  } else if (run.status === "running" && run.stage === "verify_storyboard") {
    showSection("verifying-view");
  } else if (run.status === "waiting_for_user" && run.stage === "await_approval") {
    showSection("storyboard-view");
    renderStoryboard(run);
    $("revise-box").hidden = true;
  } else if (run.status === "running" && run.stage === "generate_images") {
    showSection("generating-images-view");
  } else if (run.status === "running" && run.stage === "await_review") {
    // 개별 카드 재생성 중 — 검수 화면을 그대로 두고 폴링만 이어간다.
    showSection("review-view");
    renderReview(run);
  } else if (run.status === "waiting_for_user" && run.stage === "await_review") {
    showSection("review-view");
    renderReview(run);
  } else if (run.status === "completed") {
    showSection("completed-view");
    $("download-link").href = `/runs/${run.id}/download`;
  } else if (run.status === "failed") {
    showSection("failed-view");
    $("error-text").textContent = run.error_message || "알 수 없는 오류";
  }
}

async function poll() {
  if (!currentRunId) return;
  const run = await fetch(`/runs/${currentRunId}`).then((r) => (r.ok ? r.json() : null));
  if (!run) return;
  const topics = await loadTopics();
  await renderRun(run, topics);
  if (run.status === "running") {
    pollTimer = setTimeout(poll, 2000);
  }
}

function startPolling(runId) {
  currentRunId = runId;
  localStorage.setItem(STORAGE_KEY, runId);
  if (pollTimer) clearTimeout(pollTimer);
  poll();
}

async function init() {
  const topics = await loadTopics();
  updateSourceTextVisibility();
  $("topic-select").addEventListener("change", updateSourceTextVisibility);
  const savedRunId = localStorage.getItem(STORAGE_KEY);
  if (savedRunId) {
    startPolling(savedRunId);
  }

  $("start-btn").addEventListener("click", async () => {
    const topicId = $("topic-select").value;
    const sourceText = $("source-text-input").value.trim();
    const sourceUrl = $("source-url-input").value.trim();
    const res = await fetch("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_id: topicId, source_text: sourceText || null, source_url: sourceUrl || null }),
    });
    if (!res.ok) {
      alert((await res.json()).detail || "시작 실패");
      return;
    }
    const data = await res.json();
    startPolling(data.run_id);
  });

  $("submit-selection-btn").addEventListener("click", async () => {
    const ids = Array.from(document.querySelectorAll("#candidates-list input:checked")).map((el) => el.value);
    const res = await fetch(`/runs/${currentRunId}/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_ids: ids }),
    });
    if (!res.ok) {
      alert((await res.json()).detail || "선택 제출 실패");
      return;
    }
    poll();
  });

  $("approve-btn").addEventListener("click", async () => {
    await fetch(`/runs/${currentRunId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve" }),
    });
    poll();
  });

  $("revise-btn").addEventListener("click", () => {
    $("revise-box").hidden = false;
  });

  $("submit-revision-btn").addEventListener("click", async () => {
    const notes = $("revise-notes").value.trim();
    await fetch(`/runs/${currentRunId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "revise", notes }),
    });
    poll();
  });

  $("retry-btn").addEventListener("click", async () => {
    await fetch(`/runs/${currentRunId}/retry`, { method: "POST" });
    poll();
  });

  $("finish-btn").addEventListener("click", async () => {
    await fetch(`/runs/${currentRunId}/finish`, { method: "POST" });
    poll();
  });
}

init();
