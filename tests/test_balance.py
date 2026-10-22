from fastapi.testclient import TestClient

from stack_b_api_web import main

client = TestClient(main.app)


def test_balance_devuelve_ejemplo_simulado():
    r = client.get("/api/balance")
    assert r.status_code == 200
    assert r.json()["simulated"] is True


def test_balance_fuerza_simulated_true(monkeypatch, tmp_path):
    archivo = tmp_path / "balance.json"
    archivo.write_text('{"simulated": false, "x": 1}', encoding="utf-8")
    monkeypatch.setattr(main, "BALANCE_MOCK", archivo)
    r = client.get("/api/balance")
    assert r.status_code == 200
    assert r.json() == {"simulated": True, "x": 1}


def test_balance_sin_archivo_da_503_con_texto(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "BALANCE_MOCK", tmp_path / "no_existe.json")
    r = client.get("/api/balance")
    assert r.status_code == 503
    assert isinstance(r.json()["detail"], str)


def test_balance_json_invalido_da_503(monkeypatch, tmp_path):
    archivo = tmp_path / "balance.json"
    archivo.write_text("{esto no es json", encoding="utf-8")
    monkeypatch.setattr(main, "BALANCE_MOCK", archivo)
    r = client.get("/api/balance")
    assert r.status_code == 503
    assert isinstance(r.json()["detail"], str)


def test_balance_que_no_es_objeto_da_503(monkeypatch, tmp_path):
    archivo = tmp_path / "balance.json"
    archivo.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(main, "BALANCE_MOCK", archivo)
    r = client.get("/api/balance")
    assert r.status_code == 503
    assert isinstance(r.json()["detail"], str)