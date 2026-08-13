"use strict";

const $ = (id) => document.getElementById(id);
const won = (n) => Math.round(n).toLocaleString("ko-KR") + "원";

const GEN_LABELS = {
  gen1: "1세대", gen2_1: "2-1세대", gen2_2: "2-2세대", gen3: "3세대", gen4: "4세대",
};

function toggleHospitalType() {
  const isOutpatient = $("careType").value === "통원";
  $("hospitalTypeWrap").style.display = isOutpatient ? "" : "none";
}
$("careType").addEventListener("change", toggleHospitalType);
toggleHospitalType();

$("calcForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("submitBtn");
  btn.disabled = true;
  $("status").textContent = "계산 중입니다…";
  $("results").hidden = true;

  const body = {
    care_type: $("careType").value,
    hospital_type: $("hospitalType").value,
    paid_copay: Number($("paidCopay").value) || 0,
    nonpaid: Number($("nonpaid").value) || 0,
    rider_dosu: Number($("riderDosu").value) || 0,
    rider_injection: Number($("riderInjection").value) || 0,
    rider_mri: Number($("riderMri").value) || 0,
  };

  try {
    const res = await fetch("/api/calc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "계산 실패");
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
  const box = $("resultCards");
  box.innerHTML = "";

  data.results.forEach((r) => {
    const isBest = r.generation === data.best_generation;
    const card = document.createElement("article");
    card.className = "card" + (isBest ? " best" : "");

    const riderLines = Object.entries(r.rider_detail || {})
      .map(([name, d]) => `<li>${name}: ${won(d.pay)} (공제 ${won(d.deduct)})</li>`)
      .join("");

    card.innerHTML = `
      ${isBest ? '<div class="badge">최고 수령액</div>' : ""}
      <h3>${r.label} <span class="period">${r.period}</span></h3>
      <p class="payout">${won(r.expected_payout)}</p>
      <dl>
        <dt>청구 대상액</dt><dd>${won(r.claim_total)}</dd>
        <dt>급여 지급</dt><dd>${won(r.paid_pay)}</dd>
        <dt>비급여 지급</dt><dd>${won(r.nonpaid_pay)}</dd>
        ${r.rider_pay ? `<dt>특약 지급</dt><dd>${won(r.rider_pay)}</dd>` : ""}
        <dt>자기부담·공제 합계</dt><dd>${won(r.deduct_total)}</dd>
      </dl>
      ${riderLines ? `<ul class="riders">${riderLines}</ul>` : ""}
      ${r.outpatient_capped ? '<p class="note">※ 통원 1회 지급한도(20만원) 적용됨</p>' : ""}
    `;
    box.appendChild(card);
  });
}
