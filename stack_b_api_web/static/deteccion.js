"use strict";

const USAR_EJEMPLO = false;

const $ = (id) => document.getElementById(id);

async function pedir(nombre, params = {}, signal) {
  const url = USAR_EJEMPLO
    ? `/static/mock/${nombre}.json`
    : `/api/${nombre}?${new URLSearchParams(params)}`;

  const respuesta = await fetch(url, { signal, cache: "no-store" });

  if (!respuesta.ok) {
    let mensaje = `No se pudieron cargar los datos (HTTP ${respuesta.status}).`;
    try {
      const error = await respuesta.json();
      if (typeof error.detail === "string") mensaje = error.detail;
    } catch (_) {
      
    }
    throw new Error(mensaje);
  }
  return respuesta.json();
}

function parametros() {
  return {
    tipo: $("tipo").value,
    magnitud: Number($("magnitud").value) / 100,
    sitio: $("sitio").value,
    semilla: Number($("semilla").value),
  };
}

let controlador = null;

async function cargarEscenario() {
  if (controlador) controlador.abort();     
  controlador = new AbortController();

  $("estado").textContent = "Cargando…";
  $("error").hidden = true;

  try {
    const datos = await pedir("scenario", parametros(), controlador.signal);
    pintarTabla(datos); 
    pintarGrafica(datos);
    pintarVeredicto(datos);   
    limpiarExplicacion();       
    $("estado").textContent = "Actualizado · Datos simulados";
  } catch (error) {
    if (error.name === "AbortError") return;   
    $("error").textContent = error.message;
    $("error").hidden = false;
    $("estado").textContent = "No se pudo actualizar";
  }
}



const detectores = new Map();


const COLORES = {
  "1_reglas": "#b76b30",            // naranja
  "2_isolation_forest": "#7a6aa8",  // morado
  "3_residual_3sigma": "#275e54",   // verde 
  "4_residual_cusum": "#5e95a4",    // azul
  "5_zscore_simple": "#8a8f3c",     // oliva
};

async function cargarDetectores() {
  try {
    const datos = await pedir("detectors");
    detectores.clear();
    for (const d of datos.detectores) {
      detectores.set(d.id, { ...d, color: COLORES[d.id] || "#66766e" });
    }
    console.log("detectores:", datos.detectores.map((d) => d.nombre));
  } catch (error) {
    $("error").textContent = `No se pudo cargar la lista de detectores. ${error.message}`;
    $("error").hidden = false;
  }
}

// Tabla comparativa

const formato1 = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 1, maximumFractionDigits: 1 });


function numero(valor) {
  return valor === null || valor === undefined ? "—" : formato1.format(valor);
}


function elegirMejor(lista) {
  const completos = lista.filter((d) => d.eventos_totales > 0 && d.eventos_detectados === d.eventos_totales);
  if (completos.length === 0) return null;
  completos.sort((a, b) =>
    (a.falsas_alarmas_dia - b.falsas_alarmas_dia) ||
    (a.exceso_no_detectado - b.exceso_no_detectado) ||
    ((a.fit_ms + a.pred_ms) - (b.fit_ms + b.pred_ms)));
  return completos[0].id;
}

function celda(texto, numerica = false) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (numerica) td.className = "numeric";
  return td;
}

