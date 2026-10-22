# Qué venía en el kit y qué aportamos — ASYMPTOTIC

> **DATOS SIMULADOS.** Reto principal: **4 · Practicar GreenAI en CPU** (Guía CIFOX para participantes).

## Pregunta

¿Qué detector encuentra fugas de agua pequeñas, con pocas falsas alarmas, y cuánto cómputo cuesta, medido de forma repetible en CPU?

## Del kit y nuestro

| Del kit CIFOX (licencia MIT, sin cambios salvo lo indicado) | Aportación del equipo |
|---|---|
| `common/cifox.py`: carga, validación, métricas y reglas | `greenai/detectors.py`: Residual 3σ, Residual CUSUM y Z-score; reglas e IsolationForest reimplementados con la misma interfaz para compararlos igual |
| `data/operaciones_simuladas.csv` y `tools/generate_data.py` | `greenai/base_data.py` (datos limpios y versión difícil) y `greenai/scenarios.py` (fugas e ineficiencias por ventanas, que cambian con la semilla) |
| `tools/compare_detectors.py` (reglas frente a IsolationForest, una medición) | `greenai/bench.py` (30 repeticiones, calentamiento, fit y predict separados, memoria, calidad con IC y sensibilidad a W y factor) y `greenai/sweep.py` (90 eventos por punto en 6 tamaños, datos normales y difíciles) |
| `stack_b_api_web/`: `main.py` base, `index.html`, `app.js`, `style.css` | Endpoints `/api/detectors`, `/api/scenario`, `/api/explain`, `/api/sweep`, `/api/balance` y la página `static/deteccion.html` (+ `.css`, `.js`) |
| `stack_a_streamlit/`, `docs/` (diccionario, métricas, ejercicios), `LICENSE` | `greenai/events.py` (métricas por evento), `explain.py`, `service.py`, pruebas en `tests/`, resultados en `results/`, esta ficha y `FICHA_SUPUESTOS.md` |

El panel original del kit sigue funcionando sin cambios en http://127.0.0.1:8000/.

## Límites

1. **Con las anomalías originales del kit, las reglas empatan con el residual.** Con `greenai/bench.py` sobre el CSV del kit y sin eventos OT, las reglas y el Residual 3σ obtienen el mismo F1 (0.86). La guía advierte que esas anomalías "se diseñaron para ser visibles a las reglas"; por eso inyectamos fugas pequeñas propias, donde sí aparece la diferencia. Con eventos OT, las reglas llegan a F1 = 1.0 porque las anomalías del kit coinciden con esos eventos: no es mérito de la regla.
2. **Solo datos simulados.** No se ha demostrado nada en una instalación real; el siguiente paso sería validar con telemetría real y con otro equipo.
3. **Con ruido, las fugas muy pequeñas se esconden.** En datos difíciles, con fugas del 10 % el Residual 3σ detecta 39 % y CUSUM 77 %; el residual necesita fugas del 20 % para llegar a 92 %.
4. **Energía y CO₂e son estimaciones.** El tiempo se mide; la potencia (30 W) y el factor de emisión son supuestos. Un menor tiempo no demuestra por sí solo menos energía.
5. **Las alertas requieren revisión humana.** El detector dice "esto no cuadra con lo esperado", no si es una fuga, un sensor dañado o un cambio de operación. Los umbrales son didácticos, no límites operativos.
