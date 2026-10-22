# ASYMPTOTIC — Reto 4: Practicar GreenAI en CPU

Este repositorio contiene nuestra solución para el **Reto 4**. Básicamente, comparamos 5 detectores (desde umbrales fijos hasta modelos de ML) para encontrar ineficiencias y fugas de agua. 
¿La conclusión? El detector residual (3σ) es capaz de ver fugas pequeñas que las reglas fijas ignoran, y gasta unas 20 veces menos CPU que un modelo como IsolationForest.

> ⚠️ **AVISO DE DATOS SIMULADOS:** Todo aquí es 100 % sintético. No hay equipos reales, no hay lecturas en vivo, y las cifras de energía/CO₂ son estimaciones basadas en supuestos declarados. El sistema no ejerce ninguna acción de control.

## Documentos de entrega
- [docs/FICHA_SUPUESTOS.md](docs/FICHA_SUPUESTOS.md)
- [docs/APORTACION.md](docs/APORTACION.md)
- [Capturas de la interfaz](docs/capturas/)

## 1. Instalación (Python 3.12 obligatorio)

La guía del kit pide usar Python 3.12. La primera vez necesitas internet para instalar las dependencias.

**Windows (PowerShell):**
```powershell
py -3.12 -m venv .venv-b
.\.venv-b\Scripts\python.exe -m pip install -r stack_b_api_web/requirements.txt