function pintarTabla(datos) {
  const cuerpo = $("tabla-detectores");
  cuerpo.replaceChildren();
  $("th-exceso").textContent = `Exceso no detectado · ${datos.unidad}`;
  const mejor = elegirMejor(datos.detectores);

  for (const d of datos.detectores) {
    const info = detectores.get(d.id) || { nombre: d.id, descripcion: "", color: "#66766e" };
    const fila = document.createElement("tr");
    if (d.id === mejor) fila.className = "mejor";

    
    const tdNombre = document.createElement("td");
    const caja = document.createElement("div");
    caja.className = "det-nombre";
    const punto = document.createElement("span");
    punto.className = "det-punto";
    punto.style.backgroundColor = info.color;
    const textos = document.createElement("span");
    textos.textContent = info.nombre;
    if (d.id === mejor) {
      const etiqueta = document.createElement("span");
      etiqueta.className = "mejor-badge";
      etiqueta.textContent = "MEJOR";
      textos.append(etiqueta);
    }
    const descripcion = document.createElement("span");
    descripcion.className = "det-desc";
    descripcion.textContent = info.descripcion;
    textos.append(descripcion);
    caja.append(punto, textos);
    tdNombre.append(caja);

    fila.append(
      tdNombre,
      celda(`${d.eventos_detectados} de ${d.eventos_totales}`, true),
      celda(numero(d.horas_hasta_alerta), true),
      celda(numero(d.falsas_alarmas_dia), true),
      celda(numero(d.exceso_no_detectado), true),
      celda(numero(d.fit_ms + d.pred_ms), true),
    );
    cuerpo.append(fila);
  }

  if (datos.detectores.length === 0) {
    const fila = document.createElement("tr");
    const td = celda("Sin resultados para este escenario.");
    td.colSpan = 6;
    fila.append(td);
    cuerpo.append(fila);
  }
}
//  Gráfica

const G = {
  izq: 118, der: 700,          
  arriba: 28, abajo: 200,      
  carrilInicio: 228, carrilAlto: 26,
};
const HORA_MS = 3600 * 1000;
const NOMBRES_VARIABLE = { water_l: "agua", energy_total_kwh: "energía total" };

function svg(etiqueta, atributos = {}, texto) {
  const nodo = document.createElementNS("http://www.w3.org/2000/svg", etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) nodo.setAttribute(clave, String(valor));
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

const formatoHora = new Intl.DateTimeFormat("es-MX", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC",
});

