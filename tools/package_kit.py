"""Empaqueta únicamente la lista revisada de archivos para participantes.

Ejecutar desde cualquier carpeta. Revisar PUBLIC_FILES al añadir archivos.
No se incluyen documentos ajenos a la lista, cachés ni entornos virtuales.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ('.gitignore', '.streamlit/config.toml', 'LICENSE', 'README.md', 'common/__init__.py', 'common/cifox.py', 'data/operaciones_simuladas.csv', 'data/reference_metrics.json', 'docs/DATA_DICTIONARY.md', 'docs/DEPENDENCIES.md', 'docs/EXERCISES.md', 'docs/METRICS.md', 'docs/benchmark_if_example.json', 'docs/benchmark_rules_example.json', 'lock-ml-linux-py312.txt', 'requirements-ml.txt', 'stack_a_streamlit/README.md', 'stack_a_streamlit/app.py', 'stack_a_streamlit/lock-linux-py312.txt', 'stack_a_streamlit/requirements.txt', 'stack_a_streamlit/test_app.py', 'stack_b_api_web/README.md', 'stack_b_api_web/__init__.py', 'stack_b_api_web/lock-linux-py312.txt', 'stack_b_api_web/main.py', 'stack_b_api_web/requirements.txt', 'stack_b_api_web/static/app.js', 'stack_b_api_web/static/favicon.svg', 'stack_b_api_web/static/index.html', 'stack_b_api_web/static/style.css', 'stack_b_api_web/tests/__init__.py', 'stack_b_api_web/tests/browser_smoke.cjs', 'stack_b_api_web/tests/test_api.py', 'tests/test_benchmark.py', 'tests/test_common.py', 'tools/compare_detectors.py', 'tools/generate_data.py', 'tools/package_kit.py')


def entries():
    files = []
    for name in PUBLIC_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.resolve().relative_to(ROOT.resolve()).as_posix() != name:
            raise ValueError(f"Archivo ausente, enlace o ruta no admitida: {name}")
        files.append(path)
    return files


def build(output):
    files = entries()
    output = Path(output).resolve()
    manifest_path = ROOT / "MANIFEST.json"
    if output in {path.resolve() for path in files + [manifest_path]}:
        raise ValueError("La salida no puede sobrescribir un archivo del kit")
    manifest = {
        "audience": "participantes",
        "notice": "CIFOX: contenido educativo; datos simulados. Hashes SHA256 excluyen el propio manifiesto.",
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files + [manifest_path]:
            archive.write(path, "cifox_kits/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Error de integridad ZIP")
    return len(files) + 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT.parent / "CIFOX_kit_participantes.zip")
    args = parser.parse_args()
    print(f"{build(args.output)} archivos: {args.output}")
