"""Integridad SHA-256 de datos y resultados. Ejecutar: python -m unittest tests.test_integridad -v"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from greenai import integridad
from stack_b_api_web.main import app

ROOT = integridad.ROOT


class CopiaDelProyecto(unittest.TestCase):
    """Cada prueba trabaja sobre una copia: nunca altera los archivos reales."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for ruta in [*integridad.KIT_OFICIAL, *integridad.archivos_equipo(),
                     integridad.HUELLAS.as_posix()]:
            destino = self.tmp / ruta
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / ruta, destino)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_repositorio_real_integro(self):
        self.assertEqual(integridad.verificar(), [])

    def test_copia_integra(self):
        self.assertEqual(integridad.verificar(self.tmp), [])

    def test_un_byte_cambiado_en_el_csv_del_kit(self):
        csv = self.tmp / "data/operaciones_simuladas.csv"
        datos = bytearray(csv.read_bytes())
        datos[-2] = ord("9") if datos[-2] != ord("9") else ord("8")
        csv.write_bytes(bytes(datos))
        self.assertIn(("data/operaciones_simuladas.csv", "no coincide"),
                      integridad.verificar(self.tmp))

    def test_resultado_alterado(self):
        sweep = self.tmp / "results/sweep_fuga.json"
        sweep.write_text(sweep.read_text(encoding="utf-8").replace("0.", "0.9", 1),
                         encoding="utf-8")
        self.assertIn(("results/sweep_fuga.json", "no coincide"),
                      integridad.verificar(self.tmp))

    def test_archivo_borrado(self):
        (self.tmp / "stack_b_api_web/static/mock/sweep.json").unlink()
        self.assertIn(("stack_b_api_web/static/mock/sweep.json", "falta"),
                      integridad.verificar(self.tmp))

    def test_archivo_nuevo_sin_huella(self):
        (self.tmp / "results/sweep_falso.json").write_text("{}", encoding="utf-8")
        self.assertIn(("results/sweep_falso.json", "sin huella registrada"),
                      integridad.verificar(self.tmp))

    def test_sin_archivo_de_huellas(self):
        (self.tmp / integridad.HUELLAS).unlink()
        self.assertEqual(integridad.verificar(self.tmp)[0][1], "falta o está mal formado")

    def test_crlf_de_windows_no_es_alteracion(self):
        sweep = self.tmp / "results/sweep_fuga.json"
        sweep.write_bytes(sweep.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(integridad.verificar(self.tmp), [])

    def test_actualizar_no_cubre_los_datos_del_kit(self):
        csv = self.tmp / "data/operaciones_simuladas.csv"
        csv.write_bytes(csv.read_bytes() + b"\n")
        integridad.actualizar(self.tmp)
        self.assertIn(("data/operaciones_simuladas.csv", "no coincide"),
                      integridad.verificar(self.tmp))


class ApiBloqueaDatosAlterados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_integra_responde_normal(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["integridad"]["estado"], "ok")
        self.assertEqual(r.json()["integridad"]["archivos"], integridad.total_archivos())

    def test_alterada_responde_503_sin_rutas_ni_cifras(self):
        falla = [("results/sweep_fuga.json", "no coincide")]
        with patch.object(integridad, "verificar", return_value=falla), \
                self.assertLogs("uvicorn.error", level="WARNING"):
            for ruta in ("/health", "/api/health", "/api/sweep?tipo=fuga",
                         "/api/scenario", "/static/mock/sweep.json"):
                with self.subTest(ruta=ruta):
                    r = self.client.get(ruta)
                    self.assertEqual(r.status_code, 503)
                    self.assertEqual(r.json()["integridad"], "falla")
                    self.assertNotIn("results/", r.text)
                    self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])

    def test_la_pagina_sigue_cargando_para_mostrar_el_aviso(self):
        with patch.object(integridad, "verificar", return_value=[("x", "falta")]):
            self.assertEqual(self.client.get("/static/deteccion.html").status_code, 200)


if __name__ == "__main__":
    unittest.main()