function pintarGrafica(datos) {
  const lienzo = $("grafica");
  lienzo.replaceChildren();
  const serie = datos.serie;
  const nCarriles = datos.detectores.length;
  const altoTotal = G.carrilInicio + nCarriles * G.carrilAlto + 40;
  lienzo.setAttribute("viewBox", `0 0 720 ${altoTotal}`);
  lienzo.append(svg("title", { id: "grafica-svg-titulo" }, `Serie horaria de ${NOMBRES_VARIABLE[datos.variable] || datos.variable} con alertas por detector`));

  if (serie.length === 0) {
    lienzo.append(svg("text", { x: 360, y: 110, "text-anchor": "middle", class: "det-svg-texto" }, "Sin datos para este escenario"));
    return;
  }

 
  const t0 = Date.parse(serie[0].timestamp);
  const t1 = Date.parse(serie[serie.length - 1].timestamp) + HORA_MS;   
  const x = (ms) => G.izq + ((ms - t0) / (t1 - t0)) * (G.der - G.izq);
  const anchoHora = (G.der - G.izq) / ((t1 - t0) / HORA_MS);

  
  const valores = serie.flatMap((p) => [p.observado, p.esperado]).filter((v) => v !== null && v !== undefined);
  let min = Math.min(...valores), max = Math.max(...valores);
  if (min === max) { min -= 1; max += 1; }           
  const margen = (max - min) * 0.1;
  min -= margen; max += margen;
  const y = (v) => G.abajo - ((v - min) / (max - min)) * (G.abajo - G.arriba);
  const fondoCarriles = G.carrilInicio + nCarriles * G.carrilAlto;

  
  for (const ev of datos.eventos_reales) {
    const xa = x(Date.parse(ev.inicio));
    const xb = x(Date.parse(ev.fin) + HORA_MS);
    lienzo.append(svg("rect", { x: xa, y: G.arriba, width: xb - xa, height: G.abajo - G.arriba, class: "det-banda" }));
    lienzo.append(svg("rect", { x: xa, y: G.carrilInicio, width: xb - xa, height: fondoCarriles - G.carrilInicio, class: "det-banda-carril" }));
  }


  for (let i = 0; i <= 4; i++) {
    const v = min + ((max - min) * i) / 4;
    lienzo.append(svg("line", { x1: G.izq, x2: G.der, y1: y(v), y2: y(v), class: "chart-gridline" }));
    lienzo.append(svg("text", { x: G.izq - 8, y: y(v) + 3, "text-anchor": "end", class: "det-svg-texto" }, formato1.format(v)));
  }
  lienzo.append(svg("text", { x: G.izq - 8, y: G.arriba - 12, "text-anchor": "end", class: "det-svg-unidad" }, datos.unidad));

  
  const trazo = (campo) => {
    let d = "", nuevo = true;
    for (const p of serie) {
      const v = p[campo];
      if (v === null || v === undefined) { nuevo = true; continue; }
      const px = x(Date.parse(p.timestamp) + HORA_MS / 2);   // centro de la hora
      d += `${nuevo ? "M" : "L"}${px.toFixed(1)} ${y(v).toFixed(1)}`;
      nuevo = false;
    }
    return d;
  };
  lienzo.append(svg("path", { d: trazo("esperado"), class: "det-esperado" }));
  lienzo.append(svg("path", { d: trazo("observado"), class: "det-observado" }));

  datos.detectores.forEach((det, i) => {
    const info = detectores.get(det.id) || { nombre: det.id, color: "#66766e" };
    const yc = G.carrilInicio + i * G.carrilAlto + G.carrilAlto / 2;
    lienzo.append(svg("line", { x1: G.izq, x2: G.der, y1: yc, y2: yc, class: "chart-gridline" }));
    lienzo.append(svg("text", { x: G.izq - 8, y: yc + 4, "text-anchor": "end", class: "det-svg-carril" }, info.nombre));
    for (const ts of det.alertas) {
      const marca = svg("rect", {
        x: x(Date.parse(ts)) + 1, y: yc - 7, width: Math.max(3, anchoHora - 2), height: 14, rx: 2,
        fill: info.color, class: "det-alerta", tabindex: 0, role: "button",
        "aria-label": `Alerta de ${info.nombre}, ${formatoHora.format(new Date(ts))} UTC. Pulsa Enter para ver la explicación.`,
        "data-timestamp": ts, "data-detector": det.id,
      });
      marca.append(svg("title", {}, `${info.nombre} · ${formatoHora.format(new Date(ts))} UTC`));
      lienzo.append(marca);
    }
  });

  const horas = (t1 - t0) / HORA_MS;
  const paso = (horas <= 48 ? 6 : 12) * HORA_MS;
  for (let t = Math.ceil(t0 / paso) * paso; t <= t1; t += paso) {
    lienzo.append(svg("line", { x1: x(t), x2: x(t), y1: G.abajo, y2: G.abajo + 4, class: "chart-gridline" }));
    lienzo.append(svg("text", { x: x(t), y: fondoCarriles + 18, "text-anchor": "middle", class: "det-svg-texto" }, formatoHora.format(new Date(t))));
  }

  
  const nombre = NOMBRES_VARIABLE[datos.variable] || datos.variable;
  $("grafica-descripcion").textContent =
    `${nombre[0].toUpperCase()}${nombre.slice(1)} por hora en ${datos.parametros.sitio} (${datos.unidad}), ${serie.length} horas en UTC. ` +
    "Las franjas marcan dónde se inyectó el problema; debajo, cuándo avisó cada detector.";
  pintarLeyendaGrafica();
}

function pintarLeyendaGrafica() {
  const leyenda = $("grafica-leyenda");
  leyenda.replaceChildren();
  for (const [clase, texto] of [["leyenda-linea", "Observado"], ["leyenda-linea punteada", "Esperado (modelo residual)"], ["leyenda-banda", "Problema inyectado"]]) {
    const item = document.createElement("span");
    const marca = document.createElement("i");
    marca.className = clase;
    marca.setAttribute("aria-hidden", "true");
    item.append(marca, document.createTextNode(texto));
    leyenda.append(item);
  }
}


