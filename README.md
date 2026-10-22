# ASYMPTOTIC

**¿Qué detector ve una fuga de agua pequeña en un centro de datos, y cuánto cómputo cuesta tenerlo encendido?**

- Reto principal: **4 · Practicar GreenAI en CPU**.


> ⚠️ **DATOS SIMULADOS.** Todo es sintético: no hay equipos reales, lecturas en vivo ni acciones de control. Los tiempos y la memoria son **medidos**; la energía y el CO₂e son **estimaciones** con supuestos declarados. Las alertas requieren revisión humana.

## Qué hicimos

Comparamos cinco detectores de fugas e ineficiencias sobre los datos simulados del kit CIFOX (3 sitios × 168 horas): las reglas fijas del kit, IsolationForest, Residual 3σ, Residual CUSUM y Z-score. A cada uno le medimos **calidad y costo a la vez**, con el mismo archivo, repeticiones, calentamiento y las fases de aprender (fit) y revisar (predict) por separado.

Resultado con fugas del 10 % (90 eventos, datos normales): las reglas detectan **0 %**, el Residual 3σ **100 %** con 0.008 falsas alarmas al día y unos 5 ms; IsolationForest detecta 33 %, da 1.3 falsas alarmas al día y tarda unos 100 ms.

## Documentos de entrega

- [Ficha de datos y supuestos](docs/FICHA_SUPUESTOS.md).
- [Qué venía en el kit y qué aportamos, y límites](docs/APORTACION.md).
- [Acuífero, gobernanza y escenarios sin agua potable](docs/ACUIFERO_Y_ESCENARIOS.md).
- [Capturas de la interfaz](docs/capturas/).
- [Tabla oficial de cifras](results/cifras.txt).

## 1. Instalación (Python 3.12)

Desde la raíz del repositorio. La primera vez necesita internet para instalar dependencias; después todo funciona sin conexión.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv-b
.\.venv-b\Scripts\python.exe -m pip install -r stack_b_api_web\requirements.txt
.\.venv-b\Scripts\python.exe -m pip check
```

**macOS / Linux:**

```bash
python3.12 -m venv .venv-b
.venv-b/bin/python -m pip install -r stack_b_api_web/requirements.txt
.venv-b/bin/python -m pip check
```

`stack_b_api_web/requirements.txt` incluye `scikit-learn==1.8.0`, que necesitan los detectores. No hace falta GPU, Node ni cuentas.

## 2. Arrancar la demo

```powershell
.\.venv-b\Scripts\python.exe -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

(En macOS/Linux, `.venv-b/bin/python` en lugar de `.\.venv-b\Scripts\python.exe`.)

- Nuestra página: **http://127.0.0.1:8000/static/deteccion.html**
- Panel original del kit, sin cambios: http://127.0.0.1:8000/
- Contrato de la API: http://127.0.0.1:8000/openapi.json

No abrir los HTML con doble clic: la página necesita la API local. Ctrl + C detiene el servidor.

## 3. Pruebas

Los comandos de la guía CIFOX (página 9):

```powershell
.\.venv-b\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-b\Scripts\python.exe -m unittest discover -s stack_b_api_web/tests -v
```

## 4. Repetir la medición

```powershell
.\.venv-b\Scripts\python.exe -m greenai.bench --reps 30 --warmup 3
.\.venv-b\Scripts\python.exe -m greenai.sweep
.\.venv-b\Scripts\python.exe -m greenai.cifras | Out-File -Encoding utf8 results\cifras.txt
```

| Comando | Qué mide | Archivos que escribe |
|---|---|---|
| `greenai.bench` | CSV del kit: tiempo de pared y de CPU de fit y predict (30 repeticiones, 3 de calentamiento), pico de memoria de Python (tracemalloc), F1/precisión/recall con IC y energía/CO₂e estimados con 15, 30 y 65 W | `results/bench.csv`, `results/sensibilidad.csv`, `results/env.json` |
| `greenai.sweep` | Fugas e ineficiencias inyectadas de 5 % a 100 %, datos normales y difíciles, 10 semillas × 3 sitios × 3 eventos = 90 eventos por punto, con IC de Wilson; costo como mediana y desviación de 10 repeticiones | `results/sweep_fuga.json`, `results/sweep_ineficiencia.json` |
| `greenai.cifras` | Tabla de cifras que usa la página y el pitch | `results/cifras.txt` |

