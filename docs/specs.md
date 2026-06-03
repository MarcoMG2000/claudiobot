# Proceso SDD (Spec Driven Development)

> Léelo antes de redactar o leer cualquier spec. Toda feature con `"sdd": true`
> pasa por este proceso.

## Los 3 archivos de un spec

Cada feature vive en `specs/<id>/` con tres ficheros:

1. **`requirements.md`** — QUÉ debe cumplirse, en notación **EARS** (ver abajo).
   Cada requisito tiene un identificador `R1, R2, …` para trazabilidad.
2. **`design.md`** — CÓMO se construye: módulos afectados, interfaces, tipos de
   datos, decisiones y alternativas descartadas. Respeta `docs/architecture.md`.
3. **`tasks.md`** — pasos concretos y ordenados, como checklist `[ ]`. Cada task
   referencia los `R<n>` que ayuda a cumplir.

## La puerta de aprobación humana

```
pending → [spec-author] → spec_ready → ⏸ HUMANO APRUEBA → in_progress → [implementer → reviewer] → done
```

Cuando el spec está listo, el `spec-author` cambia el status a `spec_ready` y el
**leader se detiene**. Ningún código se escribe hasta que el humano apruebe.

## Notación EARS (obligatoria en `requirements.md`)

EARS = *Easy Approach to Requirements Syntax*. Cada requisito sigue una de estas
plantillas, en frase única y verificable:

- **Ubiquitous:** "El sistema DEBE `<respuesta>`."
- **Event-driven:** "CUANDO `<disparador>`, el sistema DEBE `<respuesta>`."
- **State-driven:** "MIENTRAS `<estado>`, el sistema DEBE `<respuesta>`."
- **Unwanted behavior:** "SI `<condición no deseada>`, ENTONCES el sistema DEBE
  `<respuesta>`."
- **Optional:** "DONDE `<característica presente>`, el sistema DEBE `<respuesta>`."

Reglas:
- Un requisito = una frase verificable. Nada de "y/o" que esconda dos requisitos.
- Cada `R<n>` debe poder mapearse a **al menos un test** (ver
  `docs/verification.md`). Si no es testeable, está mal escrito.
- Ejemplo: "SI el score máximo de recuperación es menor que el umbral
  configurado, ENTONCES el sistema DEBE abstenerse y devolver `abstained = true`
  sin llamar al LLM." (R-grounding típico de este proyecto).

## Calidad de un buen spec en este proyecto

- Cubre el **contrato de grounding** cuando aplique (abstención, citas).
- Define las **interfaces** antes que las implementaciones.
- Lista qué se testea con **fakes** y qué con servicios reales (`integration`).
- No mezcla varias features; respeta `depends_on` de `feature-list.json`.
