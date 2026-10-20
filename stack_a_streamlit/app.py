"""Panel didáctico local CIFox. Solo lee el conjunto de datos simulado incluido."""
from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st

# Permite ejecutar desde la raíz del kit o desde cualquier otra carpeta.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common.cifox import flagged, load_data, metrics

st.set_page_config(page_title="CIFox | Datos simulados", page_icon="🦊", layout="wide")
st.title("CIFox · Energía y agua")
st.warning("DATOS SIMULADOS · Demostración educativa. No representa instalaciones reales.")
st.caption(
    "Stack A: Python + pandas + Streamlit. Lectura local de un CSV; "
    "sin cuentas, cargas de archivos ni conexión a equipos."
)

try:
    data = load_data(ROOT / "data" / "operaciones_simuladas.csv").copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
except (OSError, ValueError, KeyError) as exc:
    st.error(f"No se pudo leer el CSV de demostración: {exc}")
    st.info("Conserva las carpetas common y data junto a stack_a_streamlit y vuelve a ejecutar.")
    st.stop()

if data.empty:
    st.info("El CSV no contiene filas. Revisa los datos simulados incluidos en el kit.")
    st.stop()

st.sidebar.header("Filtros de la simulación")
choices = sorted(data["cooling_type"].unique().tolist())
selected_cooling = st.sidebar.multiselect(
    "Tipo de refrigeración", choices, default=choices, key="cooling",
    help="Cada tipo corresponde a un sitio ficticio. No es un ensayo causal entre tecnologías."
)
first_date = data["timestamp"].min().date()
last_date = data["timestamp"].max().date()
start_date = st.sidebar.date_input(
    "Desde (UTC, incluido)", first_date, min_value=first_date, max_value=last_date,
    key="start_date", format="DD/MM/YYYY"
)
end_date = st.sidebar.date_input(
    "Hasta (UTC, incluido)", last_date, min_value=first_date, max_value=last_date,
    key="end_date", format="DD/MM/YYYY"
)
st.sidebar.caption("Las fechas incluyen todas las horas del día seleccionado en UTC.")
st.sidebar.info("Para empezar: cambia un filtro y observa cómo se recalculan los indicadores.")

if start_date > end_date:
    st.error("La fecha inicial debe ser anterior o igual a la fecha final.")
    st.stop()

mask = (
    data["cooling_type"].isin(selected_cooling)
    & data["timestamp"].dt.date.between(start_date, end_date)
)
filtered = data.loc[mask].copy()
if filtered.empty:
    st.info("No hay datos para estos filtros. Selecciona al menos un tipo de refrigeración.")
    st.stop()

summary = metrics(filtered)
flagged_data = flagged(filtered)

def number(value, digits=2):
    """Formato español sin depender de la configuración regional del equipo."""
    if value is None or pd.isna(value):
        return "No disponible"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")

st.subheader("Resumen del período simulado")
st.caption(
    f"{start_date:%d/%m/%Y}–{end_date:%d/%m/%Y} UTC · "
    f"{len(filtered)} registros horarios · {filtered['site_id'].nunique()} sitio(s) ficticio(s)"
)
a, b, c = st.columns(3)
a.metric("PUE simplificado", number(summary["pue"]), help="Suma energía total / suma energía TI. Adimensional.")
b.metric("WUE local simplificado", f"{number(summary['wue_l_kwh'])} L/kWh TI", help="Suma agua local / suma energía TI. Este CSV usa extracción de agua local.")
c.metric("Registros con alerta por reglas", str(summary["rule_alerts"]), help="Un registro se cuenta una sola vez aunque active varias reglas didácticas.")
a, b, c = st.columns(3)
a.metric("Energía TI", f"{number(summary['energy_it_kwh'], 0)} kWh")
b.metric("Energía total", f"{number(summary['energy_total_kwh'], 0)} kWh")
c.metric("Agua local extraída", f"{number(summary['water_l'], 0)} L")
st.info(
    "PUE = Σ energía total ÷ Σ energía TI. WUE local simplificado = Σ agua local ÷ Σ energía TI. "
    "Los cocientes se calculan sobre las sumas del filtro; no se promedian los cocientes de cada fila."
)

st.subheader("Evolución horaria")
st.caption("Las series suman los sitios seleccionados en cada hora. Energía y agua tienen ejes separados.")
hourly = filtered.groupby("timestamp", as_index=True)[
    ["energy_it_kwh", "energy_total_kwh", "water_l"]
].sum().sort_index()
chart_data = hourly.reset_index()
chart_data["hour_label"] = chart_data["timestamp"].dt.strftime("%d/%m/%Y %H:%M UTC")
utc_x = alt.X("timestamp:T", title="Fecha y hora (UTC)", scale=alt.Scale(type="utc"))
energy_chart_data = chart_data.melt(
    id_vars=["timestamp", "hour_label"], value_vars=["energy_it_kwh", "energy_total_kwh"],
    var_name="series", value_name="energy_kwh"
)
energy_chart_data["series"] = energy_chart_data["series"].map({
    "energy_it_kwh": "Energía TI", "energy_total_kwh": "Energía total"
})
left, right = st.columns(2)
with left:
    st.markdown("#### Energía por hora (kWh)")
    energy_chart = alt.Chart(energy_chart_data).mark_line().encode(
        x=utc_x, y=alt.Y("energy_kwh:Q", title="Energía (kWh)", scale=alt.Scale(zero=True)),
        color=alt.Color("series:N", title="Serie", scale=alt.Scale(range=["#1673B1", "#7D3C98"])),
        strokeDash=alt.StrokeDash("series:N", title="Serie"),
        tooltip=[alt.Tooltip("hour_label:N", title="Hora"), alt.Tooltip("series:N", title="Serie"),
                 alt.Tooltip("energy_kwh:Q", title="kWh", format=".2f")]
    ).properties(height=270)
    st.altair_chart(energy_chart, width="stretch")
