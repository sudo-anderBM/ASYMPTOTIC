# CIFOX · Kit B: API + interfaz web

Un panel educativo en español construido con **FastAPI** y **HTML/CSS/JavaScript sin compilación**. Se ejecuta en tu ordenador, con CPU y sin cuentas ni claves. **Todos los datos son simulados.** No hay conexión con equipos, subida de ficheros, escrituras ni acciones de control.

## 1. Antes de empezar

- Python **3.12** instalado; un navegador moderno.
- Conserva juntas las carpetas `stack_b_api_web`, `common` y `data`.
- Abre una terminal en la raíz `cifox_kits`, donde están esas tres carpetas. No ejecutes los comandos desde `stack_b_api_web`.
- La instalación inicial de dependencias necesita conexión a Internet, o paquetes preparados previamente. Después, el panel y su API funcionan **sin Internet**, sin fuentes remotas, CDN ni servicios de IA.

## 2. Instalar y arrancar

### macOS / Linux

```bash
python3.12 -m venv .venv-b
source .venv-b/bin/activate
python -m pip install -r stack_b_api_web/requirements.txt
python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

### Windows · PowerShell

Los comandos usan directamente el Python del entorno. No necesitas cambiar la política de ejecución de PowerShell ni activar scripts.

```powershell
py -3.12 -m venv .venv-b
.\.venv-b\Scripts\python.exe -m pip install -r stack_b_api_web\requirements.txt
.\.venv-b\Scripts\python.exe -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

Abre **http://127.0.0.1:8000** en tu navegador. Mantén esa terminal abierta; para detener el servidor, pulsa **Ctrl+C**.

Con el entorno activado, el comando principal, siempre desde la raíz del kit, es:

```bash
python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

No hace falta Node, npm, GPU, Docker ni una herramienta de compilación para ejecutar el panel. No abras `index.html` directamente: la página obtiene los datos de la API local.

## 3. Primer recorrido · cinco minutos

1. Busca el aviso **DATOS SIMULADOS**. Los tres centros ficticios se llaman SIM-A, SIM-B y SIM-C.
2. Observa los cuatro indicadores. **PUE** divide la energía total entre la energía TI. **WUE** divide los litros de agua retirada in situ entre los kWh TI. Ambos usan las sumas del periodo filtrado.
3. Elige un centro o un tipo de refrigeración. La vista se actualiza automáticamente. La combinación de un centro con otro tipo de refrigeración puede no tener registros; se indicará sin error.
4. Cambia el gráfico de **Energía** a **Agua**. Abre **Ver los valores del gráfico** para leer la misma información en una tabla.
5. Pulsa **Ver registros señalados**. La tabla explica qué regla activó cada señal. Desmarca **Solo con alerta** para volver a todos los registros.

El conjunto de referencia cubre los tres primeros días; el de evaluación, los cuatro siguientes. Aquí son filtros didácticos: **este panel no entrena ni ejecuta un modelo de IA**. Las reglas fijas se comparten con el otro kit.

## 4. Qué significa cada medida

- **PUE:** energía total / energía TI. Un menor valor indica menor energía adicional a la TI, dentro del mismo perímetro y periodo.
- **WUE mostrado:** agua retirada in situ / energía TI, en L/kWh. No incluye agua asociada a la generación eléctrica ni al resto de la cadena de suministro. No lo interpretes como consumo neto de agua ni como un inventario hídrico completo.
- **Energía y agua:** sumas del periodo seleccionado. Los registros son intervalos de una hora.
- **Alertas:** número de registros que activan al menos una regla. No es el número de condiciones disparadas, incidentes reales ni anomalías confirmadas.
- **Horas y agrupación diaria:** UTC. El navegador no convierte la tabla a tu huso horario.

Las reglas pedagógicas del módulo común señalan PUE > 1,6, agua > 1,5 L/kWh TI, temperatura de entrada > 29 °C o cualquier evento OT distinto de `normal`. Son umbrales de demostración, no límites universales ni instrucciones operativas. Compara centros considerando carga, clima, tecnología, calidad y límites de medición.

## 5. API de solo lectura

Abre estas direcciones en el navegador:

| Ruta | Resultado |
|---|---|
| `/health` o `/api/health` | Estado, carácter simulado, solo lectura y número de registros; comprueba que el CSV se puede cargar |
| `/api/metrics` | PUE, WUE, energía, agua, alertas, filtros disponibles y periodo UTC |
| `/api/records` | Hasta 100 registros por defecto, ordenados del más reciente al más antiguo |
| `/api/records?limit=1000` | Hasta 1000 registros; valores fuera de 1–1000 devuelven HTTP 422 |
| `/api/records?alerts_only=true` | Solo registros con alguna señal de regla |
| `/openapi.json` | Esquema de la API, disponible sin Internet |

**Filtros opcionales en `/api/metrics` y `/api/records`:** `site_id`, `cooling_type`, `split`. Los valores disponibles se devuelven en `filters` de `/api/metrics`. Un valor desconocido devuelve HTTP 422; una combinación válida sin coincidencias devuelve cero registros y ratios `null`.

Ejemplos:

```text
http://127.0.0.1:8000/api/metrics?site_id=SIM-A
http://127.0.0.1:8000/api/records?cooling_type=evaporativa&split=evaluacion&limit=10
http://127.0.0.1:8000/api/records?alerts_only=true&limit=1000
```

`/api/records` responde con `simulated`, `total`, `returned` y `records`. Cada registro incluye las columnas del CSV, más `rule_alert` y `rule_reason`. `total` indica el número de coincidencias antes del límite; `returned`, las filas realmente devueltas.

No se incluyen `/docs` ni `/redoc`: sus visores predeterminados usan recursos externos. El esquema `/openapi.json` sigue disponible.

## 6. Arquitectura y archivos

```text
cifox_kits/
├── common/cifox.py                  # Validación, métricas y reglas compartidas
├── data/operaciones_simuladas.csv   # Única fuente de datos de este panel
└── stack_b_api_web/
    ├── main.py                     # FastAPI, rutas GET y archivos estáticos
    ├── requirements.txt            # Cinco dependencias fijadas
    ├── lock-linux-py312.txt         # Dependencias completas del entorno probado
    ├── static/
    │   ├── index.html              # Estructura accesible en español
    │   ├── style.css               # Diseño adaptable, sin fuentes externas
    │   ├── app.js                  # Fetch, filtros, gráfico SVG y tabla
    │   └── favicon.svg
    └── tests/
        ├── test_api.py             # unittest + FastAPI TestClient
        └── browser_smoke.cjs       # QA opcional de desarrollo con Playwright
