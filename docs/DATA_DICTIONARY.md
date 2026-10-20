# Diccionario · DATOS TOTALMENTE SIMULADOS

No contiene mediciones, instalaciones, clientes ni incidentes reales. Generador original: `tools/generate_data.py`, semilla `22102026`. CSV UTF-8, campos separados por coma y decimales por punto (`.`); 504 filas: 168 horas × 3 sitios ficticios. Inicio 2026-10-12 00:00 UTC; fin 2026-10-18 23:00 UTC. Cada fila representa el intervalo de una hora que comienza en timestamp. No se debe sumar dos veces un mismo sitio/hora.

| Campo | Unidad / valores | Significado y límites |
|---|---|---|
| timestamp | ISO8601 UTC | Inicio de intervalo horario |
| site_id | SIM-A/B/C | Instalación ficticia; no entidad real |
| cooling_type | aire / evaporativa / liquida | Etiqueta simplificada, no diseño físico de ingeniería |
| energy_it_kwh | kWh / intervalo | Energía atribuida al equipo IT, estrictamente positiva |
| energy_total_kwh | kWh / intervalo | Energía total del mismo sitio/intervalo, incluye IT y auxiliares |
| water_l | L / intervalo | Agua captada in situ para operación; no huella hídrica de electricidad ni fabricación, ni consumo neto tras retornos |
| load_pct | % | Carga sintética; no potencia ni utilización medida |
| outdoor_temp_c | °C | Temperatura ambiente sintética |
| inlet_temp_c | °C | Temperatura de entrada ilustrativa; sin especificación de equipo |
| ot_event | normal / login_fallido / cambio_config_no_autorizado | Evento ficticio resumido, sin IP, credenciales ni herramientas ofensivas |
| scenario | base / ineficiencia / fuga_agua / evento_ot | Etiqueta de generación, NO entrada de detector |
| simulated_anomaly | 0/1 | Verdad sintética para evaluación, NO entrada de detector |
| split | referencia / evaluacion | Primeras 72 h por sitio (216 filas) / siguientes 96 h (288 filas) |
| is_simulated | True | Declaración obligatoria del carácter simulado |

## Baseline y cautelas
Hay 21 filas etiquetadas anómalas: 8 de ineficiencia, 8 de agua y 5 de OT. No hay anomalías inyectadas en referencia. Las ventanas de escenarios son deliberadamente sencillas. Regenerar con otra semilla modifica ruido, no ventanas; no constituye un conjunto oculto independiente.

Los coeficientes y relaciones son decisiones didácticas, no datos de fabricante ni evidencias de que una tecnología sea superior. La serie no reproduce dinámica térmica, hidráulica ni seguridad OT real. Debatir qué variables faltan es parte del ejercicio.
