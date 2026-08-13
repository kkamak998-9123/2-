// 비상장주식 평가 계산기 - 드래그앤드롭 순손익액 분류 + 계산 호출

const ZONE_META = {
  A: { title: 'A. 당기순손익', hint: '결산서상 당기순이익(손실)' },
  B: { title: 'B. 가산항목', hint: '익금산입 · 손금불산입 (세무조정 가산)' },
  C: { title: 'C. 차감항목', hint: '손금산입 · 익금불산입 (세무조정 차감)' },
};

let itemSeq = 1;

const state = {
  activeYear: 0,
  years: [
    { label: '1년전 (가중치 3)', weight: 3, items: [] },
    { label: '2년전 (가중치 2)', weight: 2, items: [] },
    { label: '3년전 (가중치 1)', weight: 1, items: [] },
  ],
};

const $ = (sel) => document.querySelector(sel);
const won = (n) => (Math.round(n * 100) / 100).toLocaleString('ko-KR');

function sumZone(items, zone) {
  return items.filter((it) => it.zone === zone).reduce((s, it) => s + it.amount, 0);
}

// ---------- 년도 탭 ----------
function renderYearTabs() {
  const bar = $('#yearTabs');
  bar.innerHTML = '';
  state.years.forEach((y, idx) => {
    const btn = document.createElement('button');
    btn.textContent = y.label;
    if (idx === state.activeYear) btn.classList.add('active');
    btn.addEventListener('click', () => {
      state.activeYear = idx;
      renderYearTabs();
      renderYearPanel();
    });
    bar.appendChild(btn);
  });
}

// ---------- 항목 추가 폼 + 드래그존 ----------
function makeChip(item, year) {
  const chip = document.createElement('div');
  chip.className = 'chip';
  chip.draggable = true;
  chip.dataset.id = item.id;
  chip.innerHTML = `<span class="chip-name">${item.name}</span><span class="chip-amount">${won(item.amount)}</span>`;

  const del = document.createElement('button');
  del.type = 'button';
  del.className = 'chip-remove';
  del.textContent = '×';
  del.addEventListener('click', (e) => {
    e.stopPropagation();
    const yr = state.years[year];
    yr.items = yr.items.filter((it) => it.id !== item.id);
    renderYearPanel();
  });
  chip.appendChild(del);

  chip.addEventListener('dragstart', (e) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ year, id: item.id }));
    e.dataTransfer.effectAllowed = 'move';
  });

  return chip;
}

function makeDropzone(zoneKey, year, items) {
  const el = document.createElement('div');
  el.className = 'dropzone';
  el.dataset.zone = zoneKey;

  const meta = ZONE_META[zoneKey];
  const head = document.createElement('div');
  head.className = 'dz-head';
  const zoneItems = items.filter((it) => it.zone === zoneKey);
  const total = sumZone(items, zoneKey);
  head.innerHTML = `<div><b>${meta.title}</b><div class="dz-hint">${meta.hint}</div></div><div class="dz-sum">${won(total)}</div>`;
  el.appendChild(head);

  const body = document.createElement('div');
  body.className = 'dz-body';
  if (zoneItems.length === 0) {
    const ph = document.createElement('div');
    ph.className = 'dz-placeholder';
    ph.textContent = '여기로 항목을 드래그하세요';
    body.appendChild(ph);
  } else {
    zoneItems.forEach((it) => body.appendChild(makeChip(it, year)));
  }
  el.appendChild(body);

  el.addEventListener('dragover', (e) => {
    e.preventDefault();
    el.classList.add('drag-over');
  });
  el.addEventListener('dragleave', () => el.classList.remove('drag-over'));
  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('drag-over');
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    const yr = state.years[data.year];
    const item = yr.items.find((it) => it.id === data.id);
    if (item) item.zone = zoneKey;
    renderYearPanel();
  });

  return el;
}