Los tiempos dependen del equipo: las versiones y el equipo quedan en `results/env.json` y en `meta` de cada `sweep_*.json` (medido con Python 3.12.10, scikit-learn 1.8.0, Windows 11).

## 5. Resultados

Fugas del 10 %, `results/sweep_fuga.json`:

| Detector | Datos normales | IC 95 % | Falsas alarmas/día | Datos difíciles | Costo (mediana, ms) |
|---|---|---|---|---|---|
| Reglas del kit (sin eventos OT) | 0 % | 0–4 % | 0 | 0 % | 0.2 |
| IsolationForest | 33 % | 25–44 % | 1.28 | 32 % | 100.1 |
| Residual 3σ | 100 % | 96–100 % | 0.008 | 39 % | 5.3 |
| Residual CUSUM | 100 % | 96–100 % | 0.28 | 77 % | 6.9 |
| Z-score simple | 48 % | 38–58 % | 0 | 22 % | 1.3 |

Ineficiencias del 10 % (datos normales): reglas 0 %, Residual 3σ 86 %, CUSUM 91 %, IsolationForest 31 %.

**Energía y CO₂e (estimados):** suponiendo 30 W (no medidos) y el factor de 0.444 kg CO₂e/kWh (Sistema Eléctrico Nacional 2024, aviso SEMARNAT del 28/02/2025), revisar cada hora y reaprender a diario durante un año con el Residual 3σ cuesta unos 1.2 s de CPU, unos 0.00001 kWh y unos 4.6 mg de CO₂e. Una fuga del 10 % en el sitio evaporativo que tardara 7 días en descubrirse perdería unos 2,350 L.

## 6. Comparación justa

- Ningún detector usa los eventos OT del kit ni las columnas `scenario` y `simulated_anomaly`.
- Todos se ajustan con la partición `referencia` (3 días) y se califican con `evaluacion` (4 días).
- Cada semilla cambia el ruido y la posición de las fugas.
- Con las anomalías originales del kit (`greenai.bench`), las reglas y el Residual 3σ empatan (F1 0.86): esas anomalías se diseñaron para ser visibles a las reglas. Por eso medimos también con fugas pequeñas inyectadas.

## 7. Límites

- Solo datos simulados; nada está demostrado en una instalación real.
- El residual es un modelo lineal: con ruido y relaciones no lineales, las fugas del 10 % se detectan mucho menos (39 %).
- Energía y CO₂e dependen de la potencia y del factor supuestos; un menor tiempo no demuestra por sí solo menos energía.
- `tracemalloc` mide la memoria que reserva Python, no toda la RAM del proceso.
- No se calcula agua por consulta de IA: la estimación de costo no incluye agua.
- Las alertas son señales para revisión humana, no diagnósticos.

## 8. Estructura

| Carpeta | Contenido |
|---|---|
| `common/`, `data/`, `tools/`, `docs/*` del kit, `stack_a_streamlit/` | Kit CIFOX (licencia MIT), sin cambios |
| `greenai/` | Detectores, datos limpios, escenarios, métricas por evento, explicación, barrido, balance y medición |
| `stack_b_api_web/` | API FastAPI (base del kit + endpoints `/api/detectors`, `/api/scenario`, `/api/explain`, `/api/sweep`, `/api/balance`) y la página `static/deteccion.html` |
| `tests/` | Pruebas del proyecto (unittest) |
| `results/` | Mediciones y cifras |

Usamos asistentes de IA para programar y redactar; el equipo revisó y probó los resultados.

## Licencia

El código, la documentación y el CSV originales del kit CIFOX se distribuyen con la licencia MIT incluida en `LICENSE`. El kit de datos se usa exclusivamente para fines del hackathon.
