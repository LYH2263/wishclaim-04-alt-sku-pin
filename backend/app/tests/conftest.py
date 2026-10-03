import importlib
import pytest

@pytest.fixture
def client(tmp_path, monkeypatch):
    """每个用例一个独立 DATA_DIR，重装载 app 以触发 startup 建表/种子。"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.seed, app.main
    importlib.reload(app.seed)
    importlib.reload(app.main)
    from fastapi.testclient import TestClient
    with TestClient(app.main.app) as tc:
        yield tc
