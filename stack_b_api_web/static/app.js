/* Sin librerías, llamadas externas, claves ni acciones de control. */
"use strict";

const $ = (id) => document.getElementById(id);
const number = (value, decimals = 0) => value === null || value === undefined
  ? "—" : new Intl.NumberFormat("es-ES", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
const labels = { aire: "Aire", evaporativa: "Evaporativa", liquida: "Líquida", referencia: "Referencia", evaluacion: "Evaluación" };
const PAGE_SIZE = 12;
const state = { records: [], chart: "energy", page: 1, controller: null, request: 0, ready: false };

function selectedQuery() {
  const query = new URLSearchParams();
  for (const [key, value] of new FormData($("filters"))) if (value) query.set(key, value);
  return query;
}

async function getJSON(path, signal) {
  const response = await fetch(path, { signal, cache: "no-store", credentials: "same-origin" });
  if (!response.ok) {
    let detail = "No se han podido cargar los datos.";
    try {
      const error = await response.json();
      if (typeof error.detail === "string") detail = error.detail;
    } catch (_) { /* Usa el mensaje seguro de reserva. */ }
    throw new Error(`${detail} (HTTP ${response.status})`);
  }
  return response.json();
}

function fillFilters(options) {
  const mapping = { site_id: "site-filter", cooling_type: "cooling-filter", split: "split-filter" };
  for (const [column, id] of Object.entries(mapping)) {
    const select = $(id);
    const current = select.value;
    while (select.options.length > 1) select.remove(1);
    for (const value of options[column] || []) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labels[value] || value;
      select.append(option);
    }
    select.value = current;
  }
}

function setMetrics(data) {
  $("metric-pue").textContent = number(data.pue, 2);
  $("metric-wue").textContent = number(data.wue_l_kwh, 2);
  $("metric-energy").textContent = number(data.energy_total_kwh);
  $("metric-water").textContent = number(data.water_l);
  $("metric-it").textContent = `Energía TI: ${number(data.energy_it_kwh)} kWh`;
  $("alert-count").textContent = number(data.rule_alerts);
  $("alert-description").textContent = `${number(data.rule_alerts)} de ${number(data.rows)} registros superan al menos una regla pedagógica. Un registro puede activar varias reglas.`;
  const dateFormat = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
  $("period").textContent = data.period_start
    ? `${dateFormat.format(new Date(data.period_start))} — ${dateFormat.format(new Date(data.period_end))} · ${number(data.rows)} registros horarios · UTC`
    : "Sin registros para esta combinación";
  $("empty-panel").hidden = data.rows !== 0;
}

async function refresh() {
  const request = ++state.request;
  if (state.controller) state.controller.abort();
  state.controller = new AbortController();
  $("metric-grid").setAttribute("aria-busy", "true");
  $("refresh-button").disabled = true;
  $("load-status").textContent = "Leyendo el CSV local…";
  $("error-panel").hidden = true;
  const query = selectedQuery();
  const recordQuery = new URLSearchParams(query);
  recordQuery.set("limit", "1000");
  try {
    const [metrics, records] = await Promise.all([
      getJSON(`/api/metrics?${query}`, state.controller.signal),
      getJSON(`/api/records?${recordQuery}`, state.controller.signal),
    ]);
    if (request !== state.request) return;
    state.records = records.records;
    state.page = 1;
    state.ready = true;
    fillFilters(metrics.filters || {});
    setMetrics(metrics);
    renderChart();
    renderRecords();
    $("load-status").textContent = records.total > records.returned
      ? `Gráfico y tabla limitados a los ${number(records.returned)} registros más recientes. Indicadores: todo el periodo.`
      : "Actualizado · Datos simulados";
  } catch (error) {
    if (error.name === "AbortError" || request !== state.request) return;
    $("error-panel").textContent = `${error.message} Comprueba que el servidor local sigue abierto y pulsa Actualizar para reintentar.${state.ready ? " Se conserva la última vista cargada; puede no corresponder a los filtros actuales." : ""}`;
    $("error-panel").hidden = false;
    $("load-status").textContent = state.ready ? "Sin actualizar · Vista anterior" : "No se pudo cargar el panel";
  } finally {
    if (request === state.request) {
      $("refresh-button").disabled = false;
      $("metric-grid").setAttribute("aria-busy", "false");
    }
  }
}

