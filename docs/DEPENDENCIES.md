# Dependencias y licencias

El kit usa paquetes abiertos; no incluye su código ni binarios. La licencia MIT del kit no sustituye las condiciones de dependencias. Fuentes oficiales y licencia declarada del paquete instalado:

| Paquete | Versión probada | Licencia | Proyecto |
|---|---|---|---|
| pandas | 2.2.3 | BSD-3-Clause (y avisos de componentes distribuidos) | https://github.com/pandas-dev/pandas |
| numpy | 2.3.5 | BSD-3-Clause (y avisos de componentes distribuidos) | https://github.com/numpy/numpy |
| fastapi | 0.141.1 | MIT | https://github.com/fastapi/fastapi |
| uvicorn | 0.52.1 | BSD-3-Clause | https://github.com/Kludex/uvicorn |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| scikit-learn | 1.8.0 | BSD-3-Clause (y avisos de componentes distribuidos) | https://github.com/scikit-learn/scikit-learn |
| Altair | 5.5.0 | BSD-3-Clause | https://github.com/vega/altair |
| Streamlit | 1.51.0 | Apache-2.0 | https://github.com/streamlit/streamlit |

Python usa licencia PSF: https://docs.python.org/3/license.html. Los instaladores resuelven dependencias transitivas; consultar los avisos incluidos en cada distribución instalada. Los requirements fijan versiones directas validadas, pero no son un lock completo transitorio ni un suministro offline. No se afirma reproducibilidad bit a bit de instalaciones distintas. Para replicar este entorno de prueba, véanse lock-linux-py312.txt de cada stack y lock-ml-linux-py312.txt, generados con pip freeze en entornos virtuales limpios. Estos snapshots no incluyen hashes de ruedas y no son garantía para otros sistemas operativos.
