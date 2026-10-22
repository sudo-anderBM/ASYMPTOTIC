# Seguridad — confianza en el dato

ASYMPTOTIC protege el dato en dos niveles: **que los archivos sean los originales** y **que una lectura falsificada no oculte una fuga**. No cifra, y explicamos por qué.

En un sistema de enfriamiento (OT), el riesgo principal no es que alguien *lea* las lecturas, sino que las *altere*: un medidor engañado puede esconder una fuga, y una cifra cambiada puede falsear el CUE que reportamos. Por eso la parte de seguridad es de **integridad**, no de confidencialidad. Encaja con el sub-reto 4 (gobernanza): un indicador de sostenibilidad solo sirve si se puede auditar.

## Nivel 1 · Integridad de archivos (implementado)

`greenai/integridad.py` calcula la huella SHA-256 de cada archivo que la API muestra y la compara con la registrada:

| Archivos | Contra qué se comparan | ¿Se puede actualizar? |
|---|---|---|
| `data/operaciones_simuladas.csv`, `data/reference_metrics.json` (kit CIFOX) | Huellas oficiales de `MANIFEST.json`, fijas en el código | Nunca |
| `results/*`, `stack_b_api_web/static/mock/*.json` (equipo) | `results/HUELLAS.sha256` | Sí, a propósito: `python -m greenai.integridad --actualizar` |

- Si un solo byte cambia, `/api/*`, `/health` y `/static/mock/*` responden **503** y la página muestra el aviso en lugar de cifras. La consola dice qué archivo falló (solo el nombre).
- La barra superior de la página muestra **"Integridad verificada · N archivos SHA-256"**, o el aviso en rojo.
- Costo: unos 1 ms por petición, solo con `hashlib` (biblioteca estándar).
- Pruebas: `tests/test_integridad.py` (byte cambiado, resultado alterado, archivo borrado, archivo nuevo sin huella, CRLF de Windows, API con 503 y cabeceras de seguridad).

## Nivel 2 · Lecturas falsificadas (medido)

`greenai/ataques.py` toma la idea de [ThermoShield](https://github.com/sudo-anderBM/ThermoShield) (detección de sensores falsificados) y la aplica a nuestras columnas. 10 semillas × 3 sitios × 2 ventanas = 60 ventanas de 12 h por celda; `results/ataques.json`.

| Ataque | Reglas | Isolation Forest | Residual 3σ | CUSUM | Z-score |
|---|---|---|---|---|---|
| Sin ataque (alarma por azar) | 0 % | 72 % | 2 % | 8 % | 0 % |
| Valor fijo en la temperatura de entrada | 0 % | 88 % | **98 %** | 100 % | 0 % |
| Deriva de −1 %/h en el agua | 0 % | 72 % | **100 %** | 100 % | 45 % |
| *Replay* de 24 h solo del agua | 0 % | 72 % | **98 %** | 90 % | 2 % |
| *Replay* coherente de la fila completa | 0 % | 55 % | **2 %** | 12 % | 0 % |

- El Residual 3σ detecta las falsificaciones de una columna porque rompen la relación entre agua, energía IT, carga y temperatura.
- Isolation Forest da alarma en 72 % de las ventanas **sin** ataque: sus cifras no indican detección.
- **Límite:** si se repite la fila completa, la relación se conserva y ningún detector estadístico lo ve.

## Lo que ya traía el kit y conservamos

- Servidor solo en `127.0.0.1`; API de solo lectura (solo GET).
- CSP estricta (sin scripts en línea, sin CDN), `nosniff`, `no-referrer`, `no-store`; `/docs` desactivado.
- Validación de parámetros (422) y errores genéricos (503) sin trazas.
- Sin datos personales; los sitios son seudónimos (SIM-A, SIM-B, SIM-C).

## Lo que no hicimos y por qué

| Medida | Por qué no |
|---|---|
| TLS | No hay ingesta por red y la guía prohíbe publicar el servidor fuera de 127.0.0.1. Si algún día se expone: uvicorn `--ssl-keyfile`/`--ssl-certfile` o un proxy inverso. |
| Cifrado en reposo | Los datos son simulados y los tiene todo participante; la clave quedaría en la misma laptop; los detectores necesitan los números en claro. |
| Usuarios, roles, gestión de claves | No hay usuarios ni escritura que autorizar; guardar credenciales crearía un activo que hoy no existe. |
| Detector de vecinos de ThermoShield | Necesita varios sensores con posición por sitio; el kit tiene un valor por variable, sitio y hora. |

## Límites y siguiente paso

1. Las huellas protegen contra cambios accidentales o de quien no edite también `HUELLAS.sha256`. Para cerrarlo: firmar las huellas con HMAC-SHA256 y una clave fuera del repositorio.
2. El *replay* coherente solo se frena en el origen: firmar cada lectura con HMAC-SHA256 y un contador que no se repite, y rechazar firmas inválidas o contadores repetidos antes de los detectores. En este prototipo no hay sensor real que firme.
3. Los eventos OT del kit (`login_fallido`, `cambio_config_no_autorizado`) ya pueden usarse con `use_ot=True`; la API los deja apagados porque en el kit coinciden con las anomalías y no prueban nada sobre fugas.

## Reproducir

```powershell
.\.venv-b\Scripts\python.exe -m greenai.integridad
.\.venv-b\Scripts\python.exe -m greenai.ataques
.\.venv-b\Scripts\python.exe -m greenai.integridad --actualizar
.\.venv-b\Scripts\python.exe -m unittest tests.test_integridad tests.test_ataques -v
```
