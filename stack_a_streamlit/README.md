# Stack A · Panel local CIFox

**DATOS SIMULADOS. Prototipo educativo.** Un panel sencillo para explorar energía, agua y alertas mediante reglas. No representa una instalación real ni controla infraestructura. No necesitas una cuenta ni subir archivos.

## Qué incluye

- Panel Streamlit con filtros de refrigeración y fechas UTC inclusivas.
- PUE y WUE local simplificados: **cociente de sumas, con energía TI en el denominador**.
- Gráficas separadas de energía y agua, con una tabla alternativa para leer los valores.
- Alertas deterministas con explicación; no son un modelo de IA, una certificación ni un diagnóstico.
- CSV simulado y módulo de cálculo compartidos con el otro stack, en `../data` y `../common`.

## Primer arranque (Python 3.12)

Instala Python 3.12 desde [python.org](https://www.python.org/downloads/). En Windows, marca la opción para añadir Python al PATH si el instalador la ofrece. Extrae **todo** el kit, abre una terminal y entra en su carpeta raíz, la que contiene `common`, `data` y `stack_a_streamlit`. No muevas solo esta carpeta.

### Windows · PowerShell

```powershell
py -3.12 -m venv .venv-a
.\.venv-a\Scripts\python.exe -m pip install -r stack_a_streamlit/requirements.txt
.\.venv-a\Scripts\python.exe -m streamlit run stack_a_streamlit/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

No es necesario activar el entorno, así se evitan cambios a la política de ejecución de PowerShell.

### macOS o Linux · Terminal

```bash
python3.12 -m venv .venv-a
.venv-a/bin/python -m pip install -r stack_a_streamlit/requirements.txt
.venv-a/bin/python -m streamlit run stack_a_streamlit/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

La instalación requiere Internet para descargar paquetes de PyPI. Después, el panel utiliza el CSV local. En algunas distribuciones Linux necesitas el paquete `python3.12-venv` de tu distribución para crear el entorno.

### Si ya activaste el entorno virtual

Desde la raíz del kit, el comando básico es:

```bash
python -m streamlit run stack_a_streamlit/app.py --server.address 127.0.0.1 --server.port 8501
```

Puedes añadir `--browser.gatherUsageStats false` para desactivar la telemetría de uso de Streamlit.

Abre **http://127.0.0.1:8501** en el navegador de ese mismo equipo. `127.0.0.1` limita el servidor al equipo local. Deja la terminal abierta; pulsa **Ctrl+C** para detenerlo. El primer inicio puede mostrar un mensaje de bienvenida de Streamlit: no necesitas dar tu correo; puedes dejarlo en blanco y pulsar Enter.

## Recorrido de cinco minutos

1. Comprueba el aviso **DATOS SIMULADOS** y observa los totales.
2. Selecciona un tipo de refrigeración. Cada uno corresponde a un sitio ficticio; no es una comparación causal entre tecnologías.
3. Selecciona un solo día usando la misma fecha en ambos filtros.
4. Abre la tabla bajo las gráficas. Suma la energía total y divídela por la energía TI para comprobar el PUE.
5. Lee los motivos de las alertas. Desmarca «Mostrar solo registros con alerta» para ver también los registros sin alerta.

## Interpretación y límites

- **PUE simplificado** = Σ energía total (kWh) / Σ energía TI (kWh). Es adimensional.
- **WUE local simplificado** = Σ agua local (L) / Σ energía TI (kWh). Se expresa en L/kWh TI. En este CSV, el agua representa **extracción local**, no una medición completa del consumo hídrico. No incluye el agua indirecta de la electricidad.
- Ambos cocientes usan exactamente las filas seleccionadas; no son promedios aritméticos de cocientes horarios.
- Las reglas del módulo compartido son ejemplos explicables. Sus umbrales no son límites normativos ni consignas aprobadas. Una alerta no demuestra una avería o un ataque.
- Las fechas, las escalas de las gráficas y sus etiquetas emergentes usan UTC. El último día del filtro está incluido completo.
- Cambian carga, clima y condiciones entre los sitios simulados. El panel no permite recomendar una tecnología real ni verificar resultados comerciales de CIFox.
- La aplicación solo lee el CSV suministrado y no incluye cargas de archivos, autenticación, acciones sobre equipos ni conectores OT. No publiques este servidor en Internet.

## Archivos y pequeñas modificaciones

- `app.py`: interfaz y filtros; empieza leyendo este archivo.
- `requirements.txt`: versiones directas verificadas.
- `lock-linux-py312.txt`: todas las dependencias de un entorno limpio probado en Linux con Python 3.12. Para reproducir ese entorno, instala este archivo en lugar de `requirements.txt`; en otras plataformas usa el archivo de requisitos directos.
- `test_app.py`: pruebas de pantalla con AppTest, sin navegador.
- `../common/cifox.py`: validación, métricas y reglas compartidas.
- `../data/operaciones_simuladas.csv`: observaciones ficticias.

Para practicar, trabaja sobre una copia del kit. Mantén el aviso «DATOS SIMULADOS». No sustituyas los datos por información sensible u operativa: integrar datos reales requiere acordar límites de medición, calidad, permisos y seguridad.

## Verificación automática

Con el entorno activado y desde la raíz:

```bash
python -m unittest discover -s stack_a_streamlit -p 'test_app.py' -v
```

También puedes sustituir `python` por `.venv-a/bin/python` en macOS/Linux o `.\.venv-a\Scripts\python.exe` en Windows. Las pruebas verifican arranque, filtros, métricas, fechas, selección vacía y cambios repetidos; no sustituyen una auditoría de accesibilidad o seguridad.

## Problemas frecuentes

- **«No module named streamlit»**: ejecuta la instalación con el mismo Python del entorno que usas para arrancar.
- **«No module named common» o falta el CSV**: vuelve a extraer el kit completo conservando las carpetas.
- **Puerto 8501 ocupado**: cambia a `--server.port 8502` y abre http://127.0.0.1:8502.
- **No hay datos**: selecciona al menos un tipo de refrigeración.
- **Fechas invertidas**: el inicio debe ser anterior o igual al final.
- **La terminal no encuentra Python**: cierra y abre la terminal tras instalar Python; verifica `py -3.12 --version` (Windows) o `python3.12 --version` (macOS/Linux).

Referencias de la herramienta: [instalación de Streamlit](https://docs.streamlit.io/get-started/installation), [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
