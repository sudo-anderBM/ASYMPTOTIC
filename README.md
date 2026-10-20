# CIFOX · Kit para participantes del hackathon

**DATOS TOTALMENTE SIMULADOS. Prototipos educativos, sin control de infraestructura.**

Dos alternativas gratuitas y de código abierto para equipos heterogéneos. No requieren GPU, API keys, cuentas, servicios de pago ni Node. Elegid una; comparten datos y lógica. Python 3.12 recomendado. Preparad dependencias antes del evento: el uso funciona sin Internet después de instalar correctamente Python y los paquetes. El ZIP no incluye instaladores ni wheels y no permite una instalación totalmente offline por sí solo.

| | A · Streamlit | B · API + web |
|---|---|---|
| Perfil | Principiantes, análisis con Python | Equipos que quieren separar API e interfaz |
| Lenguajes | Python/pandas | Python + HTML/CSS/JavaScript |
| Interfaz | Dashboard Streamlit | Web estática servida por FastAPI |
| Puerto | localhost:8501 | localhost:8000; esquema /openapi.json |
| Instalación | [README A](stack_a_streamlit/README.md) | [README B](stack_b_api_web/README.md) |
| Trade-off | Menos código UI; framework reactivo | Más archivos; control directo de UI/API |

No es necesario ejecutar los dos ni crear dos proyectos independientes. Ambos directorios dependen de common/ y data/: conservad el ZIP completo y ejecutad desde la raíz.

Este paquete reúne el material de trabajo para participantes: instalación, datos simulados, ejercicios, código, pruebas y licencias. Los criterios oficiales de evaluación y el horario del evento serán los que comunique la organización.

## Recorrido de 10 minutos
1. Descomprimid el kit completo en una carpeta local con permisos de escritura.
2. Seguid el README de vuestro stack, cread el entorno virtual e instalad requisitos.
3. Ejecutad la aplicación y abrid su URL local.
4. Filtrad un centro y comprobad los totales, unidades y advertencia de simulación.
5. Elegid un [reto](docs/EXERCISES.md); no hace falta completar todos.

## Estructura
- common/: carga, validación, ratios agregados y reglas pedagógicas.
- data/: CSV sintético y baseline JSON de referencia.
- tools/generate_data.py: regeneración determinista del CSV, solo biblioteca estándar.
- tools/compare_detectors.py: benchmark de reglas y opción IsolationForest, no medición energética física.
- stack_a_streamlit/ y stack_b_api_web/: apps y pruebas.
- tests/: tests comunes sin pytest.
- docs/: diccionario de datos, métricas, ejercicios, ejemplos de benchmark y licencias de dependencias.
- MANIFEST.json: inventario del paquete con tamaños y hashes SHA256.
- tools/package_kit.py: empaquetado de los archivos de participantes incluidos en su lista explícita.
- LICENSE: licencia MIT del contenido original.

## Comandos adicionales
Con el Python de vuestro entorno virtual (en Windows sustituid `.venv-a/bin/python` por `.venv-a\Scripts\python.exe`; para B, `.venv-b`):

```sh
.venv-a/bin/python tools/generate_data.py
.venv-a/bin/python -m unittest discover -s tests -v
.venv-a/bin/python tools/compare_detectors.py --method rules
.venv-a/bin/python -m pip install -r requirements-ml.txt
.venv-a/bin/python tools/compare_detectors.py --method isolation_forest
```

Regenerar sobrescribe únicamente el CSV por defecto; `--output otro.csv` conserva el original. Una semilla distinta modifica el ruido, no las ventanas de anomalías.

## Límites y licencia
Dataset, código y documentación originales bajo MIT. Dependencias con licencias propias: docs/DEPENDENCIES.md. No se incluyen datasets ni PDFs de terceros. Datos y supuestos no sustentan recomendaciones de ingeniería, conclusiones causales, certificaciones, alarmas reales ni cifras de agua por consulta de IA. No cargad datos reales sensibles en este ejercicio. Consultad [métricas](docs/METRICS.md), el [diccionario de datos](docs/DATA_DICTIONARY.md) y las instrucciones de prueba del stack elegido.

Los ejemplos JSON de benchmark muestran una sola ejecución sobre datos sintéticos. Sus tiempos no son una garantía de rendimiento en vuestro equipo, y energía/emisiones son estimaciones con supuestos. Las dependencias completas registradas corresponden a Linux con Python 3.12; comprobad la instalación en vuestro equipo antes del evento. No hay validación de ejecución en Windows/macOS ni auditoría formal de accesibilidad o seguridad.

## Volver a empaquetar

`python tools/package_kit.py` genera `CIFOX_kit_participantes.zip` junto a la carpeta del kit y actualiza el manifiesto. Incluye solo los archivos enumerados en `PUBLIC_FILES` del script; si vuestro proyecto añade archivos, revisad esa lista antes de compartirlo. El manifiesto no incluye su propio hash. No añadáis credenciales, datos sensibles ni documentos ajenos al trabajo del equipo.