let controladorExplicacion = null;

function limpiarExplicacion() {
  $("explicacion-contenido").hidden = true;
  $("explicacion-vacia").hidden = false;
}

async function mostrarExplicacion(marca) {
  // Resalta solo la marca elegida.
  for (const m of document.querySelectorAll(".det-alerta.activa")) m.classList.remove("activa");
  marca.classList.add("activa");

  if (controladorExplicacion) controladorExplicacion.abort();
  controladorExplicacion = new AbortController();

  const timestamp = marca.dataset.timestamp;
  const info = detectores.get(marca.dataset.detector);
  const nombre = info ? info.nombre : marca.dataset.detector;

  $("explicacion-vacia").hidden = true;
  $("explicacion-contenido").hidden = false;
  $("exp-fecha").textContent = "Cargando la explicación…";
  for (const id of ["exp-observado", "exp-esperado", "exp-desviacion", "exp-texto"]) $(id).textContent = "";

  try {
    const e = await pedir("explain", { ...parametros(), timestamp }, controladorExplicacion.signal);
    $("exp-fecha").textContent = `Alerta de ${nombre} · ${e.sitio} · ${formatoHora.format(new Date(e.timestamp))} UTC`;
    $("exp-observado").textContent = `${numero(e.observado)} ${e.unidad}`;
    $("exp-esperado").textContent = `${numero(e.esperado)} ${e.unidad}`;
    $("exp-desviacion").textContent = e.desviacion_pct === null
      ? "—"
      : `${e.desviacion_pct > 0 ? "+" : ""}${numero(e.desviacion_pct)} %`;
    $("exp-texto").textContent = `${e.texto} ${e.aviso}`;
  } catch (error) {
    if (error.name === "AbortError") return;
    $("exp-fecha").textContent = `No se pudo cargar la explicación. ${error.message}`;
  }
}

$("grafica").addEventListener("click", (evento) => {
  const marca = evento.target.closest(".det-alerta");
  if (marca) mostrarExplicacion(marca);
});


$("grafica").addEventListener("keydown", (evento) => {
  if (evento.key !== "Enter" && evento.key !== " ") return;
  const marca = evento.target.closest(".det-alerta");
  if (!marca) return;
  evento.preventDefault();          
  mostrarExplicacion(marca);
});

// Vista de resumen

const resumen = { datos: null, version: "normal", deEjemplo: false };
const META_DETECCION = 0.9;       
const MAX_FALSAS_DIA = 1;          
const MAGNITUD_OBJETIVO = 0.1;     
const formatoPct = new Intl.NumberFormat("es-MX", { style: "percent", maximumFractionDigits: 0 });

async function cargarResumen() {
  const tipo = $("tipo").value;
  $("resumen-descripcion").textContent = "Cargando el barrido…";
  try {
    resumen.datos = await pedir("sweep", { tipo });
    resumen.deEjemplo = USAR_EJEMPLO;
  } catch (error) {
    
    try {
      const r = await fetch("/static/mock/sweep.json", { cache: "no-store" });
      resumen.datos = await r.json();
      resumen.deEjemplo = true;
    } catch (_) {
      resumen.datos = null;
      $("resumen-descripcion").textContent = `No se pudo cargar el barrido. ${error.message}`;
      $("recomendacion").textContent = "";
      $("grafica-resumen").replaceChildren();
      return;
    }
  }
  pintarResumen();
}

function recomendado(lista, indice) {
  const cumplen = lista.filter((d) => d.deteccion[indice] >= META_DETECCION && d.falsas_alarmas_dia[indice] <= MAX_FALSAS_DIA);
  cumplen.sort((a, b) => (a.fit_ms + a.pred_ms) - (b.fit_ms + b.pred_ms));
  return cumplen[0] || null;
}

