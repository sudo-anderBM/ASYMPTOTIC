# Acuífero, gobernanza y escenarios sin agua potable — ASYMPTOTIC

> **DATOS SIMULADOS.** Sub-reto de la convocatoria: **4 · Green AI, gobernanza y métricas**.
> Todas las cifras de litros y kWh vienen de los datos simulados del kit (días 4 a 7, 96 h por sitio, semilla 1), llevadas a un año (× 8,760 h / 96 h). Son **escenarios con supuestos visibles, no ahorros observados**: los tres sitios son simulaciones, no un experimento controlado.

## 1. Extracción de agua de cada sitio

`water_l` es agua captada en el sitio para enfriar (guía CIFOX, p. 5): no descuenta retornos ni incluye el agua de generar la electricidad.

| Sitio | Enfriamiento | Agua por hora | Agua al año | WUE pedagógica (L/kWh IT) | PUE |
|---|---|---|---|---|---|
| SIM-A | Aire | 5.3 L | 46,000 L | 0.032 | 1.368 |
| SIM-B | Evaporativo | 140.0 L | **1,227,000 L** | 0.854 | 1.237 |
| SIM-C | Líquido | 34.8 L | 304,000 L | 0.213 | 1.198 |

Los tres sitios tienen casi la misma carga de servidores (unos 164 kWh IT por hora). SIM-B gasta menos energía, pero extrae unas 27 veces más agua que SIM-A.

## 2. Impacto en el acuífero de Yucatán

- **Extracción:** en la península de Yucatán el agua subterránea es la **única fuente de agua potable** ([Yucatan State Report Card 2017](https://ian.umces.edu/site/assets/files/11212/yucatan-state-report-card-2017.pdf)). Un sitio como SIM-B extraería del acuífero alrededor de **1.2 millones de litros al año**, y en enfriamiento evaporativo esa agua se evapora: no regresa al acuífero.
- **Presión por fugas:** una fuga del 10 % en SIM-B son **14 L por hora**. Si nadie la detecta durante una semana, son unos **2,350 L**; durante un año, unos **122,600 L**, el 10 % más de extracción sin ningún beneficio.
- **Riesgo de contaminación (hipótesis):** el suelo es **kárstico**, roca caliza con cuevas y cenotes y sin ríos en la superficie, así que lo que se derrama llega rápido al acuífero. El agua de enfriamiento suele llevar aditivos (anticorrosivos, biocidas). No lo medimos: lo planteamos como riesgo a vigilar, no como hecho.
- **Qué aporta el detector:** con fugas del 10 %, el Residual 3σ encontró 90 de 90 en datos simulados, casi sin falsas alarmas; las reglas fijas, 0 de 90. Detectar en horas en lugar de semanas reduce tanto la extracción de más como el tiempo en que un derrame puede llegar al subsuelo.

## 3. Gobernanza del recurso

Reglas propuestas para usar el detector de forma responsable:

1. **Transparencia:** cada alerta muestra lo esperado, lo medido y la diferencia; nunca es una caja negra.
2. **Decisión humana:** el detector avisa; una persona del equipo de operación revisa antes de cerrar válvulas o cambiar la operación.
3. **Reporte mensual:** PUE, WUE y CUE de cada sitio, más el costo de cómputo del propio detector, para comprobar que el balance siga siendo positivo.
4. **Registro de incidentes:** cada fuga confirmada se anota con los litros estimados perdidos, para rendir cuentas a la autoridad del agua y a la comunidad.
5. **Seguridad OT:** si alguien manipula el control del enfriamiento, el consumo deja de cuadrar con lo que predice la física; la alerta se trata también como posible incidente de seguridad. Nuestros detectores no usan los eventos OT del kit como entrada, así que es una señal independiente.

## 4. Escenarios sin agua potable (bonificación, sección 14)

Para SIM-B, el sitio que más agua extrae. Supuestos: la misma carga de servidores, factor de emisión **0.444 kg CO₂e/kWh** (Sistema Eléctrico Nacional 2024, aviso SEMARNAT del 28/02/2025).

| Escenario | Agua potable al año | Energía extra al año | CO₂e extra al año | Qué hace falta |
|---|---|---|---|---|
| Hoy: evaporativo con agua del acuífero | ~1,227,000 L | — | — | — |
| **A. Evaporativo con agua tratada o reciclada** | **0 L** | ~0 (supuesto: bombeo despreciable) | ~0 | Suministro de agua residual tratada cerca del sitio y su tratamiento para torres |
| **B. Aire de alta eficiencia (como SIM-A)** | ~46,000 L (y 0 si ese poco se surte con agua no potable) | ~188,000 kWh (PUE de 1.237 a 1.368) | ~84 t | Clima: más calor exige más energía |
| **C. Circuito líquido cerrado (como SIM-C)** | 0 L si la reposición se hace con agua no potable (en la simulación repone ~304,000 L/año) | ninguna (PUE 1.198, menor que hoy) | ninguna | Reposición con agua no potable y vigilancia del circuito |

**Lectura:** el escenario C es el más equilibrado en esta simulación: menos agua y menos energía, siempre que la reposición no sea potable. El B cambia agua por carbono: hay que decidirlo con el factor de la red y el clima de la región.

**Por qué sigue haciendo falta el detector:** en un circuito cerrado o con agua reciclada, la fuga pasa a ser la principal pérdida, y en suelo kárstico un derrame de agua tratada o con aditivos llega al acuífero. Vigilarlo cuesta unos 4 mg de CO₂e al año con una potencia supuesta de 30 W.

## 5. Límites de este análisis

- Datos simulados de una semana llevados a un año; no hay estacionalidad.
- La diferencia entre sitios es un escenario, no un ahorro medido: cambiar de enfriamiento cambia otras cosas que la simulación no incluye.
- El riesgo de contaminación es una hipótesis; no se midió ninguna calidad de agua.
