import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

TASK_NAME_DEFAULT = os.getenv("TASK_NAME", "LanzadorEncuestasPercepcion")


def get_batch_path() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    batch_path = os.getenv("BATCH_PATH")
    candidates = []

    if batch_path:
        explicit = Path(batch_path).expanduser()
        candidates.append(explicit)
        if not explicit.is_absolute():
            candidates.extend([
                Path(__file__).resolve().parent / explicit,
                repo_root / explicit,
                repo_root.parent / explicit,
            ])

    candidates.extend([
        repo_root / "ARCHIVOS_NO_DESPLIEGUE" / "Lanzador_encuestapercepcion.bat",
        repo_root / "Lanzador_encuestapercepcion.bat",
        repo_root.parent / "Lanzador_encuestapercepcion.bat",
    ])

    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved.exists():
            return str(resolved)

    return str((repo_root / "ARCHIVOS_NO_DESPLIEGUE" / "Lanzador_encuestapercepcion.bat").resolve(strict=False))


def run_command(args):
    result = subprocess.run(args, capture_output=True, text=True, shell=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_task_status(task_name: str = TASK_NAME_DEFAULT) -> dict:
    code, out, err = run_command(["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"])
    if code != 0:
        return {"task_name": task_name, "exists": False, "next_run": None, "last_run_time": None, "status": None, "path": None, "error": err}

    data = {line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip() for line in out.splitlines() if ":" in line}
    return {
        "task_name": task_name,
        "exists": True,
        "next_run": data.get("Next Run"),
        "last_run_time": data.get("Last Run Time"),
        "status": data.get("Status"),
        "path": data.get("Task To Run"),
    }


def create_monthly_task(task_name: str = TASK_NAME_DEFAULT, start_time: str = "00:05") -> dict:
    batch_path = get_batch_path()
    quoted_path = f'"{batch_path}"'
    args = [
        "schtasks", "/Create", "/TN", task_name,
        "/TR", quoted_path,
        "/SC", "MONTHLY", "/D", "1", "/ST", start_time,
        "/F"
    ]
    code, out, err = run_command(args)
    return {"returncode": code, "stdout": out, "stderr": err, "task_name": task_name}


def delete_task(task_name: str = TASK_NAME_DEFAULT) -> dict:
    code, out, err = run_command(["schtasks", "/Delete", "/TN", task_name, "/F"])
    return {"returncode": code, "stdout": out, "stderr": err, "task_name": task_name}


def run_now(mes: int, anio: int, tipo_carga: str, area: Optional[str] = None, auto_date: bool = False) -> dict:
    batch_path = get_batch_path()
    args = [batch_path]
    if auto_date:
        args.append("--auto_date")
    else:
        args += ["--anio", str(anio), "--mes", str(mes)]
    if area:
        args += ["--area", area]

    code, out, err = run_command(args)
    return {
        "returncode": code,
        "stdout": out,
        "stderr": err,
        "batch_path": batch_path,
        "timestamp": datetime.now().isoformat(),
    }