function nombreDe(id) {
  return (detectores.get(id) || { nombre: id }).nombre;
}

function textoRecomendacion(datos, lista) {
  const objetivo = datos.magnitudes.indexOf(MAGNITUD_OBJETIVO);
  const problema = datos.tipo === "fuga" ? "fugas de agua" : "gastos extra de energía";
  const ms = (d) => formato1.format(d.fit_ms + d.pred_ms);
  const meta = `≥ ${formatoPct.format(META_DETECCION)} de los eventos con ≤ ${MAX_FALSAS_DIA} falsa alarma al día`;
  if (objetivo >= 0) {
    const r = recomendado(lista, objetivo);
    if (r) {
      return `Para ${problema} del ${formatoPct.format(MAGNITUD_OBJETIVO)}, el detector más barato que detecta ${meta} es ${nombreDe(r.id)}: ` +
        `${formatoPct.format(r.deteccion[objetivo])} detectado, ${formato1.format(r.falsas_alarmas_dia[objetivo])} falsas alarmas/día, ${ms(r)} ms.`;
    }
  }
  // Nadie cumple en el 10 %: buscamos la magnitud más pequeña en la que alguien sí cumple.
  for (let i = 0; i < datos.magnitudes.length; i++) {
    const r = recomendado(lista, i);
    if (r) {
      return `Ningún detector logra ${meta} con ${problema} del ${formatoPct.format(MAGNITUD_OBJETIVO)}. ` +
        `El primero en lograrlo es ${nombreDe(r.id)}, a partir del ${formatoPct.format(datos.magnitudes[i])} (${ms(r)} ms).`;
    }
  }
  return `Ningún detector logra ${meta} en este barrido.`;
}