function svgElement(tag, attributes, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes || {})) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = text;
  return node;
}

function dailyTotals() {
  const buckets = new Map();
  for (const row of state.records) {
    const date = String(row.timestamp).slice(0, 10);
    const bucket = buckets.get(date) || { date, energy: 0, it: 0, water: 0 };
    bucket.energy += Number(row.energy_total_kwh) || 0;
    bucket.it += Number(row.energy_it_kwh) || 0;
    bucket.water += Number(row.water_l) || 0;
    buckets.set(date, bucket);
  }
  return [...buckets.values()].sort((a, b) => a.date.localeCompare(b.date));
}

function renderChart() {
  const energy = state.chart === "energy";
  const daily = dailyTotals();
  const svg = $("trend-chart");
  svg.replaceChildren();
  svg.append(svgElement("title", { id: "chart-svg-title" }, energy ? "Energía total y TI por día" : "Agua retirada por día"));
  svg.append(svgElement("desc", { id: "chart-svg-desc" }, `${daily.length} días de datos simulados. Los valores completos están en la tabla desplegable después del gráfico.`));
  $("chart-description").textContent = energy ? "Suma diaria de energía total y energía TI, en kWh. Horas en UTC." : "Suma diaria de agua retirada in situ, en litros. Horas en UTC.";
  const left = 66, right = 18, top = 15, bottom = 206, width = 720 - left - right;
  const maximum = Math.max(...daily.map(d => energy ? d.energy : d.water), 1) * 1.15;
  for (let tick = 0; tick <= 4; tick++) {
    const y = bottom - tick * (bottom - top) / 4;
    svg.append(svgElement("line", { x1: left, x2: 702, y1: y, y2: y, class: "chart-gridline" }));
    svg.append(svgElement("text", { x: left - 10, y: y + 3, "text-anchor": "end", class: "chart-axis" }, number(maximum * tick / 4)));
  }
  if (!daily.length) svg.append(svgElement("text", { x: 375, y: 112, "text-anchor": "middle", class: "chart-axis" }, "No hay datos para este filtro"));
  daily.forEach((day, index) => {
    const slot = width / daily.length;
    const center = left + slot * (index + 0.5);
    const barWidth = Math.min(25, slot * .27);
    const series = energy ? [[day.energy, "#275e54", -barWidth - 2], [day.it, "#8fb7a4", 2]] : [[day.water, "#5e95a4", -barWidth / 2]];
    for (const [value, fill, offset] of series) {
      const height = (value / maximum) * (bottom - top);
      const bar = svgElement("rect", { x: center + offset, y: bottom - height, width: barWidth, height, rx: 3, fill });
      bar.append(svgElement("title", {}, `${day.date}: ${number(value, 1)} ${energy ? "kWh" : "L"}`));
      svg.append(bar);
    }
    const text = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "short", timeZone: "UTC" }).format(new Date(`${day.date}T12:00:00Z`));
    // Mantiene legibles los rótulos si se amplía el CSV a más días.
    if (daily.length <= 14 || index % Math.ceil(daily.length / 10) === 0) {
      svg.append(svgElement("text", { x: center, y: 230, "text-anchor": "middle", class: "chart-axis" }, text));
    }
  });
  const legend = $("chart-legend");
  legend.replaceChildren();
  for (const [className, text] of energy ? [["legend-total", "Energía total"], ["legend-it", "Energía TI"]] : [["legend-water", "Agua retirada"]]) {
    const span = document.createElement("span");
    const mark = document.createElement("i");
    mark.className = className;
    mark.setAttribute("aria-hidden", "true");
    span.append(mark, document.createTextNode(text));
    legend.append(span);
  }
  const head = $("chart-data-head");
  head.replaceChildren();
  for (const label of energy ? ["Día · UTC", "Total · kWh", "TI · kWh"] : ["Día · UTC", "Agua · L"]) {
    const th = document.createElement("th"); th.scope = "col"; th.textContent = label; head.append(th);
  }
  const body = $("chart-data-body");
  body.replaceChildren();
  for (const day of daily) {
    const tr = document.createElement("tr");
    for (const value of energy ? [day.date, number(day.energy, 1), number(day.it, 1)] : [day.date, number(day.water, 1)]) {
      const td = document.createElement("td"); td.textContent = value; tr.append(td);
    }
    body.append(tr);
  }
}

