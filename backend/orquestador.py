import os
import sys
import threading
import subprocess
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from .scheduler import get_batch_path


def construir_argumentos_batch(area: str = "TODAS", anio: Optional[int] = None, mes: Optional[int] = None, auto_date: bool = False):
    """Construye los argumentos que se pasarán al batch de orquestación."""
    if auto_date:
        return []

    argumentos = []
    if area:
        argumentos += ["--area", area]
    if anio is not None:
        argumentos += ["--anio", str(anio)]
    if mes is not None:
        argumentos += ["--mes", str(mes)]
    return argumentos


def construir_comando_batch(area: str = "TODAS", anio: Optional[int] = None, mes: Optional[int] = None, auto_date: bool = False):
    """Construye la lista de comando usada para ejecutar el batch."""
    batch_path = get_batch_path()
    return ["cmd.exe", "/c", batch_path] + construir_argumentos_batch(area, anio, mes, auto_date)


def ejecutar_orquestador_batch(area: str = "TODAS", anio: Optional[int] = None, mes: Optional[int] = None, auto_date: bool = False, log_path: Optional[Path] = None):
    """Ejecuta el batch de lanzamiento de encuestas de percepción en segundo plano."""
    comando = construir_comando_batch(area, anio, mes, auto_date)

    entorno = os.environ.copy()
    entorno["SKIP_PAUSE_ON_EXIT"] = "1"
    archivo_log = None
    salida = subprocess.DEVNULL

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        archivo_log = open(log_path, "a", encoding="utf-8", errors="replace")
        archivo_log.write(f"[PORTAL] Iniciando comando: {' '.join(comando)}\n")
        archivo_log.flush()
        salida = archivo_log

    proceso = subprocess.Popen(
        comando,
        stdout=salida,
        stderr=subprocess.STDOUT if archivo_log is not None else subprocess.DEVNULL,
        env=entorno,
        shell=False
    )
    if archivo_log is not None:
        proceso._portal_log_handle = archivo_log
    return proceso


def ejecutar_orquestador_detached(area: str = "TODAS", anio: Optional[int] = None, mes: Optional[int] = None, auto_date: bool = False):
    """Inicia el batch de orquestación en un hilo separado."""
    hilo = threading.Thread(target=ejecutar_orquestador_batch, args=(area, anio, mes, auto_date), daemon=True)
    hilo.start()
    return hilo