with right:
    st.markdown("#### Agua local por hora (L)")
    water_chart = alt.Chart(chart_data).mark_line(color="#147D64").encode(
        x=utc_x, y=alt.Y("water_l:Q", title="Agua local (L)", scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip("hour_label:N", title="Hora"), alt.Tooltip("water_l:Q", title="Litros", format=".2f")]
    ).properties(height=270)
    st.altair_chart(water_chart, width="stretch")

with st.expander("Ver los valores de las gráficas en una tabla"):
    st.dataframe(hourly.reset_index().rename(columns={
        "timestamp": "Fecha y hora (UTC)", "energy_it_kwh": "Energía TI (kWh)",
        "energy_total_kwh": "Energía total (kWh)", "water_l": "Agua local (L)"
    }), hide_index=True, width="stretch")

st.subheader("Revisión de reglas didácticas")
st.caption(
    "Son reglas deterministas del módulo common/cifox.py, no un modelo de IA ni un sistema "
    "de diagnóstico. Una alerta pide revisión; no demuestra una avería o un ataque."
)
if int(summary["rule_alerts"]) > 0:
    st.warning(f"{summary['rule_alerts']} registro(s) del filtro activan una o más reglas de ejemplo.")
else:
    st.success("Ningún registro del filtro activa las reglas de ejemplo.")
alert_hourly = flagged_data.groupby("timestamp")["rule_alert"].sum().rename("alerts").reset_index()
alert_hourly["hour_label"] = alert_hourly["timestamp"].dt.strftime("%d/%m/%Y %H:%M UTC")
alert_chart = alt.Chart(alert_hourly).mark_bar(color="#A45212").encode(
    x=utc_x, y=alt.Y("alerts:Q", title="Registros con alerta", axis=alt.Axis(tickMinStep=1)),
    tooltip=[alt.Tooltip("hour_label:N", title="Hora"), alt.Tooltip("alerts:Q", title="Registros")]
).properties(height=180)
st.altair_chart(alert_chart, width="stretch")
only_alerts = st.checkbox("Mostrar solo registros con alerta", value=True, key="only_alerts")
review = flagged_data.loc[flagged_data["rule_alert"]] if only_alerts else flagged_data
columns = ["timestamp", "site_id", "cooling_type", "energy_it_kwh", "energy_total_kwh", "water_l", "rule_alert", "rule_reason"]
labels = {
    "timestamp": "Fecha y hora (UTC)", "site_id": "Sitio ficticio", "cooling_type": "Refrigeración",
    "energy_it_kwh": "Energía TI (kWh)", "energy_total_kwh": "Energía total (kWh)",
    "water_l": "Agua local (L)", "rule_alert": "Alerta por reglas", "rule_reason": "Motivo de la regla"
}
if review.empty:
    st.caption("No hay filas con alerta. Desmarca la opción para inspeccionar todas las filas filtradas.")
else:
    st.dataframe(review[columns].rename(columns=labels), hide_index=True, width="stretch")

with st.expander("Qué significan los indicadores y cómo aprender con este panel", expanded=False):
    st.markdown(
        "- **TI**: equipos de tecnología de la información.\n"
        "- **PUE simplificado**: relación entre energía total y energía TI dentro del mismo período y límite. "
        "No mide por sí solo la huella ambiental ni el trabajo útil realizado.\n"
        "- **WUE local simplificado**: litros de agua local extraída por kWh TI en esta simulación. "
        "No incluye agua indirecta de la electricidad y no equivale a una evaluación certificada de consumo hídrico.\n"
        "- **Comparación**: cambiar refrigeración selecciona distintos sitios ficticios. "
        "También varían su carga y condiciones; no permite concluir que una tecnología sea mejor.\n"
        "- **Reglas**: consulta common/cifox.py para ver condiciones y umbrales. Son ejemplos, "
        "no límites normativos ni límites operativos aprobados.\n"
        "- **Práctica**: filtra un día, calcula a mano las sumas y comprueba ambos cocientes. "
        "Después selecciona otro sitio y compara el contexto."
    )
st.divider()
st.caption(
    "DATOS SIMULADOS · Prototipo educativo, no validación de CIFox ni evidencia comercial. "
    "No controla infraestructura, no cambia consignas, no toma decisiones operativas y no se conecta a sistemas OT."
)
