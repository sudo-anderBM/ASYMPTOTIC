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
let ultimoEscenario = null;   // lo usa la demo guiada

async function cargarEscenario() {
  if (controlador) controlador.abort();     
  controlador = new AbortController();

  $("estado").textContent = "Cargando…";
  $("error").hidden = true;

  try {
    const datos = await pedir("scenario", parametros(), controlador.signal);
    ultimoEscenario = datos;
    pintarTabla(datos); 
    pintarGrafica(datos);
    pintarVeredicto(datos); 
    pintarMetricas(datos.metricas);  
    limpiarExplicacion(); 
    cargarBalance();      
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
      // Las reglas corren sin eventos OT, igual que los demás detectores (comparación justa).
      const nombre = d.id === "1_reglas" ? `${d.nombre} (sin eventos OT)` : d.nombre;
      detectores.set(d.id, { ...d, nombre, color: COLORES[d.id] || "#66766e" });
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


// Costo medido de cada detector: mediana de varias repeticiones del barrido
// (results/sweep_*.json). No se usa la medición de una sola corrida de /api/scenario.
function costeDe(d) {
  const lista = resumen.datos && resumen.datos.normal;
  const ref = lista && lista.find((x) => x.id === d.id);
  return ref ? ref.fit_ms + ref.pred_ms : null;
}

function elegirMejor(lista) {
  const completos = lista.filter((d) => d.eventos_totales > 0 && d.eventos_detectados === d.eventos_totales);
  if (completos.length === 0) return null;
  completos.sort((a, b) =>
    (a.falsas_alarmas_dia - b.falsas_alarmas_dia) ||
    (a.exceso_no_detectado - b.exceso_no_detectado) ||
    ((costeDe(a) ?? 0) - (costeDe(b) ?? 0)));
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
      celda(numero(costeDe(d)), true),
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
  // Las dos líneas van dentro de un grupo recortado que se "revela" de izquierda a derecha.
  const recorte = svg("clipPath", { id: "revelar-lineas" });
  const ventana = svg("rect", { x: 0, y: 0, width: SIN_ANIMACION ? 720 : G.izq, height: altoTotal });
  recorte.append(ventana);
  const defs = svg("defs");
  defs.append(recorte);
  lienzo.append(defs);
  const lineas = svg("g", { "clip-path": "url(#revelar-lineas)" });
  lineas.append(svg("path", { d: trazo("esperado"), class: "det-esperado" }));
  lineas.append(svg("path", { d: trazo("observado"), class: "det-observado" }));
  lienzo.append(lineas);
  revelar(ventana);

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
      if (!SIN_ANIMACION) {
        marca.classList.add("aparece");
        marca.style.animationDelay = `${650 + i * 110}ms`;   // cada carril aparece un poco después
      }
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
    "Las franjas marcan dónde se inyectó el problema; debajo, cuándo avisó cada detector. Pasa el mouse sobre la gráfica para ver cada hora.";
  pintarLeyendaGrafica();
  prepararTooltip(lienzo, datos, x, y, t0, t1);
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

// ---------- Mejora 3 · Animación y tooltip de la gráfica ----------

// Ensancha el rectángulo de recorte hasta mostrar las líneas completas (~0.9 s).
function revelar(ventana) {
  if (SIN_ANIMACION) return;
  const inicio = performance.now();
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / 900);
    const suave = 1 - Math.pow(1 - t, 3);
    ventana.setAttribute("width", G.izq + suave * (720 - G.izq));
    if (t < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// Al pasar el mouse por la zona de las líneas: guía vertical, dos puntos y una cajita con los datos de esa hora.
function prepararTooltip(lienzo, datos, x, y, t0, t1) {
  const serie = datos.serie;
  const tip = $("grafica-tooltip");
  tip.hidden = true;

  // Qué detectores avisaron en cada hora.
  const alertasPorHora = new Map();
  for (const det of datos.detectores) {
    const nombre = (detectores.get(det.id) || { nombre: det.id }).nombre;
    for (const ts of det.alertas) {
      if (!alertasPorHora.has(ts)) alertasPorHora.set(ts, []);
      alertasPorHora.get(ts).push(nombre);
    }
  }
  // ¿La hora cae dentro de un problema inyectado?
  const enProblema = (ms) => datos.eventos_reales.some((ev) => ms >= Date.parse(ev.inicio) && ms <= Date.parse(ev.fin));

  const guia = svg("line", { class: "det-guia", x1: 0, x2: 0, y1: G.arriba, y2: G.abajo, visibility: "hidden" });
  const puntoEsp = svg("circle", { r: 3.5, class: "det-punto-esp", visibility: "hidden" });
  const puntoObs = svg("circle", { r: 4.5, class: "det-punto-obs", visibility: "hidden" });
  const zona = svg("rect", { x: G.izq, y: G.arriba, width: G.der - G.izq, height: G.abajo - G.arriba, class: "det-zona" });
  lienzo.append(guia, puntoEsp, puntoObs, zona);

  const fila = (etiqueta, valor) => {
    const p = document.createElement("p");
    const e = document.createElement("span");
    e.textContent = etiqueta;
    const v = document.createElement("strong");
    v.textContent = valor;
    p.append(e, v);
    return p;
  };

  const ocultar = () => {
    tip.hidden = true;
    for (const el of [guia, puntoObs, puntoEsp]) el.setAttribute("visibility", "hidden");
  };

  const mover = (evento) => {
    const caja = lienzo.getBoundingClientRect();
    const vb = lienzo.viewBox.baseVal;
    const sx = ((evento.clientX - caja.left) * vb.width) / caja.width;      // posición en unidades del dibujo
    const ms = t0 + ((sx - G.izq) / (G.der - G.izq)) * (t1 - t0);
    const i = Math.max(0, Math.min(serie.length - 1, Math.floor((ms - t0) / HORA_MS)));
    const punto = serie[i];
    const inicioHora = Date.parse(punto.timestamp);
    const px = x(inicioHora + HORA_MS / 2);

    guia.setAttribute("x1", px);
    guia.setAttribute("x2", px);
    guia.setAttribute("visibility", "visible");
    for (const [circulo, valor] of [[puntoObs, punto.observado], [puntoEsp, punto.esperado]]) {
      if (valor === null || valor === undefined) { circulo.setAttribute("visibility", "hidden"); continue; }
      circulo.setAttribute("cx", px);
      circulo.setAttribute("cy", y(valor));
      circulo.setAttribute("visibility", "visible");
    }

    // Contenido de la cajita (siempre con textContent).
    tip.replaceChildren();
    const titulo = document.createElement("p");
    titulo.className = "det-tooltip-titulo";
    titulo.textContent = `${formatoHora.format(new Date(inicioHora))} UTC${enProblema(inicioHora) ? " · problema inyectado" : ""}`;
    tip.append(titulo);
    tip.append(fila("Observado", `${numero(punto.observado)} ${datos.unidad}`));
    tip.append(fila("Esperado", `${numero(punto.esperado)} ${datos.unidad}`));
    if (punto.esperado) {
      const dif = ((punto.observado - punto.esperado) / punto.esperado) * 100;
      tip.append(fila("Diferencia", `${dif > 0 ? "+" : ""}${numero(dif)} %`));
    }
    const quienes = alertasPorHora.get(punto.timestamp);
    tip.append(fila("Alertas", quienes ? quienes.join(", ") : "ninguna"));

    // Posición: a la derecha del punto, o a la izquierda si estamos cerca del borde.
    const escalaX = caja.width / vb.width;
    const escalaY = caja.height / vb.height;
    tip.style.left = `${px * escalaX}px`;
    tip.style.top = `${y(punto.observado ?? punto.esperado ?? 0) * escalaY}px`;
    tip.classList.toggle("izq", px > 470);
    tip.hidden = false;
  };

  zona.addEventListener("pointermove", mover);
  zona.addEventListener("pointerdown", mover);      // en pantallas táctiles, al tocar
  zona.addEventListener("pointerleave", ocultar);
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
  // Con el barrido cargado, el costo de la tabla y del veredicto pasa a las medianas medidas.
  if (ultimoEscenario) {
    pintarTabla(ultimoEscenario);
    pintarVeredicto(ultimoEscenario);
  }
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

function repeticiones(m) {
  if (m.reps) return m.reps;
  const encontrado = /(\d+) repeticiones/.exec(m.nota || "");
  return encontrado ? encontrado[1] : "varias";
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
    : `Costo de cada detector: mediana de ${repeticiones(m)} repeticiones, con aprender y revisar medidos por separado y sin contar la lectura de datos. ` +
      `Equipo: ${m.equipo} · Python ${m.python}${m.sklearn ? ` · scikit-learn ${m.sklearn}` : ""} · generado ${m.generado}. Datos simulados.`;
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


const SIN_ANIMACION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function animarNumero(elemento, valor, formatear) {
  if (valor === null || valor === undefined || SIN_ANIMACION) {
    elemento.textContent = valor === null || valor === undefined ? "—" : formatear(valor);
    return;
  }
  const inicio = performance.now();
  const duracion = 600;
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / duracion);
    const suave = 1 - Math.pow(1 - t, 3);            
    elemento.textContent = formatear(valor * suave);
    if (t < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

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
  const coste = costeDe;
  const masCaro = datos.detectores.reduce((a, b) => ((coste(b) ?? -1) > (coste(a) ?? -1) ? b : a), datos.detectores[0]);

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


  if (reglas) {
    $("v-reglas").textContent = `${reglas.eventos_detectados} de ${reglas.eventos_totales}`;
    $("v-reglas-nota").textContent = reglas.eventos_detectados === 0
      ? "no vio ningún evento: umbral fijo igual para todos los sitios"
      : `eventos vistos con umbrales fijos · ${numero(reglas.falsas_alarmas_dia)} falsas alarmas/día`;
  }

  
  if (mejor) {
    $("v-mejor-nombre").textContent = `Mejor: ${nombreMejor}`;
    $("v-mejor").textContent = `${mejor.eventos_detectados} de ${mejor.eventos_totales}`;
    $("v-mejor-nota").textContent = `avisa en ${numero(mejor.horas_hasta_alerta)} h · ${numero(mejor.falsas_alarmas_dia)} falsas alarmas/día`;
  } else {
    $("v-mejor-nombre").textContent = "Mejor detector";
    $("v-mejor").textContent = "—";
    $("v-mejor-nota").textContent = "ningún detector encontró todos los eventos";
  }

  
  $("v-exceso-etiqueta").textContent = esFuga ? "Agua que pasó sin aviso (reglas)" : "Energía extra sin aviso (reglas)";
  animarNumero($("v-exceso"), reglas ? reglas.exceso_no_detectado : null, (v) => `${numero(v)} ${datos.unidad}`);
  $("v-exceso-nota").textContent = mejor
    ? `con ${nombreMejor}: ${numero(mejor.exceso_no_detectado)} ${datos.unidad}`
    : "ningún detector la cortó a tiempo en todos los eventos";

  
  if (mejor && coste(mejor) === null) {
    $("v-coste").textContent = "—";
    $("v-coste-nota").textContent = "cargando las mediciones del barrido…";
  } else if (mejor) {
    animarNumero($("v-coste"), coste(mejor), (v) => `${numero(v)} ms`);
    const veces = coste(masCaro) / Math.max(coste(mejor), 0.01);
    const nombreCaro = (detectores.get(masCaro.id) || { nombre: masCaro.id }).nombre;
    $("v-coste-nota").textContent = masCaro.id === mejor.id
      ? "es también el más caro de los cinco"
      : `${nombreCaro}: ${numero(coste(masCaro))} ms (${numero(veces)}× más) · mediana de repeticiones`;
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
  for (const boton of document.querySelectorAll(".atajo")) {
    boton.classList.toggle("activo", boton.dataset.magnitud === $("magnitud").value);
  }
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


for (const boton of document.querySelectorAll(".atajo")) {
  boton.addEventListener("click", () => {
    $("magnitud").value = boton.dataset.magnitud;
    actualizarEtiquetaMagnitud();
    cargarEscenario();
  });
}

async function fijarEscenario({ sitio, tipo, magnitud, semilla }) {
  const cambiaTipo = tipo !== undefined && tipo !== $("tipo").value;
  if (sitio !== undefined) $("sitio").value = sitio;
  if (tipo !== undefined) $("tipo").value = tipo;
  if (magnitud !== undefined) $("magnitud").value = magnitud;
  if (semilla !== undefined) $("semilla").value = semilla;
  actualizarEtiquetaMagnitud();
  if (cambiaTipo) cargarResumen();
  await cargarEscenario();
}

const demo = { activa: false, turno: 0 };
const PASOS_DEMO = 6;

function esperar(ms) {
  const turno = demo.turno;
  return new Promise((resolver, rechazar) => {
    setTimeout(() => (turno === demo.turno && demo.activa ? resolver() : rechazar(new Error("demo-detenida"))), ms);
  });
}

function desplazarA(elemento) {
  elemento.scrollIntoView({ behavior: SIN_ANIMACION ? "auto" : "smooth", block: "start" });
}

function subtitulo(paso, texto) {
  $("demo-paso").textContent = `Paso ${paso} de ${PASOS_DEMO}`;
  $("demo-avance").style.width = `${(paso / PASOS_DEMO) * 100}%`;
  $("demo-texto").textContent = texto;
}

function minuscula(texto) {
  return texto ? texto[0].toLowerCase() + texto.slice(1) : texto;
}

function nombreDetector(id) {
  return (detectores.get(id) || { nombre: id }).nombre;
}

async function reproducirDemo() {
  if (demo.activa) return;
  demo.activa = true;
  demo.turno += 1;
  document.body.classList.add("demo-en-curso");
  $("demo-barra").hidden = false;
  $("demo-iniciar").disabled = true;
  const de = (d) => `${d.eventos_detectados} de ${d.eventos_totales}`;

  try {
   
    subtitulo(1, "Operación normal en SIM-A: la línea real (sólida) sigue a la esperada (punteada). Todavía no hay ninguna fuga.");
    await fijarEscenario({ sitio: "SIM-A", tipo: "fuga", magnitud: 0, semilla: 1 });
    desplazarA($("veredicto"));
    await esperar(6500);

   
    await fijarEscenario({ magnitud: 10 });
    let e = ultimoEscenario;
    const reglas = e.detectores.find((d) => d.id === "1_reglas");
    const idMejor = elegirMejor(e.detectores);
    const mejor = e.detectores.find((d) => d.id === idMejor);
    subtitulo(2, mejor
      ? `Inyectamos una fuga del 10 % (franjas naranjas). Las reglas del kit detectan ${de(reglas)}; ${nombreDetector(mejor.id)} detecta ${de(mejor)} y deja pasar ${numero(mejor.exceso_no_detectado)} ${e.unidad} en lugar de ${numero(reglas.exceso_no_detectado)} ${e.unidad}.`
      : `Inyectamos una fuga del 10 % (franjas naranjas). Las reglas del kit detectan ${de(reglas)}, y ningún detector ve todos los eventos.`);
    desplazarA($("grafica-titulo"));    
    await esperar(8500);

    
    const marca = mejor && document.querySelector(`.det-alerta[data-detector="${mejor.id}"]`);
    if (marca) {
      desplazarA($("grafica-titulo"));
      await mostrarExplicacion(marca);
      subtitulo(3, `Qué dice el modelo residual en esa hora: ${$("exp-texto").textContent}`);
    } else {
      subtitulo(3, "Cada alerta se puede abrir para ver lo observado frente a lo esperado por el modelo.");
    }
    await esperar(8500);

    await fijarEscenario({ magnitud: 30 });
    e = ultimoEscenario;
    const completos = e.detectores.filter((d) => d.eventos_totales > 0 && d.eventos_detectados === d.eventos_totales).length;
    const iforest = e.detectores.find((d) => d.id === "2_isolation_forest");
    const mejor30 = e.detectores.find((d) => d.id === elegirMejor(e.detectores));
    const coste = costeDe;
    let texto4 = `Con una fuga del 30 %, ${completos} de ${e.detectores.length} detectores ven todos los eventos.`;
    if (iforest && mejor30 && mejor30.id !== iforest.id && coste(iforest) !== null && coste(mejor30) !== null) {
      texto4 += ` IsolationForest da ${numero(iforest.falsas_alarmas_dia)} falsas alarmas al día y cuesta ${numero(coste(iforest) / Math.max(coste(mejor30), 0.01))}× más tiempo de cómputo que ${nombreDetector(mejor30.id)} (mediana de repeticiones).`;
    }
    subtitulo(4, texto4);
    desplazarA($("veredicto"));
    await esperar(8500);

    
    desplazarA($("resumen"));
    document.querySelector('[data-version="normal"]').click();
    await esperar(900);
    subtitulo(5, `Con ${resumen.datos ? resumen.datos.meta.eventos_por_punto : "muchos"} eventos por punto, ${minuscula($("recomendacion").textContent)}`);
    await esperar(8000);
    document.querySelector('[data-version="dificil"]').click();
    subtitulo(5, `Con datos difíciles (ruido y relación no lineal): ${minuscula($("recomendacion").textContent)}`);
    await esperar(8000);

    await fijarEscenario({ sitio: "SIM-B", tipo: "fuga", magnitud: 10, semilla: 1 });
    $("dias").value = 7;
    $("dias-valor").textContent = "7 días";
    await cargarBalance();
    desplazarA($("balance"));
    const b = ultimoBalance;
    if (b) {
      const c = b.costo_detector_anual;
      const evita = b.beneficio.unidad === "L"
        ? `${cifra(b.beneficio.evitado)} L de agua`
        : `${cifra(b.beneficio.kwh_evitados)} kWh`;
      subtitulo(6, `Balance neto: si una fuga del 10 % en SIM-B tardara ${b.supuestos.dias_sin_detector} días en descubrirse, se perderían ${evita}. ` +
        `Suponiendo ${b.supuestos.watts} W (no medidos), tener el detector encendido todo un año cuesta unos ${cifra(c.g_co2e)} g de CO₂e. ` +
        (b.balance_positivo ? "Evita mucho más de lo que gasta." : "En este caso no compensa."));
    } else {
      subtitulo(6, "Balance neto: comparamos lo que cuesta el detector al año con lo que evita perder.");
    }
    await esperar(10000);

    $("demo-texto").textContent = "Fin de la demo. Ahora puedes mover los controles.";
    await esperar(3500);
    terminarDemo();
  } catch (error) {
    if (error.message !== "demo-detenida") {
      $("demo-texto").textContent = `La demo se detuvo: ${error.message}`;
    }
  }
}

function terminarDemo() {
  demo.activa = false;
  demo.turno += 1;               
  document.body.classList.remove("demo-en-curso");
  $("demo-barra").hidden = true;
  $("demo-iniciar").disabled = false;
}

$("demo-iniciar").addEventListener("click", reproducirDemo);
$("demo-detener").addEventListener("click", terminarDemo);
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && demo.activa) terminarDemo();
});
for (const tipoEvento of ["pointerdown", "keydown"]) {
  $("controles").addEventListener(tipoEvento, (evento) => {
    if (demo.activa && evento.isTrusted) terminarDemo();
  });
}


$("modo").textContent = USAR_EJEMPLO
  ? "Modo ejemplo: datos fijos (fuga 10 %, SIM-A, semilla 1); los controles aún no cambian el resultado."
  : "";

actualizarEtiquetaMagnitud();
cargarDetectores().then(() => {
  cargarEscenario();
  cargarResumen();
});

// Tarjetas de métricas 

const METRICAS = [
  { clave: "pue", nombre: "PUE", unidad: "", ayuda: "Energía total ÷ energía de los servidores. Lo ideal es 1." },
  { clave: "wue_l_kwh", nombre: "WUE pedagógica del kit", unidad: "L/kWh", ayuda: "Agua tomada en el sitio por kWh de servidores. No incluye el agua de generar la electricidad." },
  { clave: "cue_kg_kwh", nombre: "CUE", unidad: "kg CO₂e/kWh", ayuda: "CO₂e por cada kWh de los servidores (PUE × factor de la red)." },
];

const formato3 = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

function valorMetrica(valor) {
  return valor === null || valor === undefined ? "—" : formato3.format(valor);
}

function pintarMetricas(m) {
  const seccion = $("metricas");
  if (!m || !m.sin_problema || !m.con_problema) {
    seccion.hidden = true;          // la API todavía no manda métricas
    return;
  }

  const contenedor = $("m-tarjetas");
  contenedor.replaceChildren();

  for (const metrica of METRICAS) {
    const antes = m.sin_problema[metrica.clave];
    const despues = m.con_problema[metrica.clave];

    const tarjeta = document.createElement("article");
    tarjeta.className = "m-tarjeta";

    const nombre = document.createElement("p");
    nombre.className = "m-nombre";
    nombre.textContent = metrica.nombre;

    const valores = document.createElement("p");
    valores.className = "m-valores";
    const vAntes = document.createElement("span");
    vAntes.className = "m-antes";
    vAntes.textContent = valorMetrica(antes);
    const flecha = document.createElement("span");
    flecha.className = "m-flecha";
    flecha.setAttribute("aria-hidden", "true");
    flecha.textContent = "→";
    const vDespues = document.createElement("strong");
    vDespues.textContent = valorMetrica(despues);
    const unidad = document.createElement("span");
    unidad.className = "m-unidad";
    unidad.textContent = metrica.unidad;
    valores.append(vAntes, flecha, vDespues, unidad);

    const cambio = document.createElement("p");
    cambio.className = "m-cambio";
    if (!antes || despues === null || despues === undefined) {
      cambio.textContent = "—";
    } else {
      const pct = ((despues - antes) / antes) * 100;
      if (Math.abs(pct) < 0.05) {
        cambio.textContent = "Sin cambio";
      } else {
        cambio.textContent = `${pct > 0 ? "+" : ""}${numero(pct)} % con el problema`;
        cambio.classList.add(pct > 0 ? "sube" : "baja");
      }
    }

    const ayuda = document.createElement("p");
    ayuda.className = "m-ayuda";
    ayuda.textContent = metrica.ayuda;

    tarjeta.append(nombre, valores, cambio, ayuda);
    contenedor.append(tarjeta);
  }

  $("metricas-nota").textContent =
    `CUE = PUE × ${formato3.format(m.factor_kg_co2e_kwh)} kg CO₂e/kWh (factor de la red eléctrica de México). ` +
    "Calculado con las 96 horas de evaluación del sitio elegido.";
  seccion.hidden = false;
}

// Panel Balance neto

const BALANCE_DE_EJEMPLO = false;

const SUPUESTOS = { watts: 30, factor: 0.438, l_por_kwh: 1.2 };

const formatoSig = new Intl.NumberFormat("es-MX", { maximumSignificantDigits: 2 });
const formatoEntero = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 0 });

function cifra(valor) {
  if (valor === null || valor === undefined) return "—";
  if (valor === 0) return "0";
  if (Math.abs(valor) < 1) return formatoSig.format(valor);
  if (Math.abs(valor) < 100) return numero(valor);
  return formatoEntero.format(valor);
}

function filaDato(etiqueta, valor) {
  const fila = document.createElement("div");
  const dt = document.createElement("dt");
  dt.textContent = etiqueta;
  const dd = document.createElement("dd");
  dd.textContent = valor;
  fila.append(dt, dd);
  return fila;
}

let controladorBalance = null;

async function cargarBalance() {
  if (controladorBalance) controladorBalance.abort();
  controladorBalance = new AbortController();
  $("balance-error").hidden = true;

  const params = { ...parametros(), dias: Number($("dias").value), ...SUPUESTOS };
  const url = BALANCE_DE_EJEMPLO
    ? "/static/mock/balance.json"
    : `/api/balance?${new URLSearchParams(params)}`;

  try {
    const respuesta = await fetch(url, { signal: controladorBalance.signal, cache: "no-store" });
    if (!respuesta.ok) {
      let mensaje = `No se pudo calcular el balance (HTTP ${respuesta.status}).`;
      try {
        const error = await respuesta.json();
        if (typeof error.detail === "string") mensaje = error.detail;
      } catch (_) {}
      throw new Error(mensaje);
    }
    pintarBalance(await respuesta.json());
  } catch (error) {
    if (error.name === "AbortError") return;
    $("balance-error").textContent = error.message;
    $("balance-error").hidden = false;
  }
}

let ultimoBalance = null;   

function pintarBalance(b) {
  ultimoBalance = b;
  const costo = b.costo_detector_anual;
  const ben = b.beneficio;

  $("balance-costo").replaceChildren(
    filaDato("Tiempo de CPU", `${cifra(costo.segundos_cpu)} s`),
    filaDato("Energía", `${cifra(costo.kwh)} kWh`),
    filaDato("Emisiones", `${cifra(costo.g_co2e)} g CO₂e`),
  );

  if (ben.unidad === "L") {
    $("balance-evitado").textContent = `${cifra(ben.evitado)} L de agua`;
    $("balance-evita").replaceChildren(
      filaDato("Pérdida por hora con la fuga", `${cifra(ben.perdida_por_hora)} L`),
      filaDato("Días sin descubrirla", `${b.supuestos.dias_sin_detector}`),
    );
  } else {
    $("balance-evitado").textContent = `${cifra(ben.kwh_evitados)} kWh`;
    $("balance-evita").replaceChildren(
      filaDato("Energía extra por hora", `${cifra(ben.perdida_por_hora)} kWh`),
      filaDato("Emisiones evitadas", `${cifra(ben.kg_co2e_evitados)} kg CO₂e`),
      filaDato("Días sin descubrirla", `${b.supuestos.dias_sin_detector}`),
    );
  }

  const sello = $("balance-sello");
  if (b.balance_positivo === null || b.balance_positivo === undefined) {
    sello.textContent = "Sin problema que evitar";
    sello.className = "balance-sello neutro";
  } else {
    sello.textContent = b.balance_positivo ? "✓ Balance positivo" : "Balance negativo";
    sello.className = `balance-sello ${b.balance_positivo ? "positivo" : "negativo"}`;
  }
  sello.hidden = false;

  const s = b.supuestos;
  $("balance-supuestos").textContent =
    `Supuestos (no medidos): potencia supuesta de ${s.watts} W, ${s.revisiones_por_anio} revisiones y ${s.reentrenos_por_anio} reentrenamientos al año, ` +
    `factor de emisión ${s.factor_kg_co2e_kwh} kg CO₂e/kWh (${s.factor_contexto || "red eléctrica de México, aviso 2023"}). ` +
    "Medido: solo el tiempo de cómputo. No incluye fabricación, red ni agua." +
    (BALANCE_DE_EJEMPLO ? " (Datos de ejemplo: aún no cambian con los controles.)" : "");
}

$("dias").addEventListener("input", () => {
  const d = Number($("dias").value);
  $("dias-valor").textContent = `${d} ${d === 1 ? "día" : "días"}`;
});
$("dias").addEventListener("change", cargarBalance);