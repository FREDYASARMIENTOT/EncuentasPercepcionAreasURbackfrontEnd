# -*- coding: utf-8 -*-
"""
test_lanzador_parquet.py - Test rápido del módulo orquestador_parquet

Uso:
    python -m pytest backend/tests/test_lanzador_parquet.py -v
    python backend/tests/test_lanzador_parquet.py

Requiere: conda activate EncuestasBackendAzure
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.orquestador_parquet import ParquetReader, get_parquet_launcher, procesar_dataframe_melt
    IMPORT_OK = True
except ImportError as e:
    IMPORT_OK = False
    IMPORT_ERROR = str(e)


def test_import():
    """Verifica que el módulo se puede importar."""
    assert IMPORT_OK, f"No se pudo importar orquestador_parquet: {IMPORT_ERROR}"


def test_cargar_parquet():
    """Verifica que el parquet se carga correctamente."""
    if not IMPORT_OK:
        return
    df = ParquetReader.get_dataframe()
    assert len(df) > 0, "Parquet vacío"
    assert len(df.columns) == 30, f"Se esperaban 30 columnas, se encontraron {len(df.columns)}"
    print(f"  OK: {len(df):,} filas, {len(df.columns)} columnas")


def test_areas_disponibles():
    """Verifica que se obtienen áreas disponibles."""
    if not IMPORT_OK:
        return
    areas = ParquetReader.get_areas_disponibles(2026)
    assert len(areas) > 0, "No se encontraron áreas para 2026"
    assert "CRAI" in areas, f"CRAI no está en áreas: {areas[:5]}"
    print(f"  OK: {len(areas)} áreas disponibles")


def test_meses_disponibles():
    """Verifica que se obtienen meses disponibles."""
    if not IMPORT_OK:
        return
    meses = ParquetReader.get_meses_disponibles(2026)
    assert len(meses) > 0, "No se encontraron meses para 2026"
    assert 5 in meses, f"Mes 5 no está en meses: {meses}"
    print(f"  OK: meses {meses}")


def test_filtrar_datos():
    """Verifica que el filtrado por año/mes/área funciona."""
    if not IMPORT_OK:
        return
    df = ParquetReader.filtrar_datos(2026, 5, "CRAI")
    assert len(df) > 0, "No hay datos para CRAI mes 5"
    assert "areaNombre" in df.columns, "Falta columna areaNombre"
    assert "Año" in df.columns, "Falta columna Año"
    print(f"  OK: {len(df):,} filas filtradas para CRAI | 5/2026")


def test_filtrar_avanzado():
    """Verifica el filtrado avanzado con múltiples criterios."""
    if not IMPORT_OK:
        return
    df = ParquetReader.filtrar_datos_avanzado(anio=2026, mes=5, area="CRAI")
    assert len(df) > 0, "No hay datos en filtrado avanzado"
    print(f"  OK: {len(df):,} filas (avanzado)")


def test_procesar_dataframe():
    """Verifica que el procesamiento (melt + indicadores) funciona."""
    if not IMPORT_OK:
        return
    raw = ParquetReader.filtrar_datos(2026, 5, "CRAI")
    proc = procesar_dataframe_melt(raw)
    assert len(proc) > 0, "Procesamiento generó DataFrame vacío"
    assert "Indicador_0_100" in proc.columns, "Falta columna Indicador_0_100"
    assert "Métrica" in proc.columns, "Falta columna Métrica"
    metricas = proc["Métrica"].dropna().unique().tolist()
    assert "Atención" in metricas, f"Atención no en métricas: {metricas}"
    print(f"  OK: {len(raw):,} raw -> {len(proc):,} procesadas, métricas: {metricas}")


def test_resumen():
    """Verifica el resumen estadístico."""
    if not IMPORT_OK:
        return
    resumen = ParquetReader.get_resumen(2026, 5, "CRAI")
    assert resumen["rows"] > 0, "Resumen sin filas"
    assert resumen["encuestados"] > 0, "Resumen sin encuestados"
    print(f"  OK: {resumen}")


def test_launcher():
    """Verifica que ParquetLauncher funciona."""
    if not IMPORT_OK:
        return
    launcher = get_parquet_launcher()
    info = launcher.get_parquet_info()
    assert info["rows"] > 0, "Launcher sin datos"
    assert info["local_exists"], "Parquet local no existe"
    print(f"  OK: source={info['source']}, rows={info['rows']:,}")


if __name__ == '__main__':
    print("=" * 60)
    print("  TEST LANZADOR PARQUET - backend.orquestador_parquet")
    print("=" * 60)

    tests = [
        ("1. Import", test_import),
        ("2. Cargar parquet", test_cargar_parquet),
        ("3. Áreas disponibles", test_areas_disponibles),
        ("4. Meses disponibles", test_meses_disponibles),
        ("5. Filtrar datos", test_filtrar_datos),
        ("6. Filtrado avanzado", test_filtrar_avanzado),
        ("7. Procesar dataframe", test_procesar_dataframe),
        ("8. Resumen", test_resumen),
        ("9. Launcher", test_launcher),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name}: ERROR - {e}")
            failed += 1

    print(f"\n  Resultados: {passed} OK, {failed} FAIL de {len(tests)} tests")
    print("=" * 60)