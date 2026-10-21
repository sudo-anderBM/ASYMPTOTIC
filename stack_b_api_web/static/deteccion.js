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
    console.log("scenario:", datos);           
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