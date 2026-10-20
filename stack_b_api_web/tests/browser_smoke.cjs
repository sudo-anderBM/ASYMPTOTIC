/* QA opcional: requiere Playwright y Chromium, no son dependencias de ejecución.
 * Servidor iniciado en 127.0.0.1:8000. Ejecutar con node desde cualquier carpeta.
 */
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

(async () => {
  const browser = await chromium.launch({
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}),
    headless: true,
    chromiumSandbox: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
  const errors = [];
  const externalRequests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (!request.url().startsWith("http://127.0.0.1:8000/")) externalRequests.push(request.url());
  });
  const loaded = async () => page.waitForFunction(() => document.getElementById("load-status").textContent.includes("Actualizado"));
  await page.goto("http://127.0.0.1:8000/");
  await loaded();
  assert.match(await page.title(), /CIFOX/);
  assert.equal(await page.locator("#records-body tr").count(), 12);
  assert.match(await page.locator("#record-count").innerText(), /504/);
  assert.notEqual(await page.locator("#metric-pue").innerText(), "—");
  assert.equal(await page.locator("#trend-chart rect").count(), 14);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  const snapshots = path.join(__dirname, "..", "screenshots");
  fs.mkdirSync(snapshots, { recursive: true });
  await page.screenshot({ path: path.join(snapshots, "panel-escritorio.png"), fullPage: true });

  await page.getByRole("button", { name: "Agua", exact: true }).click();
  assert.equal(await page.locator("#trend-chart rect").count(), 7);
  await page.locator(".chart-data summary").click();
  assert.equal(await page.locator("#chart-data-body tr").count(), 7);
  await page.locator(".chart-data summary").click();
  await page.getByRole("button", { name: "Energía", exact: true }).click();
  await page.locator("#next-page").click();
  assert.equal(await page.locator("#page-number").innerText(), "2 / 42");
  await page.locator("#prev-page").click();
  await page.locator("#view-alerts").click();
  assert.equal(await page.locator("#alerts-only").isChecked(), true);
  assert.equal(await page.locator(".signal-normal").count(), 0);
  await page.locator("#alerts-only").uncheck();

  await page.locator("#site-filter").selectOption("SIM-A");
  await loaded();
  assert.match(await page.locator("#record-count").innerText(), /168/);
  assert.ok((await page.locator("#records-body tr td:nth-child(2)").allTextContents()).every(x => x === "SIM-A"));
  await page.locator("#cooling-filter").selectOption("evaporativa");
  await loaded();
  assert.equal(await page.locator("#empty-panel").isVisible(), true);
  assert.equal(await page.locator("#metric-pue").innerText(), "—");
  assert.equal(await page.locator("#record-count").innerText(), "0 registros");

  // Cambios rápidos: gana la última selección, nunca una respuesta anterior.
  await page.locator("#cooling-filter").selectOption("");
  await page.locator("#site-filter").selectOption("SIM-B");
  await page.locator("#site-filter").selectOption("SIM-C");
  await loaded();
  assert.ok((await page.locator("#records-body tr td:nth-child(2)").allTextContents()).every(x => x === "SIM-C"));
  await page.locator("#site-filter").selectOption("");
  await loaded();
  await page.locator("#split-filter").selectOption("evaluacion");
  await loaded();
  assert.match(await page.locator("#record-count").innerText(), /288/);
  await page.locator("#split-filter").selectOption("");
  await loaded();

  await page.route("**/api/metrics?*", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Fallo de prueba" }) }));
  await page.locator("#refresh-button").click();
  await page.waitForFunction(() => !document.getElementById("error-panel").hidden);
  assert.match(await page.locator("#error-panel").innerText(), /Se conserva la última vista/);
  assert.equal(await page.locator("#refresh-button").isDisabled(), false);
  await page.unroute("**/api/metrics?*");
  await page.locator("#refresh-button").click();
  await loaded();
  assert.equal(await page.locator("#error-panel").isVisible(), false);
  assert.equal(await page.locator("#refresh-button").isDisabled(), false);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => scrollTo(0, 0));
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.screenshot({ path: path.join(snapshots, "panel-movil.png"), fullPage: true });
  await page.locator("#cooling-filter").selectOption("liquida");
  await loaded();
  assert.match(await page.locator("#record-count").innerText(), /168/);
  assert.deepEqual(errors, []);
  assert.deepEqual(externalRequests, []);
  await browser.close();
  console.log("PASS: carga, API, gráfico, tabla, filtros, estado vacío, paginación, cambios rápidos, error/reintento, móvil, sin errores JS ni peticiones externas.");
})().catch(error => { console.error(error); process.exit(1); });
