ra  como usuario ejecutarlos, si son  varas centencias  puedes  crear a rchivos ps1.# -*- coding: utf-8 -*-
"""Test rápido del lanzador parquet."""
import sys
from pathlib import Path

# Agregar root al path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.orquestador_parquet import ParquetReader, get_parquet_launcher

def main():
    print("=" * 60)
    print("  TEST LANZADOR PARQUET")
    print("=" * 60)
    
    # 1. Cargar parquet
    print("\n[1] Cargando parquet...")
    try:
        df = ParquetReader.get_dataframe()
        print(f"    OK - Filas: {len(df):,} | Columnas: {len(df.columns)}")
        print(f"    Fuente: {ParquetReader._cached_source}")
    except Exception as e:
        print(f"    ERROR: {e}")
        return
    
    # 2. Info básica
    print("\n[2] Información del parquet...")
    info = ParquetReader.get_info()
    for k, v in info.items():
        print(f"    {k}: {v}")
    
    # 3. Áreas disponibles
    print("\n[3] Áreas disponibles (2026)...")
    areas = ParquetReader.get_areas_disponibles(2026)
    print(f"    Total áreas: {len(areas)}")
    for a in areas[:10]:
        print(f"    - {a}")
    if len(areas) > 10:
        print(f"    ... y {len(areas) - 10} más")
    
    # 4. Meses disponibles
    print("\n[4] Meses disponibles (2026)...")
    meses = ParquetReader.get_meses_disponibles(2026)
    print(f"    Meses: {meses}")
    
    # 5. Filtrar datos
    if areas:
        area_test = areas[0]
        mes_test = meses[0] if meses else 1
        print(f"\n[5] Filtrando datos: area='{area_test}', mes={mes_test}, anio=2026...")
        df_filt = ParquetReader.filtrar_datos(2026, mes_test, area_test)
        print(f"    Filas filtradas: {len(df_filt):,}")
        if not df_filt.empty:
            print(f"    Columnas: {list(df_filt.columns[:10])}...")
    
    # 6. Resumen
    print("\n[6] Resumen estadístico...")
    resumen = ParquetReader.get_resumen(2026)
    for k, v in resumen.items():
        print(f"    {k}: {v}")
    
    # 7. Test ParquetLauncher
    print("\n[7] Test ParquetLauncher...")
    launcher = get_parquet_launcher()
    launcher_info = launcher.get_parquet_info()
    print(f"    Info launcher: rows={launcher_info.get('rows')}, source={launcher_info.get('source')}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETADO")
    print("=" * 60)

if __name__ == '__main__':
    main()