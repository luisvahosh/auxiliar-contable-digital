from django.shortcuts import render


def inicio(request):
    """Página de inicio — día 1: el 'hola' visible del PLAN.md §8."""
    return render(request, "core/inicio.html")
