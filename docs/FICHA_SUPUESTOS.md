# Ficha de datos y supuestos — ASYMPTOTIC

> **DATOS SIMULADOS.** Nada de este proyecto proviene de un centro de datos real.
> Reto principal: **4 · Practicar GreenAI en CPU** (Guía CIFOX para participantes).

## 1. Datos

| Qué | Detalle |
|---|---|
| Archivo del kit | `data/operaciones_simuladas.csv`: 504 filas = 3 sitios ficticios × 168 horas, semilla 22102026 |
| Sitios | SIM-A (aire), SIM-B (evaporativa), SIM-C (líquida) |
| Partición | `referencia`: 3 primeros días (72 h por sitio) para ajustar · `evaluacion`: 4 días siguientes (96 h por sitio) para calificar |
| Datos limpios | `greenai/base_data.py` regenera la misma semana con las fórmulas de `tools/generate_data.py`, sin anomalías. Coinciden con el CSV del kit en 488 de 504 filas; las 16 restantes son las anomalías que trae el kit |
| Datos difíciles | Misma base con ±5 % de ruido en el agua y un término no lineal con la temperatura (`+0.004·max(0, T−24)²`) |
| Fugas inyectadas | `greenai/scenarios.py`: 3 ventanas de 6 h por sitio, solo en evaluación. Fuga de magnitud m: `agua × (1 + m)` |
| Ineficiencias inyectadas | Mismas ventanas: `total = IT + (total − IT) × (1 + m)` |
| Semillas | Cada semilla cambia el ruido **y** la posición de las ventanas, para que el examen no sea siempre el mismo |
| Entradas prohibidas | `scenario` y `simulated_anomaly` nunca se usan para detectar; los eventos OT tampoco (`use_ot=False` en todos los detectores) |

## 2. Indicadores

- **PUE** = Σ `energy_total_kwh` ÷ Σ `energy_it_kwh` del periodo y sitio elegidos.
- **WUE pedagógica del kit** = Σ `water_l` ÷ Σ `energy_it_kwh` (L/kWh IT). Es agua tomada en el sitio; no incluye el agua de generar la electricidad ni descuenta retornos. No acredita una medición normalizada.
- Nunca se promedian los cocientes de cada hora: siempre cociente de sumas, con el mismo filtro en numerador y denominador.

## 3. Qué es medido y qué es supuesto

| Medido (en el equipo de quien ejecuta) | Supuesto (hipótesis declarada, no medida) |
|---|---|
| Tiempo de **aprender** (fit) y de **revisar** (predict), por separado, con calentamiento descartado | Potencia del equipo: **30 W**. No es el TDP ni una medición; `bench.py` también prueba 15 y 65 W |
| Mediana, media y desviación de las repeticiones (`bench.py`: 30; `sweep.py`: 10) | Factor de emisión: **0.444 kg CO₂e/kWh**, Sistema Eléctrico Nacional de México 2024, aviso de SEMARNAT del 28/02/2025. `bench.py` también usa 100, 300 y 600 g/kWh como sensibilidad |
| Pico de memoria de Python (tracemalloc; no es la RAM total del proceso) | Uso del detector: revisar cada hora (8,760 veces al año) y reaprender una vez al día (365) |
| Calidad de detección con intervalo de confianza del 95 % (Wilson) | Días que tardaría en descubrirse una fuga sin detector: **7** (se puede mover en la página) |
| Sistema, CPU y versiones (`results/env.json` y `meta` de `results/sweep_*.json`) | |

**Regla:** un menor tiempo no demuestra por sí solo menos energía. Los kWh y el CO₂e son estimaciones: `kWh = W supuestos × segundos ÷ 3,600,000` y `g CO₂e = kWh × factor × 1,000`.

## 4. Lo que la estimación no incluye

- Fabricación del equipo, red, almacenamiento ni refrigeración del propio equipo.
- **Agua.** No se puede obtener litros por consulta o por chat: no se midió ningún centro de datos donde corra el modelo.
- Lectura del CSV ni imports (se excluyen de la medición a propósito).

## 5. Resultados principales (fugas del 10 %, datos normales)

Fuente: `results/sweep_fuga.json` (10 semillas × 3 sitios × 3 eventos = 90 eventos por punto).

| Detector | Eventos detectados | IC 95 % | Falsas alarmas/día | Costo (mediana, ms) |
|---|---|---|---|---|
| Reglas del kit (sin eventos OT) | 0 % | 0–4 % | 0 | 0.25 |
| IsolationForest | 33 % | 25–44 % | 1.28 | 102.8 |
| Residual 3σ | 100 % | 96–100 % | 0.008 | 5.1 |
| Residual CUSUM | 100 % | 96–100 % | 0.28 | 6.6 |
| Z-score simple | 48 % | 38–58 % | 0 | 1.3 |

Los tiempos de esta tabla se midieron en Windows 11 con Python 3.13.12 y scikit-learn 1.9.1. Si se vuelve a medir con la versión de referencia del kit (Python 3.12, scikit-learn 1.8.0), actualizar esta tabla con los archivos nuevos de `results/`.
