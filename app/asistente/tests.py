"""
Pruebas del asistente normativo (RAG con respaldo por términos).
"""
from unittest.mock import patch

from django.urls import reverse

from core.pruebas import CasoConEmpresa

from .models import ArticuloNormativo
from .rag import consultar, recuperar


class PruebasCorpus(CasoConEmpresa):
    def test_la_semilla_carga_el_corpus(self):
        self.assertGreaterEqual(ArticuloNormativo.objects.count(), 10)
        self.assertTrue(ArticuloNormativo.objects.filter(
            tema="retencion-honorarios").exists())


class PruebasRecuperacionPorTerminos(CasoConEmpresa):
    """Sin embeddings, el RAG cae a coincidencia de términos (sin API)."""

    def test_recupera_por_palabras_clave(self):
        fichas = recuperar("¿qué retención aplica a los honorarios?")
        self.assertTrue(fichas)
        self.assertIn("honorarios", fichas[0].titulo.lower())

    def test_pregunta_de_iva_trae_la_ficha_de_iva(self):
        fichas = recuperar("tarifa general del IVA en ventas")
        temas = [f.tema for f in fichas]
        self.assertIn("iva-responsables", temas)


class PruebasConsulta(CasoConEmpresa):
    def test_respuesta_sin_llm_entrega_las_fichas(self):
        # Sin NVIDIA_API_KEY el LLM no responde: se devuelven las fichas
        with patch.dict("os.environ", {"NVIDIA_API_KEY": ""}):
            resultado = consultar("retención por servicios")
        self.assertTrue(resultado["fuentes"])
        self.assertIn("disclaimer", resultado)
        self.assertIn("contador", resultado["disclaimer"])

    def test_respuesta_con_llm_usa_el_contexto(self):
        falsa = type("R", (), {"ok": True, "json": lambda self: {
            "choices": [{"message": {"content": "Según el art. 392, 4%."}}]}})()
        with patch.dict("os.environ", {"NVIDIA_API_KEY": "nvapi-x"}), \
             patch("asistente.rag.requests.post", return_value=falsa):
            resultado = consultar("retención servicios")
        self.assertIn("art. 392", resultado["respuesta"])

    def test_pregunta_sin_coincidencia_avisa(self):
        with patch.dict("os.environ", {"NVIDIA_API_KEY": ""}):
            resultado = consultar("zzzz qwerty xkcd")
        self.assertEqual(resultado["fuentes"], [])
        self.assertIn("No encontré", resultado["respuesta"])

    def test_la_vista_responde(self):
        respuesta = self.client.get(reverse("asistente:asistente"),
                                    {"q": "retención honorarios"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Fuentes citadas")
        self.assertContains(respuesta, "art. 392")

    def test_la_vista_sin_pregunta_muestra_el_formulario(self):
        respuesta = self.client.get(reverse("asistente:asistente"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Tu pregunta")


class PruebasBusquedaSemantica(CasoConEmpresa):
    def test_usa_embeddings_cuando_hay(self):
        # Dos fichas con embeddings; la pregunta se acerca a una
        a = ArticuloNormativo.objects.get(tema="retencion-honorarios")
        b = ArticuloNormativo.objects.get(tema="iva-responsables")
        a.embedding = [1.0, 0.0]; a.save()
        b.embedding = [0.0, 1.0]; b.save()
        ArticuloNormativo.objects.exclude(pk__in=[a.pk, b.pk]).update(embedding=None)
        with patch("asistente.rag.embed", return_value=[0.9, 0.1]):
            fichas = recuperar("algo", k=1)
        self.assertEqual(fichas[0].tema, "retencion-honorarios")
