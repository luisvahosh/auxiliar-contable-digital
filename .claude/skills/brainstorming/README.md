# Skill Brainstorming — Ideación Estructurada

Este skill ayuda a **estructurar la ideación** cuando inicia una nueva funcionalidad, evitando ambigüedades desde el principio y explorando trade-offs.

## Cuándo usar

✅ Funcionalidad nueva en un módulo existente  
✅ Mejora significativa que afecta múltiples partes  
✅ Corrección compleja que requiere decisión arquitectónica  
✅ Integración con sistema externo  
✅ Cambio en un modelo o flujo del usuario

❌ Correcciones triviales (bug manifiesto)  
❌ Ya tienes una estrategia clara y quieres ejecutar  
❌ Preguntas conceptuales sin un problema concreto

## Ejemplo de uso

```bash
/brainstorming Agregar validación de CUFE duplicado en facturas de venta
```

El skill te hará preguntas sobre:
- ¿Solo en carga de XML o también en digitación manual?
- ¿Qué hacer con duplicados: rechazar, avisar, fusionar?
- ¿Comparación por empresa o global?

Luego presentará alternativas con esfuerzo, módulos afectados y trade-offs.

## Qué sale

1. **Aclaración de requisitos** — lo que entendió, confirmado contigo
2. **2-3 alternativas** — cada una con ventajas/desventajas/esfuerzo
3. **Recomendación** — cuál elegir y por qué
4. **Siguiente paso** — qué hacer exactamente (qué archivo leer, qué test escribir, etc.)

## Convenciones del proyecto que el skill conoce

El skill está informado sobre:

- **Alcance:** "asistir, no reemplazar" (la app apoya, no sustituye Alegra/Siigo/Nominapp)
- **Multi-tenant:** toda query filtra por empresa, URLs con UUID
- **Humano en circuito:** niveles automática/sugerida/manual explícitos
- **Seguridad:** defusedxml para XML, no loguear datos financieros, minimizar a IA
- **UI:** español, mobile-first, números tabulares en contabilidad
- **Config:** todo por `.env`, nada quemado
- **Arquitectura actual:** Django modular, 229+ tests, Postgres en prod

## Después de brainstorming

El skill te propone un siguiente paso concreto. Típicamente:

- **Leer** `app/modulo/models.py` para entender la estructura
- **Escribir tests** del caso nuevo (TDD)
- **Revisar** qué models/views existentes se tocan
- **Crear la rama** con un nombre descriptivo

Luego sí ejecutas el trabajo de desarrollo. Si en el camino encontras un giro importante, puedes invocar `/brainstorming` de nuevo — la conversación es fluida.

## No necesitas memorizar nada

El skill está diseñado para hacer la conversación clara y estructurada. Si algo no queda claro después de sus preguntas, dile al skill: "no me queda clara la diferencia entre la opción A y B, explica más."