function pintarResumen() {
  const datos = resumen.datos;
  if (!datos) return;
  const lista = datos[resumen.version] || [];
  const mags = datos.magnitudes;

  $("resumen-titulo").textContent = datos.tipo === "fuga"
    ? "Detección según el tamaño de la fuga"
    : "Detección según el tamaño del gasto extra";
  $("resumen-descripcion").textContent =
    `${datos.tipo === "fuga" ? "Fugas de agua" : "Gasto extra de energía"}: porcentaje de eventos detectados según el tamaño del problema. ` +
    `Cada punto resume ${datos.meta.eventos_por_punto} eventos (${datos.meta.semillas} semillas × 3 sitios × 3 ventanas); las barras verticales son el intervalo de confianza del 95 %.` +
    (resumen.version === "dificil"
      ? " Datos difíciles: el agua lleva ruido de ±5 % y una relación no lineal con la temperatura" +
        (datos.tipo === "fuga" ? "." : "; la energía no cambia, por eso los resultados son casi iguales.")
      : "");
  $("recomendacion").textContent = (resumen.deEjemplo ? "EJEMPLO, no medido. " : "") + textoRecomendacion(datos, lista);

  
  const L = { izq: 60, der: 700, arriba: 20, abajo: 250 };
  const lienzo = $("grafica-resumen");
  lienzo.replaceChildren();
  lienzo.append(svg("title", { id: "resumen-svg-titulo" }, "Fracción de eventos detectados por magnitud y detector"));
  const paso = (L.der - L.izq) / mags.length;
  const x = (i) => L.izq + paso * (i + 0.5);                      
  const y = (v) => L.abajo - v * (L.abajo - L.arriba);            

  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    lienzo.append(svg("line", { x1: L.izq, x2: L.der, y1: y(v), y2: y(v), class: "chart-gridline" }));
    lienzo.append(svg("text", { x: L.izq - 8, y: y(v) + 3, "text-anchor": "end", class: "det-svg-texto" }, formatoPct.format(v)));
  }
  
  const iObj = mags.indexOf(MAGNITUD_OBJETIVO);
  if (iObj >= 0) {
    lienzo.append(svg("rect", { x: x(iObj) - paso / 2, y: L.arriba, width: paso, height: L.abajo - L.arriba, class: "det-banda-carril" }));
  }
  lienzo.append(svg("line", { x1: L.izq, x2: L.der, y1: y(META_DETECCION), y2: y(META_DETECCION), stroke: "#b76b30", "stroke-dasharray": "4 4", "stroke-width": 1 }));
  lienzo.append(svg("text", { x: L.der, y: y(META_DETECCION) - 5, "text-anchor": "end", class: "det-svg-texto" }, `meta ${formatoPct.format(META_DETECCION)}`));

  mags.forEach((m, i) => {
    lienzo.append(svg("text", { x: x(i), y: L.abajo + 18, "text-anchor": "middle", class: "det-svg-texto" }, formatoPct.format(m)));
  });
  lienzo.append(svg("text", { x: (L.izq + L.der) / 2, y: L.abajo + 38, "text-anchor": "middle", class: "det-svg-unidad" }, "Tamaño del problema"));

  lista.forEach((d, k) => {
    const color = (detectores.get(d.id) || { color: "#66766e" }).color;
    const dx = (k - (lista.length - 1) / 2) * 5;
    let ruta = "";
    d.deteccion.forEach((v, i) => {
      ruta += `${i === 0 ? "M" : "L"}${(x(i) + dx).toFixed(1)} ${y(v).toFixed(1)}`;
      const ic = d.deteccion_ic95 && d.deteccion_ic95[i];
      if (ic) lienzo.append(svg("line", { x1: x(i) + dx, x2: x(i) + dx, y1: y(ic[0]), y2: y(ic[1]), stroke: color, class: "det-bigote" }));
    });
    lienzo.append(svg("path", { d: ruta, stroke: color, class: "det-linea" }));
    d.deteccion.forEach((v, i) => {
      const punto = svg("circle", { cx: x(i) + dx, cy: y(v), r: 3.5, fill: color });
      punto.append(svg("title", {}, `${nombreDe(d.id)} · ${formatoPct.format(mags[i])}: ${formatoPct.format(v)} detectado, ${formato1.format(d.falsas_alarmas_dia[i])} falsas alarmas/día`));
      lienzo.append(punto);
    });
  });

  const leyenda = $("resumen-leyenda");
  leyenda.replaceChildren();
  for (const d of lista) {
    const item = document.createElement("span");
    const marca = document.createElement("i");
    marca.setAttribute("aria-hidden", "true");
    marca.style.backgroundColor = (detectores.get(d.id) || { color: "#66766e" }).color;
    item.append(marca, document.createTextNode(`${nombreDe(d.id)} · ${formato1.format(d.fit_ms + d.pred_ms)} ms`));
    leyenda.append(item);
  }

  const m = datos.meta;
  $("resumen-meta").textContent = resumen.deEjemplo
    ? "Barrido de EJEMPLO (valores no medidos): falta generar results/ con python -m greenai.sweep. Datos simulados."
    : `${m.nota} Generado: ${m.generado} · equipo: ${m.equipo} · Python ${m.python}.`;
}

for (const boton of document.querySelectorAll("[data-version]")) {
  boton.addEventListener("click", () => {
    resumen.version = boton.dataset.version;
    for (const b of document.querySelectorAll("[data-version]")) {
      const activo = b === boton;
      b.classList.toggle("active", activo);
      b.setAttribute("aria-pressed", String(activo));
    }
    pintarResumen();
  });
}


$("tipo").addEventListener("change", cargarResumen);

// ---------- Mejora 2 · Veredicto del escenario ----------

