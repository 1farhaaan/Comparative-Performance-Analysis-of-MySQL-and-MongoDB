'use strict';
// charts.js — NexusDesk Admin Charts (teal/amber palette)

const C = {
  teal:    '#14b8a6', teal2:  '#0d9488',
  amber:   '#f59e0b', amber2: '#d97706',
  success: '#10b981', sky:    '#38bdf8',
  violet:  '#7c3aed', rose:   '#f43f5e',
  muted:   '#475569', grid:   'rgba(148,163,184,0.08)',
  text:    '#94a3b8',
};

function readData(id, attr) {
  const el = document.getElementById(id);
  if (!el) return null;
  try { return JSON.parse(el.dataset[attr] || 'null'); } catch { return null; }
}

const BASE_OPTS = {
  responsive: true, maintainAspectRatio: true,
  plugins: { legend: { display: false }, tooltip: { backgroundColor:'#111624', titleColor:'#e2e8f0', bodyColor:'#94a3b8', borderColor:'#1e2a40', borderWidth:1, padding:10 } },
  scales: {
    x: { grid: { color: C.grid }, ticks: { color: C.text, font: { family: 'Fira Code', size: 11 } } },
    y: { grid: { color: C.grid }, ticks: { color: C.text, font: { family: 'Fira Code', size: 11 } } },
  }
};

// ── 1. Resolution Ring ─────────────────────────────────────────
function initRingChart() {
  const el = document.getElementById('ringChart');
  if (!el || !window.Chart) return;
  new Chart(el, {
    type: 'doughnut',
    data: {
      labels: ['Resolved', 'Open', 'In Progress'],
      datasets: [{ data: [+el.dataset.resolved||0, +el.dataset.open||0, +el.dataset.inprogress||0],
        backgroundColor: [C.success, C.amber, C.teal],
        borderWidth: 0, hoverOffset: 4 }]
    },
    options: {
      responsive: true, cutout: '72%',
      plugins: { legend: { display: false }, tooltip: { ...BASE_OPTS.plugins.tooltip } }
    }
  });
}

// ── 2. Priority Horizontal Bar ─────────────────────────────────
function initPriorityChart() {
  const el = document.getElementById('priorityChart');
  if (!el || !window.Chart) return;
  const labels = readData('priorityChart','labels') || ['Low','Medium','High','Critical'];
  const values = readData('priorityChart','values') || [0,0,0,0];
  new Chart(el, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: [C.success, C.sky, C.amber, C.rose],
        borderRadius: 6, borderSkipped: false }]
    },
    options: {
      ...BASE_OPTS, indexAxis: 'y',
      scales: {
        x: { grid: { color: C.grid }, ticks: { color: C.text, font: { family: 'Fira Code', size: 11 } } },
        y: { grid: { display: false }, ticks: { color: C.text, font: { family: 'Fira Code', size: 11 } } },
      }
    }
  });
}

// ── 3. Weekly Stacked Area ─────────────────────────────────────
function initWeeklyChart() {
  const el = document.getElementById('weeklyChart');
  if (!el || !window.Chart) return;
  const labels   = readData('weeklyChart','labels')   || ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const raised   = readData('weeklyChart','raised')   || [3,5,2,8,4,6,3];
  const resolved = readData('weeklyChart','resolved') || [2,4,2,6,3,5,2];

  // Cumulative
  let cumResolved = 0, cumOpen = 0;
  const cumR = resolved.map(v => (cumResolved += v));
  const cumO = raised.map((v,i) => (cumOpen += Math.max(0, v - resolved[i])));

  new Chart(el, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Cumulative Resolved', data: cumR,
          borderColor: C.teal, backgroundColor: 'rgba(20,184,166,.08)',
          fill: true, tension: 0.4, borderWidth: 2,
          pointBackgroundColor: C.teal, pointRadius: 3 },
        { label: 'Open Backlog', data: cumO,
          borderColor: C.amber, backgroundColor: 'rgba(245,158,11,.06)',
          fill: true, tension: 0.4, borderWidth: 2, borderDash: [5,3],
          pointBackgroundColor: C.amber, pointRadius: 3 }
      ]
    },
    options: {
      ...BASE_OPTS,
      plugins: { ...BASE_OPTS.plugins,
        legend: { display: true, position: 'top', labels: { color: C.text, font: { family: 'Fira Code', size: 11 }, boxWidth: 12, boxHeight: 3 } }
      }
    }
  });
}