```

La API sirve la interfaz en el mismo origen y puerto. No se necesita CORS. No hay base de datos ni sesiones de usuario. El CSV se vuelve a leer en cada petición; es apropiado para una demostración pequeña, no para un servicio de alta carga.

La interfaz consulta hasta 1000 filas. Los 504 registros originales caben completos. Si amplías el CSV a más de 1000 coincidencias, el gráfico y la tabla se limitan a las 1000 más recientes y lo avisan; los indicadores siguen usando todo el periodo. Las alertas de la tabla también se restringen a esas filas cargadas.

El código introduce datos en el DOM con `textContent`, evitando interpretar contenido del CSV como HTML. Incluye etiquetas, foco de teclado visible, estado de carga, mensajes de error, respeto al movimiento reducido y una tabla alternativa para el gráfico. Esto no equivale a una auditoría formal de accesibilidad.

## 7. Pruebas

Desde la raíz del kit, con el entorno activo:

```bash
python -m unittest discover -s stack_b_api_web/tests -v
python -m pip check
```

Windows sin activar el entorno:

```powershell
.\.venv-b\Scripts\python.exe -m unittest discover -s stack_b_api_web\tests -v
.\.venv-b\Scripts\python.exe -m pip check
```

Las pruebas comprueban cálculos compartidos, filtros, combinación vacía, límites, orden, alertas, archivos estáticos, errores de datos y rechazo de métodos de escritura. Ejecutadlas en vuestro entorno después de instalar y tras modificar el código.

El inventario de dependencias de referencia está en `lock-linux-py312.txt`, registrado en Linux con Python 3.12. Para instalar esas mismas versiones, puedes usar el lock en lugar de `requirements.txt`. No garantiza compatibilidad con otros sistemas; Windows y macOS necesitan comprobación en el equipo que vais a usar.

El guion opcional `tests/browser_smoke.cjs` está dirigido a desarrolladores con Playwright y Chromium configurados. No forma parte de la instalación normal ni hace falta ejecutarlo para usar el kit. Las pruebas de API no sustituyen la revisión visual ni una auditoría formal de accesibilidad, seguridad o rendimiento.

Puede aparecer un aviso de deprecación de Starlette sobre TestClient y httpx. Un aviso no equivale por sí solo a un error: comprobad el resultado de las pruebas y mantened las versiones declaradas mientras investigáis.

## 8. Si algo no funciona

- **`No module named stack_b_api_web` o `common`:** vuelve a la raíz `cifox_kits` y comprueba que conservaste todas las carpetas del paquete.
- **`No module named fastapi`:** instala los requisitos con el mismo Python que usas para arrancar el servidor.
- **Puerto 8000 ocupado:** usa `--port 8001` y abre `http://127.0.0.1:8001`. La interfaz utiliza rutas relativas y seguirá funcionando.
- **La página dice que no puede cargar datos:** comprueba que el servidor sigue abierto. Visita `/health`, revisa que existe `data/operaciones_simuladas.csv` y pulsa **Actualizar**. Si falla una actualización, la página identifica expresamente que conserva la vista anterior.
- **CSV modificado no válido:** restaura el CSV original. El módulo común valida columnas, tipos, rangos, intervalos duplicados y que los datos se declaren simulados.
- **Windows no reconoce `py`:** usa la ruta del Python 3.12 que instalaste; no necesitas cambiar permisos del sistema.

## 9. Límites de seguridad

El servidor se vincula a **127.0.0.1**, accesible solo desde tu máquina. No cambies el host a `0.0.0.0`, lo publiques ni lo conectes a redes o equipos reales como parte de este ejercicio. No tiene autenticación, gestión multiusuario ni controles para un despliegue en producción. No introduzcas datos personales, contraseñas o telemetría real en el CSV de prácticas.
