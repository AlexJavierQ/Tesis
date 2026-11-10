# -*- coding: utf-8 -*-
"""Pruebas de seguridad V1 sin llamadas al LLM ni modificar datos oficiales.

Ejecutar desde la raiz:
    python -m unittest pruebas.test_v1_consulta -v

Requiere httpx, dependencia de fastapi.testclient.
"""
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from fastapi.testclient import TestClient
from interfaces.api import app


ESTUDIANTE = {
    "usuario": "estudiante_prueba",
    "rol": "estudiante",
    "carreras": ["computacion"],
    "carrera": "computacion",
}
RESPUESTA = {
    "respuesta": "Respuesta de prueba con evidencia.",
    "con_respaldo": True,
    "modo": "general",
    "pregunta_interpretada": "¿Cuáles son los requisitos?",
    "citas": [{
        "fuente": "normativa.pdf", "pagina": 1, "seccion": "Requisitos",
        "documento_id": 1, "version": 1, "path": "computacion/global/normativa.pdf",
    }],
}


class PruebasConsultaV1(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.mock_sesion = self.stack.enter_context(
            patch("interfaces.api._sesion", return_value=ESTUDIANTE.copy()))
        self.stack.enter_context(
            patch("interfaces.api.rag.carreras", return_value=["computacion", "otra"]))
        self.stack.enter_context(
            patch("interfaces.api.rag.cursos", return_value=["Practicum 2"]))
        self.mock_rag = self.stack.enter_context(
            patch("interfaces.api.rag.responder", return_value=RESPUESTA))
        self.mock_metricas = self.stack.enter_context(
            patch("interfaces.api.metricas.registrar"))
        self.mock_dueno = self.stack.enter_context(
            patch("interfaces.api.historial.es_dueno", return_value=True))
        self.stack.enter_context(patch("interfaces.api.memoria.preparar", return_value=None))
        self.mock_guardar = self.stack.enter_context(
            patch("interfaces.api.historial.agregar_mensaje"))
        self.cl = TestClient(app)

    def preguntar(self, carrera="computacion", conversacion_id=None):
        return self.cl.post("/preguntar", json={
            "pregunta": "¿Cuáles son los requisitos?",
            "carrera": carrera,
            "modo": "general",
            "conversacion_id": conversacion_id,
        })

    def test_sin_sesion_devuelve_401_y_no_invoca_llm(self):
        self.mock_sesion.return_value = None
        resp = self.preguntar()
        self.assertEqual(resp.status_code, 401)
        self.mock_rag.assert_not_called()
        self.mock_metricas.assert_not_called()

    def test_carrera_ajena_devuelve_403(self):
        resp = self.preguntar(carrera="otra")
        self.assertEqual(resp.status_code, 403)
        self.mock_rag.assert_not_called()
        self.mock_metricas.assert_not_called()

    def test_conversacion_ajena_devuelve_403(self):
        self.mock_dueno.return_value = False
        resp = self.preguntar(conversacion_id=123)
        self.assertEqual(resp.status_code, 403)
        self.mock_rag.assert_not_called()
        self.mock_guardar.assert_not_called()

    def test_consulta_autorizada_responde_con_citas(self):
        resp = self.preguntar(conversacion_id=123)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["citas"][0]["version"], 1)
        self.assertEqual(resp.json()["citas"][0]["pagina"], 1)
        self.mock_rag.assert_called_once()
        self.mock_metricas.assert_called_once()
        self.assertEqual(self.mock_guardar.call_count, 2)


if __name__ == "__main__":
    unittest.main()
