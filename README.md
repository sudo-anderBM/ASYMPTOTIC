# ASYMPTOTIC

## Demo


<p align="center">
  <strong>IA eficiente para centros de datos sostenibles</strong>
  <br>
  Detección de fugas de agua e ineficiencias mediante modelos estadísticos y aprendizaje automático.
</p>

## ¿Qué es ASYMPTOTIC?

ASYMPTOTIC evalúa detectores ligeros capaces de identificar fugas de agua e ineficiencias energéticas en centros de datos simulados, comparando su precisión y costo computacional.

**¿Por qué importa en Yucatán?** La península depende del agua subterránea y su terreno kárstico facilita la infiltración de contaminantes. Prevenir pérdidas contribuye a proteger este recurso.

En nuestra simulación, una fuga del 10 % en un sistema con consumo de 140 L/h puede representar aproximadamente **2,352 litros de agua perdidos en siete días**.

*Referencia: [Yucatan State Report Card 2017](https://ian.umces.edu/site/assets/files/11212/yucatan-state-report-card-2017.pdf). Los datos de consumo son sintéticos.*

## ¿Cómo funciona?

Comparamos cinco detectores:

- **Reglas fijas:** evaluación mediante umbrales operativos.
- **Isolation Forest:** detección de anomalías mediante aprendizaje automático.
- **Residual 3σ:** identificación de desviaciones respecto al comportamiento esperado.
- **Residual CUSUM:** detección de desviaciones acumuladas.
- **Z-score:** identificación estadística de valores atípicos.

El modelo residual calcula la diferencia entre el consumo observado y el esperado:

$$
r_t = y_t - \hat{y}_t
$$

Donde \(y_t\) representa el consumo observado, \(\hat{y}_t\) el consumo estimado por el modelo y \(r_t\) el residuo. Una desviación significativa puede indicar una anomalía que requiere revisión humana.

## Resultados experimentales

Detección de fugas simuladas del 10 %:

| Detector | Escenario normal | Escenario difícil |
|---|---:|---:|
| Reglas fijas | 0 % | 0 % |
| Isolation Forest | 33 % | 32 % |
| Residual 3σ | 100 % | 39 % |
| Residual CUSUM | 100 % | 77 % |
| Z-score | 48 % | 22 % |

En el escenario normal, Residual 3σ registró aproximadamente **0.008 falsas alarmas al día** y una latencia mediana de **5.3 ms** en el benchmark reportado.

## GreenAI: eficiencia computacional

Evaluamos la tasa de detección, las falsas alarmas, la latencia, el tiempo de CPU y la memoria asignada durante las pruebas. La energía y las emisiones de CO₂e se estiman mediante supuestos explícitos; no son mediciones directas.

## Tecnologías

- Python 3.12 y scikit-learn 1.8.0.
- FastAPI para la API y la interfaz web.
- Streamlit para el panel del kit.
- Datos sintéticos, escenarios controlados y pruebas automatizadas.
- Ejecución en CPU, sin necesidad de GPU.

## Instalación y ejecución

```bash
python3.12 -m venv .venv-b
.venv-b/bin/python -m pip install -r stack_b_api_web/requirements.txt
.venv-b/bin/python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

En Windows, utiliza `.\.venv-b\Scripts\python.exe` en lugar de `.venv-b/bin/python`.

- **Interfaz web:** http://127.0.0.1:8000/static/deteccion.html
- **Documentación de la API:** http://127.0.0.1:8000/openapi.json

## Integridad de los datos

ASYMPTOTIC utiliza hashes SHA-256 para verificar la integridad de archivos de referencia y resultados. Esto permite detectar modificaciones, pero no sustituye una firma digital si también se puede alterar el manifiesto de hashes.

## Limitaciones

- Los datos y escenarios son sintéticos.
- Los resultados no representan una validación en centros de datos reales.
- Las estimaciones ambientales dependen de los supuestos utilizados.
- Las alertas requieren revisión humana y no controlan directamente los equipos.

El proyecto amplía el kit CIFOX con detectores, evaluación experimental y análisis de eficiencia computacional, utilizando herramientas de IA como apoyo al desarrollo y pruebas para verificar el funcionamiento.

Consulta `docs/` y `results/` para conocer la metodología, los supuestos y los resultados detallados. Revisa los archivos del repositorio para conocer las condiciones de licencia.

---

<p align="center">
  <strong>Matemáticas × Física × IA × Eficiencia computacional</strong>
</p>
