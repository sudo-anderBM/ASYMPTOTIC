"""Integridad de datos y resultados: ¿son los archivos originales?

Antes de mostrar una cifra, la API comprueba que cada archivo que sirve
tiene la misma huella SHA-256 que cuando se generó. Si alguien cambia un
solo byte, la huella cambia y la API responde 503 en lugar de mostrar
cifras alteradas.

Dos fuentes de verdad:
  * Datos del kit (CIFOX): huellas oficiales de MANIFEST.json, copiadas
    aquí como constantes. Nunca se actualizan: si no coinciden, el CSV no
    es el del kit.
  * Resultados del equipo (results/ y los ejemplos de static/mock/):
    huellas en results/HUELLAS.sha256, que se regeneran a propósito
    después de volver a correr el barrido o el benchmark.

Uso desde la raíz:
    python -m greenai.integridad               # verifica y muestra la tabla
    python -m greenai.integridad --actualizar  # tras regenerar resultados

Límites (dichos tal cual):
  * Los finales de línea CRLF se cuentan como LF, para que el mismo
    archivo dé la misma huella en Windows y en Linux.
  * Protege contra cambios accidentales o de alguien que no toque también
    HUELLAS.sha256. Quien pueda editar ambos puede falsificar los
    resultados; para eso haría falta firmar las huellas con una clave que
    no viva en el repositorio (HMAC), fuera del alcance de este prototipo.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUELLAS = Path("results") / "HUELLAS.sha256"

# Huellas oficiales del kit, copiadas de MANIFEST.json (campo sha256).
# No se regeneran nunca: si no coinciden, los datos no son los del kit.
KIT_OFICIAL = {
    "data/operaciones_simuladas.csv":
        "a498db9c2251a8f9dc761ab08f30f59f3e8269ac5a71546219a2d1b5552e7088",
    "data/reference_metrics.json":
        "4e39f3c98222a7220a429714f876d9dfe80f2d4a3b716932cc7cc30b6ed127cd",
}

# Patrones de los archivos del equipo que la API o el pitch muestran.
PATRONES_EQUIPO = ("results/*.json", "results/*.csv", "results/*.txt",
                   "stack_b_api_web/static/mock/*.json")


def huella(ruta: Path) -> str:
    """SHA-256 del archivo, contando CRLF como LF."""
    contenido = ruta.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(contenido).hexdigest()


def archivos_equipo(raiz: Path = ROOT) -> list[str]:
    rutas = set()
    for patron in PATRONES_EQUIPO:
        rutas.update(p.relative_to(raiz).as_posix() for p in raiz.glob(patron))
    rutas.discard(HUELLAS.as_posix())
    return sorted(rutas)


def total_archivos(raiz: Path = ROOT) -> int:
    """Archivos con huella: los del kit más los del equipo."""
    return len(KIT_OFICIAL) + len(archivos_equipo(raiz))


def leer_huellas(raiz: Path = ROOT) -> dict[str, str]:
    archivo = raiz / HUELLAS
    esperadas = {}
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        valor, ruta = linea.split(maxsplit=1)
        esperadas[ruta.lstrip("*")] = valor
    return esperadas


def verificar(raiz: Path = ROOT) -> list[tuple[str, str]]:
    """Devuelve [(archivo, problema)]. Lista vacía = todo íntegro."""
    problemas: list[tuple[str, str]] = []
    try:
        esperadas = {**leer_huellas(raiz), **KIT_OFICIAL}
    except (OSError, ValueError):
        return [(HUELLAS.as_posix(), "falta o está mal formado")]

    for ruta in archivos_equipo(raiz):          # archivos nuevos sin huella
        if ruta not in esperadas:
            problemas.append((ruta, "sin huella registrada"))

    for ruta, valor in sorted(esperadas.items()):
        archivo = raiz / ruta
        if not archivo.is_file():
            problemas.append((ruta, "falta"))
        elif huella(archivo) != valor:
            problemas.append((ruta, "no coincide"))
    return problemas


def actualizar(raiz: Path = ROOT) -> int:
    """Reescribe HUELLAS.sha256 con los resultados actuales del equipo."""
    lineas = ["# SHA-256 de los resultados del equipo (CRLF contado como LF).",
              "# Regenerar solo a propósito: python -m greenai.integridad --actualizar"]
    rutas = archivos_equipo(raiz)
    lineas += [f"{huella(raiz / r)}  {r}" for r in rutas]
    (raiz / HUELLAS).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return len(rutas)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--actualizar", action="store_true",
                   help="regenera results/HUELLAS.sha256 (no toca las del kit)")
    args = p.parse_args(argv)

    if args.actualizar:
        kit = [(r, m) for r, m in verificar() if r in KIT_OFICIAL]
        if kit:
            print("No se actualiza: los datos del kit no son los originales.")
            for ruta, motivo in kit:
                print(f"  {ruta}: {motivo}")
            return 1
        print(f"Huellas actualizadas: {actualizar()} archivos en {HUELLAS.as_posix()}")

    problemas = verificar()
    total = total_archivos()
    if not problemas:
        print(f"Integridad OK: {total} archivos coinciden con su huella SHA-256.")
        return 0
    print(f"Integridad FALLA en {len(problemas)} archivo(s):")
    for ruta, motivo in problemas:
        print(f"  {ruta}: {motivo}")
    print("Si regeneraste resultados a propósito: python -m greenai.integridad --actualizar")
    return 1


if __name__ == "__main__":
    sys.exit(main())