function renderRecords() {
  const visible = state.records.filter(row => !$("alerts-only").checked || row.rule_alert);
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  state.page = Math.max(1, Math.min(state.page, pages));
  const start = (state.page - 1) * PAGE_SIZE;
  const body = $("records-body");
  body.replaceChildren();
  const dateFormat = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hourCycle: "h23" });
  for (const row of visible.slice(start, start + PAGE_SIZE)) {
    const tr = document.createElement("tr");
    const values = [dateFormat.format(new Date(row.timestamp)), row.site_id, labels[row.cooling_type] || row.cooling_type, number(row.energy_it_kwh, 1), number(row.energy_total_kwh, 1), number(row.water_l, 1)];
    values.forEach((value, index) => {
      const td = document.createElement("td");
      if (index >= 3) td.className = "numeric";
      if (index === 0) td.className = "date-cell";
      if (index === 2) { const badge = document.createElement("span"); badge.className = "cooling-badge"; badge.textContent = value; td.append(badge); }
      else td.textContent = value;
      tr.append(td);
    });
    const signal = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = row.rule_alert ? "signal-alert" : "signal-normal";
    badge.textContent = row.rule_alert ? "Revisar" : "Sin señal";
    signal.append(badge);
    if (row.rule_alert) { const reason = document.createElement("span"); reason.className = "rule-reason"; reason.textContent = row.rule_reason; signal.append(reason); }
    tr.append(signal); body.append(tr);
  }
  if (!visible.length) {
    const row = document.createElement("tr"); const td = document.createElement("td"); td.colSpan = 7;
    td.textContent = $("alerts-only").checked ? "No hay alertas en los registros seleccionados." : "No hay registros para mostrar.";
    row.append(td); body.append(row);
  }
  $("record-count").textContent = visible.length ? `${start + 1}–${Math.min(start + PAGE_SIZE, visible.length)} de ${number(visible.length)} registros${$("alerts-only").checked ? " con alerta" : ""}` : "0 registros";
  $("page-number").textContent = `${state.page} / ${pages}`;
  $("prev-page").disabled = state.page === 1;
  $("next-page").disabled = state.page >= pages;
}

$("filters").addEventListener("submit", event => { event.preventDefault(); refresh(); });
for (const select of $("filters").querySelectorAll("select")) select.addEventListener("change", refresh);
for (const button of document.querySelectorAll("[data-chart]")) button.addEventListener("click", () => {
  state.chart = button.dataset.chart;
  for (const item of document.querySelectorAll("[data-chart]")) {
    const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active));
  }
  renderChart();
});
$("alerts-only").addEventListener("change", () => { state.page = 1; renderRecords(); });
$("view-alerts").addEventListener("click", () => {
  $("alerts-only").checked = true; state.page = 1; renderRecords();
  $("alerts-only").focus();
  $("records-title").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
});
$("prev-page").addEventListener("click", () => { state.page--; renderRecords(); });
$("next-page").addEventListener("click", () => { state.page++; renderRecords(); });
refresh();