const SIN_ANIMACION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Cuenta desde 0 hasta el valor final en ~0.6 s (o lo pone directo si el usuario pidió menos movimiento).
function animarNumero(elemento, valor, formatear) {
  if (valor === null || valor === undefined || SIN_ANIMACION) {
    elemento.textContent = valor === null || valor === undefined ? "—" : formatear(valor);
    return;
  }
  const inicio = performance.now();
  const duracion = 600;
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / duracion);
    const suave = 1 - Math.pow(1 - t, 3);            // empieza rápido y frena al final
    elemento.textContent = formatear(valor * suave);
    if (t < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// Escribe una frase con partes en negrita sin usar innerHTML: [["texto normal"], ["texto", true], ...]
function frase(elemento, partes) {
  elemento.replaceChildren();
  for (const [texto, negrita] of partes) {
    if (negrita) {
      const fuerte = document.createElement("strong");
      fuerte.textContent = texto;
      elemento.append(fuerte);
    } else {
      elemento.append(document.createTextNode(texto));
    }
  }
}

function pintarVeredicto(datos) {
  const p = datos.parametros;
  const esFuga = p.tipo === "fuga";
  const tamano = new Intl.NumberFormat("es-MX", { style: "percent", maximumFractionDigits: 0 }).format(p.magnitud);
  const problema = esFuga ? "una fuga de agua" : "un gasto extra de energía";
  const reglas = datos.detectores.find((d) => d.id === "1_reglas");
  const idMejor = elegirMejor(datos.detectores);
  const mejor = datos.detectores.find((d) => d.id === idMejor) || null;
  const nombreMejor = mejor ? (detectores.get(mejor.id) || { nombre: mejor.id }).nombre : null;
  const coste = (d) => d.fit_ms + d.pred_ms;
  const masCaro = datos.detectores.reduce((a, b) => (coste(b) > coste(a) ? b : a), datos.detectores[0]);

  // 1) La frase principal.
  if (p.magnitud === 0) {
    frase($("veredicto-frase"), [["Sin problema inyectado en " + p.sitio + ": "], ["cualquier alerta aquí es una falsa alarma", true], ["."]]);
  } else if (mejor) {
    frase($("veredicto-frase"), [
      [`Con ${problema} del ${tamano} en ${p.sitio}, las reglas del kit detectan `],
      [`${reglas ? reglas.eventos_detectados : "—"} de ${reglas ? reglas.eventos_totales : "—"}`, true],
      [`; ${nombreMejor} detecta `],
      [`${mejor.eventos_detectados} de ${mejor.eventos_totales}`, true],
      [` con ${numero(mejor.falsas_alarmas_dia)} falsas alarmas al día.`],
    ]);
  } else {
    frase($("veredicto-frase"), [
      [`Con ${problema} del ${tamano} en ${p.sitio}, `],
      ["ningún detector encontró todos los eventos", true],
      [". Prueba con un tamaño mayor o mira el resumen de abajo."],
    ]);
  }

  // Sin problema inyectado: las tarjetas muestran falsas alarmas, no "detectados".
  if (p.magnitud === 0) {
    const menosFalsas = datos.detectores.reduce((a, b) => (b.falsas_alarmas_dia < a.falsas_alarmas_dia ? b : a), datos.detectores[0]);
    $("v-reglas").textContent = reglas ? `${numero(reglas.falsas_alarmas_dia)} /día` : "—";
    $("v-reglas-nota").textContent = "falsas alarmas: no hay nada que detectar";
    $("v-mejor-nombre").textContent = "Menos falsas alarmas";
    $("v-mejor").textContent = `${numero(menosFalsas.falsas_alarmas_dia)} /día`;
    $("v-mejor-nota").textContent = (detectores.get(menosFalsas.id) || { nombre: menosFalsas.id }).nombre;
    $("v-exceso-etiqueta").textContent = esFuga ? "Agua extra" : "Energía extra";
    $("v-exceso").textContent = `0.0 ${datos.unidad}`;
    $("v-exceso-nota").textContent = "no se inyectó ningún problema";
    $("v-coste").textContent = "—";
    $("v-coste-nota").textContent = "sube el tamaño del problema para comparar";
    return;
  }

  // 2) Tarjeta de las reglas del kit.
  if (reglas) {
    $("v-reglas").textContent = `${reglas.eventos_detectados} de ${reglas.eventos_totales}`;
    $("v-reglas-nota").textContent = reglas.eventos_detectados === 0
      ? "no vio ningún evento: umbral fijo igual para todos los sitios"
      : `eventos vistos con umbrales fijos · ${numero(reglas.falsas_alarmas_dia)} falsas alarmas/día`;
  }

  // 3) Tarjeta del mejor detector.
  if (mejor) {
    $("v-mejor-nombre").textContent = `Mejor: ${nombreMejor}`;
    $("v-mejor").textContent = `${mejor.eventos_detectados} de ${mejor.eventos_totales}`;
    $("v-mejor-nota").textContent = `avisa en ${numero(mejor.horas_hasta_alerta)} h · ${numero(mejor.falsas_alarmas_dia)} falsas alarmas/día`;
  } else {
    $("v-mejor-nombre").textContent = "Mejor detector";
    $("v-mejor").textContent = "—";
    $("v-mejor-nota").textContent = "ningún detector encontró todos los eventos";
  }

  // 4) Tarjeta del exceso no detectado (agua o energía).
  $("v-exceso-etiqueta").textContent = esFuga ? "Agua que pasó sin aviso (reglas)" : "Energía extra sin aviso (reglas)";
  animarNumero($("v-exceso"), reglas ? reglas.exceso_no_detectado : null, (v) => `${numero(v)} ${datos.unidad}`);
  $("v-exceso-nota").textContent = mejor
    ? `con ${nombreMejor}: ${numero(mejor.exceso_no_detectado)} ${datos.unidad}`
    : "ningún detector la cortó a tiempo en todos los eventos";

  // 5) Tarjeta del cómputo.
  if (mejor) {
    animarNumero($("v-coste"), coste(mejor), (v) => `${numero(v)} ms`);
    const veces = coste(masCaro) / Math.max(coste(mejor), 0.01);
    const nombreCaro = (detectores.get(masCaro.id) || { nombre: masCaro.id }).nombre;
    $("v-coste-nota").textContent = masCaro.id === mejor.id
      ? "es también el más caro de los cinco"
      : `${nombreCaro}: ${numero(coste(masCaro))} ms (${numero(veces)}× más)`;
  } else {
    $("v-coste").textContent = "—";
    $("v-coste-nota").textContent = "sin detector recomendado en este escenario";
  }

  // Pequeña animación de entrada en las tarjetas.
  for (const tarjeta of document.querySelectorAll(".v-tarjeta")) {
    tarjeta.classList.remove("v-actualizado");
    void tarjeta.offsetWidth;                      // reinicia la animación
    tarjeta.classList.add("v-actualizado");
  }
}

function actualizarEtiquetaMagnitud() {
  $("magnitud-valor").textContent = `${$("magnitud").value} %`;
}

function semillaValida() {
  const campo = $("semilla");
  let valor = Math.round(Number(campo.value));
  if (!Number.isFinite(valor) || valor < 1) valor = 1;
  if (valor > 1000) valor = 1000;
  campo.value = valor;
}

$("magnitud").addEventListener("input", actualizarEtiquetaMagnitud);

$("magnitud").addEventListener("change", cargarEscenario);
$("sitio").addEventListener("change", cargarEscenario);
$("tipo").addEventListener("change", cargarEscenario);
$("semilla").addEventListener("change", () => {
  semillaValida();
  cargarEscenario();
});

$("controles").addEventListener("submit", (evento) => {
  evento.preventDefault();
  semillaValida();
  cargarEscenario();
});


$("modo").textContent = USAR_EJEMPLO
  ? "Modo ejemplo: datos fijos (fuga 10 %, SIM-A, semilla 1); los controles aún no cambian el resultado."
  : "";

actualizarEtiquetaMagnitud();
cargarDetectores().then(() => {
  cargarEscenario();
  cargarResumen();
});