"use strict";

const USAR_EJEMPLO = true;

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

// null o undefined se muestran como "—"; los números con 1 decimal.
function numero(valor) {
  return valor === null || valor === undefined ? "—" : formato1.format(valor);
}

// El mejor: detectó todos los eventos; luego menos falsas alarmas,
// luego menos exceso no detectado (agua o energía perdida) y, al final, menos coste.
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