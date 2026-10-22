# ASYMPTOTIC

<p align="center">
  <strong>IA eficiente para centros de datos sostenibles</strong>
  <br>
  Detección de fugas de agua e ineficiencias mediante modelos estadísticos y aprendizaje automático.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/GreenAI-Eficiencia%20computacional-10B981?style=flat-square" alt="GreenAI">
  <img src="https://img.shields.io/badge/Datos-Sintéticos-F59E0B?style=flat-square" alt="Datos sintéticos">
</p>

## ¿Qué es ASYMPTOTIC?

ASYMPTOTIC investiga si detectores ligeros pueden identificar fugas pequeñas de agua en centros de datos simulados, comparando su precisión y costo computacional.

**¿Por qué importa en Yucatán?** La península depende del agua subterránea y su terreno kárstico facilita la infiltración de contaminantes. Prevenir pérdidas de agua es relevante para proteger este recurso.

En nuestra simulación, una fuga del 10 % en un sitio evaporativo que consume 140 L/h puede representar aproximadamente **2,352 litros perdidos en siete días**.

*Referencia regional: [Yucatan State Report Card 2017](https://ian.umces.edu/site/assets/files/11212/yucatan-state-report-card-2017.pdf). Las cifras de consumo son simuladas.*

## ¿Cómo funciona?

Comparamos cinco detectores:

- **Reglas fijas:** umbrales operativos.
- **Isolation Forest:** aprendizaje automático no supervisado.
- **Residual 3σ:** desviaciones respecto al comportamiento esperado.
- **Residual CUSUM:** acumulación de desviaciones pequeñas.
- **Z-score:** detección estadística de valores atípicos.

El modelo residual estima la diferencia entre el consumo observado y el esperado:

$$
r_t = y_t - \hat{y}_t
$$

donde \(y_t\) representa el consumo observado, \(\hat{y}_t\) el consumo estimado por el modelo y \(r_t\) el residuo. Un residuo elevado puede indicar una anomalía que requiere revisión.

Las desviaciones permiten identificar posibles anomalías que requieren revisión humana.

## Resultados experimentales

Para fugas simuladas del 10 %:

| Detector | Detección normal | Detección difícil |
|---|---:|---:|
| Reglas fijas | 0 % | 0 % |
| Isolation Forest | 33 % | 32 % |
| Residual 3σ | 100 % | 39 % |
| Residual CUSUM | 100 % | 77 % |
| Z-score | 48 % | 22 % |

En el escenario normal, Residual 3σ registró aproximadamente 0.008 falsas alarmas al día y un costo mediano de 5.3 ms en el benchmark reportado.

**GreenAI:** evaluamos detección, falsas alarmas, tiempo de CPU, latencia y memoria. La energía y el CO₂e se estiman mediante supuestos explícitos; no son mediciones directas.

## Tecnologías y ejecución

- Python 3.12 y scikit-learn 1.8.0.
- FastAPI para la API y la interfaz web.
- Datos sintéticos, escenarios controlados y pruebas automatizadas.
- Ejecución en CPU, sin necesidad de GPU.

```bash
python3.12 -m venv .venv-b
.venv-b/bin/python -m pip install -r stack_b_api_web/requirements.txt
.venv-b/bin/python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

En Windows, utiliza `.\.venv-b\Scripts\python.exe` en lugar de `.venv-b/bin/python`.

Interfaz: [http://127.0.0.1:8000/static/deteccion.html](http://127.0.0.1:8000/static/deteccion.html)

## Alcance y limitaciones

Los datos y escenarios son sintéticos. El rendimiento no está validado en instalaciones reales; las estimaciones ambientales dependen de supuestos y las alertas no deben utilizarse para controlar equipos.

El proyecto parte del kit CIFOX y añade detectores, evaluación experimental y medición de recursos. Se utilizaron asistentes de IA como apoyo al desarrollo, con revisión y pruebas del equipo.

Consulta `docs/` y `results/` para conocer los supuestos, la metodología y los resultados completos. La licencia y las condiciones de uso se especifican en los archivos del repositorio.

---

<p align="center">
  <strong>Matemáticas × Física × IA × Eficiencia computacional</strong>
</p>