function makePalette(year, items) {
  const el = document.createElement('div');
  el.className = 'palette dropzone';
  el.dataset.zone = 'palette';

  const head = document.createElement('div');
  head.className = 'dz-head';
  head.innerHTML = `<div><b>미분류 항목</b><div class="dz-hint">새 항목을 만들고 A·B·C 영역으로 드래그하세요</div></div>`;
  el.appendChild(head);

  const form = document.createElement('div');
  form.className = 'add-item-form';
  form.innerHTML = `
    <input type="text" class="item-name" placeholder="항목명 (예: 당기순이익, 벌금과료)" />
    <input type="number" class="item-amount" placeholder="금액" step="1" />
    <button type="button" class="add-item-btn">+ 추가</button>
  `;
  const nameInput = form.querySelector('.item-name');
  const amountInput = form.querySelector('.item-amount');
  const addBtn = form.querySelector('.add-item-btn');
  const addItem = () => {
    const name = nameInput.value.trim();
    const amount = Number(amountInput.value);
    if (!name || Number.isNaN(amount) || amount === 0) return;
    state.years[year].items.push({ id: itemSeq++, name, amount, zone: 'palette' });
    nameInput.value = '';
    amountInput.value = '';
    renderYearPanel();
    $(`#yearPanels .add-item-form .item-name`)?.focus();
  };
  addBtn.addEventListener('click', addItem);
  amountInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') addItem(); });
  el.appendChild(form);

  const body = document.createElement('div');
  body.className = 'dz-body palette-body';
  const paletteItems = items.filter((it) => it.zone === 'palette');
  if (paletteItems.length === 0) {
    const ph = document.createElement('div');
    ph.className = 'dz-placeholder';
    ph.textContent = '추가된 항목이 없습니다';
    body.appendChild(ph);
  } else {
    paletteItems.forEach((it) => body.appendChild(makeChip(it, year)));
  }
  el.appendChild(body);

  el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('drag-over'); });
  el.addEventListener('dragleave', () => el.classList.remove('drag-over'));
  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('drag-over');
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    const yr = state.years[data.year];
    const item = yr.items.find((it) => it.id === data.id);
    if (item) item.zone = 'palette';
    renderYearPanel();
  });

  return el;
}

function renderYearPanel() {
  const root = $('#yearPanels');
  root.innerHTML = '';
  const year = state.activeYear;
  const yr = state.years[year];

  root.appendChild(makePalette(year, yr.items));

  const zonesWrap = document.createElement('div');
  zonesWrap.className = 'zones-grid';
  ['A', 'B', 'C'].forEach((z) => zonesWrap.appendChild(makeDropzone(z, year, yr.items)));
  root.appendChild(zonesWrap);

  const a = sumZone(yr.items, 'A');
  const b = sumZone(yr.items, 'B');
  const c = sumZone(yr.items, 'C');
  const net = a + b - c;

  const summary = document.createElement('div');
  summary.className = 'year-summary';
  summary.innerHTML = `<b>${yr.label} 순손익액</b> = A(${won(a)}) + B(${won(b)}) − C(${won(c)}) = <span class="net-value">${won(net)} 원</span>`;
  root.appendChild(summary);
}

// ---------- 재무자료 불러오기 ----------
function applyParsedFinancials(data) {
  $('#totalAssets').value = data.net_asset.total_assets;
  $('#totalLiabilities').value = data.net_asset.total_liabilities;

  data.years.forEach((y, idx) => {
    if (idx >= state.years.length) return;
    const items = [];
    items.push({ id: itemSeq++, name: '당기순이익', amount: y.net_income, zone: 'A' });
    y.additions.forEach((it) => items.push({ id: itemSeq++, name: it.name, amount: it.amount, zone: 'B' }));
    y.subtractions.forEach((it) => items.push({ id: itemSeq++, name: it.name, amount: it.amount, zone: 'C' }));
    state.years[idx].items = items;
    state.years[idx].label = `${y.label} · ${y.year}년`;
  });

  state.activeYear = 0;
  renderYearTabs();
  renderYearPanel();
}

