"""
Test suite para el backend de Portal Encuestas Percepción
Pruebas de integración y unitarias para endpoints de orquestador
"""

import pytest
import json
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Agregar la raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from portal.backend.app import app
from portal.backend.schema import JobParamCreate, JobExecutionModel

client = TestClient(app)


class TestOrquestadorAPI:
    """Pruebas para los endpoints del orquestador"""

    def test_root_endpoint(self):
        """Prueba que el servidor esté respondiendo"""
        response = client.get("/")
        assert response.status_code == 200

    def test_orquestador_automatico(self):
        """Prueba el endpoint de orquestador automático"""
        payload = {
            "area": "TODAS",
            "auto_date": True
        }
        
        response = client.post(
            "/api/orquestador/run",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Puede ser 200, 202 o similar
        assert response.status_code in [200, 202, 201]
        assert "pid" in response.json() or "status" in response.json()

    def test_orquestador_manual_crai(self):
        """Prueba el endpoint de orquestador manual con CRAI 2026-05"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post(
            "/api/orquestador/run",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [200, 202, 201]
        data = response.json()
        assert "pid" in data or "status" in data

    def test_orquestador_diferentes_areas(self):
        """Prueba con diferentes áreas"""
        areas = ["CRAI", "CASA UR", "Consultorio Jurídico", "Cancillería UR"]
        
        for area in areas:
            payload = {
                "area": area,
                "anio": 2026,
                "mes": 5,
                "auto_date": False
            }
            
            response = client.post(
                "/api/orquestador/run",
                json=payload
            )
            
            assert response.status_code in [200, 202, 201], f"Falló para área {area}"

    def test_orquestador_validacion_campos(self):
        """Prueba validación de campos vacíos"""
        payload = {
            "area": "",
            "auto_date": False
        }
        
        response = client.post(
            "/api/orquestador/run",
            json=payload
        )
        
        # Debería aceptar pero usar valores por defecto
        assert response.status_code in [200, 201, 202, 422]

    def test_orquestador_anio_valido(self):
        """Prueba con año válido"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        assert response.status_code in [200, 201, 202]
        assert response.json() is not None

    def test_orquestador_mes_valido(self):
        """Prueba con mes válido (1-12)"""
        for mes in [1, 5, 12]:
            payload = {
                "area": "CRAI",
                "anio": 2026,
                "mes": mes,
                "auto_date": False
            }
            
            response = client.post("/api/orquestador/run", json=payload)
            assert response.status_code in [200, 201, 202], f"Falló para mes {mes}"

    def test_orquestador_cors_headers(self):
        """Prueba que CORS está correctamente configurado"""
        response = client.options(
            "/api/orquestador/run",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert response.status_code in [200, 204]

    def test_orquestador_response_json(self):
        """Prueba que la respuesta es JSON válido"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        
        try:
            data = response.json()
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Response no es JSON válido")

    def test_orquestador_estado_inicial(self):
        """Prueba que el status inicial es correcto"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        data = response.json()
        
        # Debe contener información de estado
        assert "status" in data or "pid" in data


class TestOrquestadorIntegracion:
    """Pruebas de integración del flujo completo"""

    def test_flujo_completo_crai_2026_mayo(self):
        """Prueba el flujo completo: CRAI, 2026, Mayo"""
        # 1. Iniciar orquestador
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        assert response.status_code in [200, 201, 202]
        data = response.json()
        
        # 2. Verificar que retorna ID de proceso
        pid = data.get("pid")
        if pid:
            assert pid > 0 or isinstance(pid, str)
        
        # 3. Verificar comando en respuesta
        if "command" in data:
            assert "CRAI" in data["command"]
            assert "2026" in data["command"]
            assert "5" in data["command"]

    def test_parametros_esperados_en_respuesta(self):
        """Prueba que la respuesta contiene los parámetros esperados"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        data = response.json()
        
        # La respuesta debe ser una estructura conocida
        assert isinstance(data, dict)
        assert len(data) > 0


class TestOrquestadorErrores:
    """Pruebas de manejo de errores"""

    def test_payload_vacio(self):
        """Prueba con payload vacío"""
        response = client.post(
            "/api/orquestador/run",
            json={}
        )
        
        # Podría rechazar o usar defaults
        assert response.status_code in [200, 201, 202, 422]

    def test_mes_invalido(self):
        """Prueba con mes inválido"""
        payload = {
            "area": "CRAI",
            "anio": 2026,
            "mes": 13,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        # Podría aceptar o rechazar, pero no debe fallar
        assert response.status_code < 500

    def test_anio_negativo(self):
        """Prueba con año negativo"""
        payload = {
            "area": "CRAI",
            "anio": -1,
            "mes": 5,
            "auto_date": False
        }
        
        response = client.post("/api/orquestador/run", json=payload)
        assert response.status_code < 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
