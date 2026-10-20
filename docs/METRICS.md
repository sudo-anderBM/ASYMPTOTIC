# Métricas, reglas y límites

## Energía y agua
- PUE ilustrativo = suma(energy_total_kwh) / suma(energy_it_kwh), sin unidades. El total incluye IT. Mismo perímetro y mismos intervalos. No promediar ratios horarios sin ponderarlos.
- Cociente hídrico mostrado como WUE ilustrativo = suma(water_l) / suma(energy_it_kwh), L/kWh IT. Aquí water_l representa captación operativa in situ: declarar esta convención. No es consumo neto, no incorpora agua de generación eléctrica ni fabricación y no se afirma equivalencia con un informe normalizado/certificado.
- El filtro cambia el perímetro temporal y de sitios; comparar solo filtros equivalentes. Sin filas, ratio indefinido (null), no cero. Comparar total y ratio: un ratio menor no garantiza menor impacto absoluto.
- No deducir litros por consulta/chat. No se simula un servicio de inferencia ni su utilización compartida. Tampoco multiplicar consumo de este portátil por un PUE arbitrario para presentarlo como medición.

## Baseline de anomalías
`common/cifox.py` aporta reglas explicables: PUE >1.6, cociente hídrico >1.5 L/kWh IT, entrada >29°C o cualquier evento OT distinto de normal. Son umbrales inventados para enseñar, no umbrales de seguridad. El conjunto fue construido con anomalías visibles a esas reglas: su resultado perfecto no valida eficacia externa.

Opcional: `tools/compare_detectors.py --method isolation_forest` ajusta StandardScaler + IsolationForest (100 árboles, contamination 0.05, random_state 22102026, 1 trabajo CPU) solo en referencia. Usa seis variables numéricas; no usa escenario, etiqueta ni OT. Por tanto la comparación con reglas que sí ven OT tiene diferente información y NO es una prueba justa de superioridad. Es una oportunidad para que el equipo diseñe una comparación controlada. No ajustar sobre evaluación y después reportarla como prueba independiente.

## GreenAI: qué se mide y qué se estima
`python tools/compare_detectors.py --method rules` informa tiempo de pared (perf_counter), tiempo CPU (process_time) y pico de asignaciones Python (tracemalloc, NO RAM total). Excluye carga del CSV e imports; incluye ajuste+predicción en IF, solo reglas en baseline. El overhead de instrumentación está incluido.

`--assumed-watts 30` y `--assumed-gco2e-per-kwh 300` son supuestos editables, NO valores medidos ni recomendaciones:
- energía estimada kWh = W supuestos × segundos de pared / 3 600 000
- emisiones estimadas gCO2e = kWh estimados × gCO2e/kWh supuestos

Reportar equipo, SO, versiones, tamaño del dato, repeticiones, media/mediana/dispersión, calentamiento y si la fase es entrenamiento o inferencia. Procesos de fondo, reposo, hardware y temperatura afectan resultados. Una sola corrida corta no demuestra ahorro real. Medición de energía física requiere instrumentación adicional y un protocolo; el kit no la ofrece. No estima huella de entrenamiento previo, fabricación, red, almacenamiento, refrigeración ni agua.

## Seguridad
Solo lectura local. Sin PLC, red OT, actuadores, contraseñas ni respuesta automatizada. Un evento de login fallido no prueba ataque. No usar este prototipo para controlar refrigeración, tomar decisiones de continuidad o certificar seguridad.
