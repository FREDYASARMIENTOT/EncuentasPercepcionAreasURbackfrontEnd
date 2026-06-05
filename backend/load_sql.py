import re
from pathlib import Path

from sqlalchemy import text

try:
    from .database import engine
except ImportError:
    from database import engine

SQL_FILE = Path(__file__).resolve().parents[0] / "sql" / "insert_synthetic_data.sql"
GO_PATTERN = re.compile(r"^\s*GO\s*$", re.IGNORECASE)


def split_sql_batches(sql_text: str):
    batches = []
    current = []
    for line in sql_text.splitlines():
        if GO_PATTERN.match(line):
            if current:
                batches.append("\n".join(current).strip())
                current = []
        else:
            current.append(line)
    if current:
        batches.append("\n".join(current).strip())
    return [batch for batch in batches if batch]


if __name__ == "__main__":
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"SQL file not found: {SQL_FILE}")

    sql_text = SQL_FILE.read_text(encoding="utf-8")
    batches = split_sql_batches(sql_text)

    with engine.begin() as connection:
        for batch in batches:
            print(f"Ejecutando batch SQL ({len(batch)} caracteres)")
            connection.execute(text(batch))

    print("Ejecución del script SQL completada.")
