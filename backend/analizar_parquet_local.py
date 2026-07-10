"""
Analiza el parquet local para entender su estructura y contenido.
"""
import pandas as pd
from pathlib import Path

PARQUET_LOCAL = Path(r"F:\ETL_DITIC\EncuestasPercepciónAzure\VistaEncuestaPercepcion2026.parquet")

def main():
    print("=" * 70)
    print("  ANALISIS DEL PARQUET LOCAL")
    print("=" * 70)

    if not PARQUET_LOCAL.exists():
        print(f"\n  !! Archivo no encontrado: {PARQUET_LOCAL}")
        return

    size_mb = PARQUET_LOCAL.stat().st_size / (1024 * 1024)
    print(f"\n  Archivo : {PARQUET_LOCAL}")
    print(f"  Tamano  : {size_mb:.2f} MB")

    df = pd.read_parquet(PARQUET_LOCAL)
    print(f"  Filas   : {len(df):,}")
    print(f"  Columnas: {len(df.columns)}")

    # Estructura
    print(f"\n  -- Estructura {'─' * 58}")
    for i, (c, t) in enumerate(df.dtypes.items(), 1):
        nulos = df[c].isna().sum()
        print(f"    {i:3d}. {c:<40s} {str(t):<20s} nulos={nulos:,}")

    # Valores unicos de Anio y Mes
    print(f"\n  -- Anios y Meses disponibles {'─' * 42}")
    if "Anio" in df.columns and "Mes" in df.columns:
        for anio in sorted(df["Anio"].unique()):
            meses = sorted(df[df["Anio"] == anio]["Mes"].unique())
            filas_anio = len(df[df["Anio"] == anio])
            print(f"    Anio {anio}: meses={meses}  filas={filas_anio:,}")
    else:
        print("    !! No se encontraron columnas 'Anio' y 'Mes'")
        # Buscar columnas similares
        for c in df.columns:
            if "anio" in c.lower() or "año" in c.lower() or "year" in c.lower():
                print(f"    Columna similar a anio: {c}")
            if "mes" in c.lower() or "month" in c.lower():
                print(f"    Columna similar a mes: {c}")

    # Encuestas disponibles
    print(f"\n  -- Encuestas disponibles {'─' * 47}")
    if "encuestaNombre" in df.columns:
        for enc in df["encuestaNombre"].unique():
            filas = len(df[df["encuestaNombre"] == enc])
            print(f"    {enc:<50s} filas={filas:,}")

    # Sedes
    print(f"\n  -- Sedes disponibles {'─' * 51}")
    if "sedeNombre" in df.columns:
        for sede in sorted(df["sedeNombre"].dropna().unique()):
            print(f"    {sede}")

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()