// ── 4. Category Doughnut ───────────────────────────────────────
function initCategoryChart() {
  const el = document.getElementById('categoryChart');
  if (!el || !window.Chart) return;
  const labels = readData('categoryChart','labels') || ['Auth','Performance','UI/UX','Other'];
  const values = readData('categoryChart','values') || [1,1,1,1];
  const colors = [C.teal, C.amber, C.violet, C.sky, C.rose, C.success, '#a78bfa', '#fb7185'];
  new Chart(el, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length),
        borderWidth: 0, hoverOffset: 4 }]
    },
    options: {
      responsive: true, cutout: '60%',
      plugins: {
        legend: { display: true, position: 'right', labels: { color: C.text, font: { family: 'Fira Code', size: 10 }, boxWidth: 10, boxHeight: 10, padding: 8 } },
        tooltip: BASE_OPTS.plugins.tooltip
      }
    }
  });
}

// ── 5. DB Latency Grouped Bar + difference line ────────────────
function initDbLatencyOverlayChart() {
  const el = document.getElementById('mongoChart');
  if (!el || !window.Chart) return;
  const mongoTimes = readData('mongoChart','mongo') || [3.2, 3.1, 3.4, 3.0, 3.3];
  const mysqlTimes = readData('mongoChart','mysql') || [5.1, 5.3, 4.9, 5.2, 5.0];
  const labels = mongoTimes.map((_,i) => `Op ${i+1}`);
  const diff   = mysqlTimes.map((v,i) => +(v - mongoTimes[i]).toFixed(2));

  new Chart(el, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'MongoDB (ms)', data: mongoTimes, backgroundColor: 'rgba(20,184,166,.7)', borderRadius: 4, order: 2 },
        { label: 'MySQL (ms)',   data: mysqlTimes, backgroundColor: 'rgba(56,189,248,.6)', borderRadius: 4, order: 2 },
        { label: 'MySQL advantage (ms)', data: diff,
          type: 'line', borderColor: C.amber, backgroundColor: 'transparent',
          borderWidth: 2, pointRadius: 4, pointBackgroundColor: C.amber,
          yAxisID: 'y2', order: 1 }
      ]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        x:  { grid: { color: C.grid }, ticks: { color: C.text, font: { family: 'Fira Code', size: 10 } } },
        y:  { grid: { color: C.grid }, ticks: { color: C.text, font: { family: 'Fira Code', size: 10 } }, title: { display: true, text: 'ms', color: C.text } },
        y2: { position: 'right', grid: { display: false }, ticks: { color: C.amber, font: { family: 'Fira Code', size: 10 } }, title: { display: true, text: 'diff ms', color: C.amber } }
      },
      plugins: { ...BASE_OPTS.plugins, legend: { display: true, position: 'top', labels: { color: C.text, font: { family: 'Fira Code', size: 10 }, boxWidth: 10 } } }
    }
  });
}

// ── 6. DB Performance Radar ────────────────────────────────────
function initDbCompareChart() {
  const el = document.getElementById('dbCompareChart');
  if (!el || !window.Chart) return;
  const labels     = readData('dbCompareChart','labels') || ['Insert Speed','Throughput','JOIN Speed','Aggregation','Schema Flex','ACID'];
  const mongoData  = readData('dbCompareChart','mongo')  || [82,91,44,68,95,40];
  const mysqlData  = readData('dbCompareChart','mysql')  || [55,70,95,72,30,98];

  new Chart(el, {
    type: 'radar',
    data: {
      labels,
      datasets: [
        { label: 'MongoDB',
          data: mongoData, borderColor: C.teal, backgroundColor: 'rgba(20,184,166,.12)',
          borderWidth: 2, pointBackgroundColor: C.teal, pointRadius: 3 },
        { label: 'MySQL',
          data: mysqlData, borderColor: C.sky, backgroundColor: 'rgba(56,189,248,.08)',
          borderWidth: 2, pointBackgroundColor: C.sky, pointRadius: 3 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: true, aspectRatio: 1.6,
      scales: {
        r: {
          grid: { color: C.grid }, angleLines: { color: C.grid },
          pointLabels: { color: C.text, font: { family: 'Fira Code', size: 10 } },
          ticks: { display: false }, min: 0, max: 100
        }
      },
      plugins: {
        legend: { display: true, position: 'bottom', labels: { color: C.text, font: { family: 'Fira Code', size: 11 }, boxWidth: 12 } },
        tooltip: BASE_OPTS.plugins.tooltip
      }
    }
  });
}

// ── Entry point ────────────────────────────────────────────────
function initAllCharts() {
  initRingChart();
  initPriorityChart();
  initWeeklyChart();
  initCategoryChart();
  initDbLatencyOverlayChart();
  initDbCompareChart();
}