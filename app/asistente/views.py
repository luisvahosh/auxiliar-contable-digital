from django.shortcuts import render

from .models import ArticuloNormativo
from .rag import consultar


def asistente(request):
    pregunta = request.GET.get("q", "").strip()
    resultado = consultar(pregunta) if pregunta else None
    return render(request, "asistente/asistente.html", {
        "pregunta": pregunta,
        "resultado": resultado,
        "temas": ArticuloNormativo.objects.all(),
    })
