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
cargarDetectores().then(cargarEscenario);