"""
Transforma el parquet del Data Lake para que su estructura coincida
exactamente con la vista View_respuestas_encuesta_percepcion_historica_optimizada
en la base de datos dbpercepcion.

Diferencias encontradas:
  Parquet                    -> Vista SQL
  ─────────────────────────────────────────────────────────
  Anio                       -> Año
  Atencion                   -> Atencion (con tilde: Atención)
  Comunicacion_y_acceso      -> Comunicacion y acceso (con tildes y espacios)
  Resolucion_de_la_necesidad -> Resolucion de la necesidad (con tildes y espacios)
  Tiempo_de_respuesta        -> Tiempo de respuesta (con tildes y espacios)
  NPS_Numerico (object)      -> decimal
  Atencion_Numerica (object) -> decimal

Uso:
  python transformar_parquet.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
from azure.storage.blob import BlobServiceClient

# ── Cargar .env ────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ── Variables Azure Blob ────────────────────────────────────────────────────
AZURE_URL    = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "https://saurdatamining.blob.core.windows.net")
CONTAINER    = os.getenv("AZURE_CONTAINER_NAME", "fs-encuestaspercepcion")
SAS_TOKEN    = os.getenv("AZURE_SAS_TOKEN", "")
PARQUET_NAME = "EncuestasPercepcion/VistaEncuestaPercepcion2026.parquet"
# Archivo de salida local (temporal)
OUTPUT_LOCAL = Path(__file__).resolve().parent / "VistaEncuestaPercepcion2026_transformado.parquet"

# ── Mapeo de renombrado: nombre parquet -> nombre vista SQL ─────────────────
RENAME_MAP = {
    "Anio":                       "Año",
    "Atencion":                   "Atención",
    "Comunicacion_y_acceso":      "Comunicación y acceso",
    "Resolucion_de_la_necesidad": "Resolución de la necesidad",
    "Tiempo_de_respuesta":        "Tiempo de respuesta",
}

# ── Orden de columnas segun la vista SQL ────────────────────────────────────
COLUMNS_ORDER = [
    "encuestadoId",
    "Año",
    "Mes",
    "respuestaFch",
    "preguntaDescripcion",
    "encuestaNombre",
    "servicioNombre",
    "sedeNombre",
    "areaNombre",
    "encuestadoApellidos",
    "encuestadoNombres",
    "encuestadoCelular",
    "encuestadoEmail",
    "tipoPreguntaId",
    "consecutivo",
    "preguntaId",
    "encuestaId",
    "idAreaServicio",
    "idServicioEncuesta",
    "idSedeEncuesta",
    "respuestaId",
    "Atención",
    "Comunicación y acceso",
    "Eficiencia",
    "NPS",
    "Resolución de la necesidad",
    "Tiempo de respuesta",
    "preguntaSinIndicador",
    "NPS_Numerico",
    "Atencion_Numerica",
]

# Columnas que deben ser convertidas a float (decimal en SQL)
NUMERIC_COLUMNS = ["NPS_Numerico", "Atencion_Numerica"]


def get_blob_service():
    url = AZURE_URL.rstrip("/")
    sas = SAS_TOKEN.lstrip("?")
    return BlobServiceClient(f"{url}?{sas}")


def main():
    print("=" * 70)
    print("  TRANSFORMACION DEL PARQUET PARA COINCIDIR CON LA VISTA SQL")
    print("=" * 70)

    # ── 1. Descargar parquet original ──────────────────────────────────────
    print(f"\n[1] Descargando parquet original ...")
    try:
        client = get_blob_service().get_blob_client(container=CONTAINER, blob=PARQUET_NAME)
        raw = client.download_blob().readall()
        df = pd.read_parquet(BytesIO(raw))
        print(f"    -> Descargado: {len(raw):,} bytes")
        print(f"    -> Filas    : {len(df):,}")
        print(f"    -> Columnas : {len(df.columns)}")
    except Exception as e:
        print(f"    !! ERROR: {e}")
        sys.exit(1)

    cols_originales = list(df.columns)

    # ── 2. Renombrar columnas ──────────────────────────────────────────────
    print(f"\n[2] Renombrando columnas ...")
    df = df.rename(columns=RENAME_MAP)
    for old_name, new_name in RENAME_MAP.items():
        print(f"    {old_name:<35s} -> {new_name}")

    # ── 3. Convertir tipos numericos ───────────────────────────────────────
    print(f"\n[3] Convirtiendo columnas numericas a float (decimal SQL) ...")
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            tipo_antes = df[col].dtype
            df[col] = pd.to_numeric(df[col], errors="coerce")
            print(f"    {col:<35s} {tipo_antes} -> {df[col].dtype}")

    # ── 4. Reordenar columnas segun la vista SQL ───────────────────────────
    print(f"\n[4] Reordenando columnas segun la vista SQL ...")
    # Verificar que todas las columnas esperadas existen
    missing = [c for c in COLUMNS_ORDER if c not in df.columns]
    extra   = [c for c in df.columns if c not in COLUMNS_ORDER]
    if missing:
        print(f"    !! Columnas faltantes despues de renombrar: {missing}")
    if extra:
        print(f"    !! Columnas extra en parquet (se conservan al final): {extra}")
        COLUMNS_ORDER.extend(extra)
    df = df[COLUMNS_ORDER]
    print(f"    -> Columnas ordenadas: {len(df.columns)}")

    # ── 5. Verificar estructura final ──────────────────────────────────────
    print(f"\n[5] Estructura final del parquet transformado {'─' * 32}")
    for i, (c, t) in enumerate(df.dtypes.items(), 1):
        print(f"    {i:3d}. {c:<40s} {str(t)}")

    # ── 6. Guardar localmente ──────────────────────────────────────────────
    print(f"\n[6] Guardando parquet transformado localmente ...")
    df.to_parquet(OUTPUT_LOCAL, index=False, engine="pyarrow")
    size_mb = OUTPUT_LOCAL.stat().st_size / (1024 * 1024)
    print(f"    -> Archivo: {OUTPUT_LOCAL}")
    print(f"    -> Tamano : {size_mb:.2f} MB")
    print(f"    -> Filas  : {len(df):,}")

    # ── 7. Resumen ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  TRANSFORMACION COMPLETADA")
    print("=" * 70)
    print(f"\n  Cambios aplicados:")
    print(f"    - 5 columnas renombradas (acentos/tildes/espacios)")
    print(f"    - 2 columnas convertidas a float decimal")
    print(f"    - 30 columnas reordenadas segun la vista SQL")
    print(f"\n  Archivo de salida: {OUTPUT_LOCAL}")
    print(f"\n  Para subir de vuelta al Data Lake:")
    print(f"    (Opcionalmente reemplazar el original)")
    print("=" * 70)


if __name__ == "__main__":
    main()