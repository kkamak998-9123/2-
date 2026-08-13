"use strict";

const $ = (id) => document.getElementById(id);

let SGG_MAP = {};

async function loadOptions() {
  const res = await fetch("/api/options");
  if (!res.ok) throw new Error("옵션 로드 실패");
  const data = await res.json();
  SGG_MAP = data.sggMap || {};

  const ctpv = $("ctpv");
  data.ctpvs.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    ctpv.appendChild(opt);
  });

  renderChips("themes", data.themes);
  renderChips("households", data.households);
}

function renderChips(containerId, items) {
  const box = $(containerId);
  items.forEach((name) => {
    const label = document.createElement("label");
    label.className = "chip";
    label.innerHTML =
      `<input type="checkbox" value="${name}" /><span>${name}</span>`;
    box.appendChild(label);
  });
}

function selectedChips(containerId) {
  return [...$(containerId).querySelectorAll("input:checked")].map((c) => c.value);
}

$("ctpv").addEventListener("change", (e) => {
  const sgg = $("sgg");
  sgg.innerHTML = '<option value="">(전체)</option>';
  (SGG_MAP[e.target.value] || []).forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sgg.appendChild(opt);
  });
});

$("searchForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("submitBtn");
  btn.disabled = true;
  $("status").textContent = "조회 중입니다…";
  $("results").hidden = true;

  const params = new URLSearchParams();
  const age = $("age").value.trim();
  if (age) params.set("age", age);
  if ($("ctpv").value) params.set("ctpv", $("ctpv").value);
  if ($("sgg").value) params.set("sgg", $("sgg").value);
  const kw = $("keyword").value.trim();
  if (kw) params.set("keyword", kw);
  const themes = selectedChips("themes");
  if (themes.length) params.set("themes", themes.join(","));
  const households = selectedChips("households");
  if (households.length) params.set("households", households.join(","));

  try {
    const res = await fetch("/api/search?" + params.toString());
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "조회 실패");
    }
    const data = await res.json();
    renderResults(data);
    $("status").textContent = "";
  } catch (err) {
    $("status").textContent = "오류: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

function renderResults(data) {
  $("results").hidden = false;

  const cap = (n) => (n >= data.limit ? `${data.limit}건 이상` : `${n}건`);

  $("nCount").textContent = cap(data.national.length);
  renderCards("nationalList", data.national, "전국 공통 조건에 맞는 혜택이 없습니다.");

  const localGroup = $("localGroup");
  if ($("ctpv").value) {
    localGroup.hidden = false;
    const region = `${$("ctpv").value} ${$("sgg").value}`.trim();
    $("localTitle").textContent = `지역 (${region})`;
    $("lCount").textContent = cap(data.local.length);
    renderCards("localList", data.local, "해당 지역 조건에 맞는 혜택이 없습니다.");
  } else {
    localGroup.hidden = true;
  }
}

function renderCards(containerId, items, emptyMsg) {
  const box = $(containerId);
  box.innerHTML = "";
  if (!items.length) {
    box.innerHTML = `<p class="empty">${emptyMsg}</p>`;
    return;
  }
  items.forEach((it) => {
    const card = document.createElement("article");
    card.className = "card";
    const tags = [it.life, it.thema, it.trgter]
      .filter(Boolean)
      .join(", ");
    card.innerHTML = `
      <h3>${escapeHtml(it.servNm)}</h3>
      ${it.jur ? `<p class="jur">${escapeHtml(it.jur)}</p>` : ""}
      ${it.region ? `<p class="region">📍 ${escapeHtml(it.region)}</p>` : ""}
      <p class="dgst">${escapeHtml(it.servDgst || "")}</p>
      ${tags ? `<p class="tags">${escapeHtml(tags)}</p>` : ""}
      <div class="card-actions">
        <button class="detail-btn" data-id="${it.servId}">상세 보기</button>
        ${it.online ? '<span class="badge">온라인 신청 가능</span>' : ""}
        ${it.servDtlLink ? `<a href="${it.servDtlLink}" target="_blank" rel="noopener">복지로 링크 ↗</a>` : ""}
      </div>`;
    card.querySelector(".detail-btn").addEventListener("click", () =>
      openDetail(it.servId)
    );
    box.appendChild(card);
  });
}

async function openDetail(servId) {
  const modal = $("modal");
  const body = $("modalBody");
  body.innerHTML = '<p class="loading">상세 정보를 불러오는 중…</p>';
  modal.hidden = false;

  try {
    const res = await fetch("/api/detail/" + encodeURIComponent(servId));
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "상세 조회 실패");
    }
    const d = await res.json();
    body.innerHTML = renderDetail(d);
  } catch (err) {
    body.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function renderDetail(d) {
  const section = (title, text) =>
    text ? `<h4>${title}</h4><p>${escapeHtml(text).replace(/\n/g, "<br>")}</p>` : "";
  const apply = (d.applyMethod || []).filter(Boolean);
  return `
    <h3>${escapeHtml(d.servNm || "")}</h3>
    ${d.jur ? `<p class="jur">${escapeHtml(d.jur)}</p>` : ""}
    ${section("서비스 요약", d.outline)}
    ${section("지원대상", d.target)}
    ${section("선정기준", d.criteria)}
    ${section("지원내용", d.benefit)}
    ${d.cycle ? `<p class="meta">지원주기: ${escapeHtml(d.cycle)}</p>` : ""}
    ${d.provision ? `<p class="meta">제공유형: ${escapeHtml(d.provision)}</p>` : ""}
    ${apply.length ? `<h4>신청방법</h4><p>${apply.map(escapeHtml).join("<br>")}</p>` : ""}
  `;
}

$("modalClose").addEventListener("click", () => ($("modal").hidden = true));
$("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") $("modal").hidden = true;
});

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

loadOptions().catch((err) => {
  $("status").textContent = "초기화 오류: " + err.message;
});
