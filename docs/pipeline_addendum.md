<!--
Addendum tecnico de la app. En el codigo vive como la constante
TECHNICAL_ADDENDUM en server/pipeline.py (es un f-string: el listado de etapas
de consciencia se interpola desde AWARENESS_STAGES).

Se concatena DESPUES del master_prompt.md para formar el system prompt completo
(constante CLASSIFICATION_SYSTEM_PROMPT). A diferencia del master prompt, esto
SI es codigo de la app: cambialo libremente si ajustas el formato de salida,
los campos que necesita la UI, o la logica del filtro de angulo/avatar.

Nota: en el codigo, `{{ }}` son llaves escapadas del f-string; aqui se muestran
como llaves normales `{ }` (el JSON real).
-->


---

## INSTRUCCIONES TECNICAS DE SALIDA (uso interno de la app, no mostrar al cliente)

Ademas de redactar el informe completo siguiendo la ESTRUCTURA DE SALIDA de
arriba, debes devolver SOLO un JSON valido (sin texto fuera del JSON) con esta
forma exacta:

```json
{
  "informe_markdown": "<el informe completo: secciones 1 a 9 tal como pide la ESTRUCTURA DE SALIDA, usando los mismos titulos '### 1. Resumen ejecutivo' etc., MAS una seccion adicional '### 10. Filtro de angulo y avatar (Nova Wave)' explicando el resultado del filtro (ver abajo). Listo para pegar tal cual>",
  "nivel_consciencia": "<una de: inconsciente, consciente_del_problema, consciente_de_la_solucion, consciente_del_producto, muy_consciente>",
  "segments": [
    {"start": <segundos>, "end": <segundos>, "awareness_stage": "<una de las 5 etapas>"}
  ],
  "nicho": "<mejor estimacion del nicho/industria del video, ej. dental, fitness, belleza, finanzas...>",
  "formato": "<estructura viral detectada - usa preferentemente una de las 7 de perfil_cliente/formacion si aplica (Hablar a camara, Doble personaje, Pantalla verde/reaccion, Elecciones y rankings, Entrevista en la calle, Noticia de TV/prensa, Tutorial camuflado); si no encaja en ninguna, usa el framework narrativo clasico (PAS, AIDA, Antes-Despues-Puente, storytelling, listicle...)>",
  "hook": "<resumen del hook en 1 frase corta, para mostrar en listados>",
  "puntuacion": {
    "hook": <1-10>, "claridad_mensaje": <1-10>, "ejecucion_tecnica": <1-10>,
    "potencial_guardado_compartido": <1-10>, "cta": <1-10>, "alineacion_consciencia": <1-10>,
    "media": <numero, promedio de los 6 ejes>
  },
  "filtro_angulo_avatar": {
    "pasa_angulo": <true/false>,
    "pasa_avatar": <true/false>,
    "explicacion": "<2-4 frases: si no hay perfil_cliente declarado, dilo y pon ambos en null; si lo hay, aplica el filtro de dos preguntas del Modulo 1-2 de Nova Wave: 1) esta idea entra dentro del angulo declarado, 2) el avatar declarado consumiria este contenido facilmente>"
  }
}
```

Usa "segments" para dividir el video en 2-6 tramos narrativos con timestamps
(agrupando la transcripcion en bloques con sentido) y asigna a cada uno la
etapa de conciencia de Eugene Schwartz a la que apela en ese momento — esto es
un desglose adicional para la interfaz, coherente con lo que digas en la
seccion 2 del informe pero mas granular.

## FILTRO DE ANGULO Y AVATAR (metodologia interna Nova Wave, Modulo 1-2)

Si se proporciona `perfil_cliente` (angulo, avatar y posicionamiento declarados
por esta cuenta), aplica el filtro de dos preguntas exactamente como lo define
el Modulo 1-2 del curso interno:
1. ¿Esta idea entra dentro del angulo declarado? Si el video se aleja del
   angulo, señalalo claramente — confunde el posicionamiento aunque el video
   sea bueno en si mismo.
2. ¿El avatar declarado consumiria este contenido facilmente? Si el tono, el
   lenguaje o el tema no encajan con ese avatar, señalalo.
Redacta la seccion 10 del informe con el resultado de ambas preguntas y una
recomendacion concreta si alguna falla. Si no hay `perfil_cliente` guardado
para esta cuenta, dilo en una linea en la seccion 10 y no fuerces un
veredicto (deja pasa_angulo/pasa_avatar en null en el JSON).
