import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "backend" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.orquestador import construir_argumentos_batch, ejecutar_orquestador_batch
from backend.scheduler import get_batch_path


class DummyProcess:
    def __init__(self):
        self.pid = 12345


def test_construir_argumentos_batch_builds_expected_args():
    assert construir_argumentos_batch(area="CRAI", anio=2026, mes=5) == ["--area", "CRAI", "--anio", "2026", "--mes", "5"]
    assert construir_argumentos_batch(area="TODAS", auto_date=True) == []
    assert construir_argumentos_batch(area="CRAI", anio=None, mes=None) == ["--area", "CRAI"]


def test_ejecutar_orquestador_batch_invokes_cmd_with_expected_args(monkeypatch):
    batch_path = get_batch_path()
    captured = {}

    def fake_popen(args, stdout, stderr, env, shell):
        captured["args"] = args
        captured["env"] = env
        captured["shell"] = shell
        return DummyProcess()

    monkeypatch.setattr("backend.orquestador.subprocess.Popen", fake_popen)
    proceso = ejecutar_orquestador_batch(area="CRAI", anio=2026, mes=5)

    assert proceso.pid == 12345
    assert captured["shell"] is False
    assert captured["args"][:3] == ["cmd.exe", "/c", batch_path]
    assert captured["args"][3:] == ["--area", "CRAI", "--anio", "2026", "--mes", "5"]
    assert captured["env"]["SKIP_PAUSE_ON_EXIT"] == "1"


def test_run_now_builds_command_line_flags(monkeypatch):
    batch_path = get_batch_path()
    captured = {}

    def fake_run(args, capture_output, text, shell):
        captured["args"] = args
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("backend.scheduler.subprocess.run", fake_run)
    from backend.scheduler import run_now

    result = run_now(5, 2026, "mensual", area="CRAI", auto_date=False)

    assert result["returncode"] == 0
    assert captured["args"][:3] == [batch_path, "--anio", "2026"]
    assert captured["args"][3:7] == ["--mes", "5", "--area", "CRAI"]