async function uploadFinancials() {
  const balanceSheet = $('#fileBalanceSheet').files[0];
  const incomeStatements = $('#fileIncomeStatements').files[0];
  const adjustments = $('#fileAdjustments').files[0];
  const status = $('#uploadStatus');
  const btn = $('#uploadBtn');

  if (!balanceSheet || !incomeStatements || !adjustments) {
    status.className = 'upload-status bad';
    status.textContent = '재무상태표, 손익계산서, 조정합계표 3개 파일을 모두 선택해주세요.';
    return;
  }

  const formData = new FormData();
  formData.append('balance_sheet', balanceSheet);
  formData.append('income_statements', incomeStatements);
  formData.append('adjustments', adjustments);

  btn.disabled = true;
  status.className = 'upload-status';
  status.textContent = '불러오는 중...';

  try {
    const res = await fetch('/api/parse-financials', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '파일을 처리하는 중 오류가 발생했습니다.');
    }
    const data = await res.json();
    applyParsedFinancials(data);
    status.className = 'upload-status ok';
    status.textContent = '불러오기 완료: 순자산가치와 연도별 항목이 자동으로 채워졌습니다. 필요하면 드래그로 재분류하세요.';
  } catch (e) {
    status.className = 'upload-status bad';
    status.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

// ---------- 특수법인 유형 로드 ----------
async function loadSpecialCorpTypes() {
  const sel = $('#specialCorpType');
  try {
    const res = await fetch('/api/special-corp-types');
    const items = await res.json();
    sel.innerHTML = items.map((it) => `<option value="${it.id}">${it.label}</option>`).join('');
  } catch (e) {
    sel.innerHTML = '<option value="normal">일반법인 (순손익가치:순자산가치 = 3:2)</option>';
  }
}

// ---------- 계산 ----------
async function calculate() {
  const payload = {
    shares_outstanding: Number($('#sharesOutstanding').value),
    capitalization_rate: Number($('#capitalizationRate').value),
    years: state.years.map((y) => ({
      label: y.label,
      net_income: sumZone(y.items, 'A'),
      additions: y.items.filter((it) => it.zone === 'B').map((it) => ({ name: it.name, amount: it.amount })),
      subtractions: y.items.filter((it) => it.zone === 'C').map((it) => ({ name: it.name, amount: it.amount })),
    })),
    net_asset: {
      total_assets: Number($('#totalAssets').value),
      total_liabilities: Number($('#totalLiabilities').value),
      goodwill: Number($('#goodwill').value),
    },
    special_corp_type: $('#specialCorpType').value,
    major_shareholder: {
      is_major_shareholder: $('#isMajorShareholder').checked,
      is_exempt: $('#isExempt').checked,
      premium_rate: Number($('#premiumRate').value),
    },
  };

  const resultBody = $('#resultBody');
  resultBody.innerHTML = '<div class="empty-hint">계산 중...</div>';

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '계산 중 오류가 발생했습니다.');
    }
    const result = await res.json();
    renderResult(result, payload);
  } catch (e) {
    resultBody.innerHTML = `<div class="empty-hint bad">${e.message}</div>`;
  }
}

function renderResult(result, payload) {
  const { profit, net_asset, weighted, premium, special_corp_label } = result;

  const yearRows = payload.years
    .map((y, i) => {
      const adjusted = profit.adjusted_net_incomes[i];
      return `<div class="metric-row"><span class="m-label">${y.label}</span><span class="m-value">${won(adjusted)} 원</span></div>`;
    })
    .join('');

  const ratioText = weighted.ratio[0] === 0 ? '순자산가치 100%' : `${weighted.ratio[0]} : ${weighted.ratio[1]}`;

  $('#resultBody').innerHTML = `
    <div class="kpis result-kpis">
      <div class="kpi">
        <div class="kpi-label">1주당 순손익가치</div>
        <div class="kpi-value">${won(profit.profit_value_per_share)}<span class="unit">원</span></div>
      </div>
      <div class="kpi">
        <div class="kpi-label">1주당 순자산가치</div>
        <div class="kpi-value">${won(net_asset.net_asset_value_per_share)}<span class="unit">원</span></div>
      </div>
      <div class="kpi">
        <div class="kpi-label">가중평균 (${special_corp_label.split(' ')[0]})</div>
        <div class="kpi-value">${won(weighted.weighted_value)}<span class="unit">원</span></div>
      </div>
      <div class="kpi kpi-final">
        <div class="kpi-label">최종 1주당 평가액</div>
        <div class="kpi-value">${won(premium.final_value_per_share)}<span class="unit">원</span></div>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-row"><span class="m-label">법인 유형</span><span class="m-value">${special_corp_label}</span></div>
      <div class="metric-row"><span class="m-label">가중평균 비율 (순손익:순자산)</span><span class="m-value">${ratioText}</span></div>
      <div class="metric-row"><span class="m-label">순자산가치 80% 하한</span><span class="m-value">${won(weighted.floor_value)} 원 ${weighted.floor_applied ? '<span class="badge warn">하한 적용</span>' : ''}</span></div>
      <div class="metric-row"><span class="m-label">최대주주 할증</span><span class="m-value">${premium.premium_applied ? `+${premium.premium_rate}% 적용` : '미적용'}</span></div>
    </div>

    <div class="panel-title sub-title">연도별 순손익액 (세무조정 반영)</div>
    <div class="metric-grid">${yearRows}</div>
    <div class="metric-row total-row"><span class="m-label">최근 3년 가중평균 순손익액 (총액)</span><span class="m-value">${won(profit.weighted_total_net_income)} 원</span></div>
  `;
}

// ---------- 초기화 ----------
document.addEventListener('DOMContentLoaded', () => {
  renderYearTabs();
  renderYearPanel();
  loadSpecialCorpTypes();
  $('#calcBtn').addEventListener('click', calculate);
  $('#uploadBtn').addEventListener('click', uploadFinancials);
});
