# Encargo común: libro del maestro (serie Sophia)

Escribe **un archivo Markdown** de la serie de comentarios bíblicos de Mauricio, para maestros y predicadores evangélicos. La Biblia citada es la **RVR1960**. Lo que no sale del texto bíblico se dice como dato de fuera.

## 1. El propósito: perlas

El libro existe para sacar **perlas**: enseñanzas hondas y poco conocidas que un maestro rara vez oye hoy, y que salen de mirar el texto de cerca (una palabra que se repite en otro sitio, un verbo que cambia, un eco que en castellano no se ve). Ejemplos del gusto del autor: la semilla que cayó *junto al camino*; Bartimeo, ciego, que llama a Jesús *Hijo de David* porque conocía las Escrituras.
- **Una perla principal por capítulo**, anunciada con la frase fija: «Y aquí está la perla del capítulo.» Puede haber perlas menores.
- **Contar solo si da algo.** Un recuento («sale en dos versículos de toda la Biblia») vale cuando revela algo; contar por contar es relleno.
- No es un sermón: nada de «esto es para el que…», ni clímax en Cristo obligatorio. Cristo aparece cuando el texto lo trae, y entonces con todo su peso.
- La primera trampa a vigilar: dar por «la misma palabra» dos cosas que son el nombre y el verbo de una raíz, dos lemas con números distintos, o dos palabras que solo coinciden en castellano. Compruébalo siempre con `biblia.py heb` / `strong` antes de escribir «es la misma palabra».
- «Es la primera vez en la Biblia» casi siempre tiene un caso anterior: compruébalo con `biblia.py strong` o `busca`.

## 2. La voz

La de Génesis y Éxodo: apartados que nacen de observaciones del texto, **frases cortas**, trato de **usted**, honradez sobre lo que el texto no dice («el texto no lo dice»; «esto es una lectura, no lo que dice el versículo»). Negritas para la frase que el lector debe llevarse de cada párrafo (una o dos por párrafo, no más). Palabras sencillas: el lector es un maestro de escuela dominical, no un filólogo; el dato técnico se explica en la misma frase.

## 3. La forma exacta del archivo

Capítulo (`<prefijo>-<tomo 2 cifras>-<slug del tomo>-capNN.md`):

```
# Capítulo N
## «Título literal de la RVR1960»

### El texto

> «texto RVR1960 completo del pasaje, con **las palabras clave** en negrita»
> — Libro c:v-v

Párrafo de entrada: qué pasa en el pasaje y de qué va el capítulo (con la idea en negrita).

---

### Título de apartado (nacido de una observación)

> «el versículo o versículos de los que sale la idea, con **las palabras que trata** en negrita» (c:v)

Cuerpo del apartado…

---
(más apartados, 4 a 6 en total)

## Resumen del capítulo

1. c:v: … (una línea por apartado, con las palabras del original y las referencias)

---

## Preguntas de estudio

1. Lea c:v y … ¿…? (5 preguntas, cada una manda a leer un pasaje)

---

## NOTA PARA EL AUTOR

(3 a 6 líneas, ver §7)
```

- **Cada apartado `###` (salvo «El texto») empieza con su versículo citado** en bloque `>`, con la referencia entre paréntesis al final y en negrita las palabras que el apartado trata.
- Longitud: unos 22.000-28.000 caracteres el capítulo; 10.000-16.000 la introducción.
- Introducción del tomo (`…-introduccion.md`): `# Introducción` / `## Título propio` y prosa que presenta el tomo, sus hilos y lo que el lector va a encontrar, con enlaces a los capítulos del tomo. La introducción del tomo 1 es también la del libro entero. Sin «El texto», sin resumen ni preguntas; sí NOTA.

## 4. Las citas bíblicas

- **Toda cita entre «» es literal de la RVR1960** y lleva su referencia justo detrás: «…» (Isaías 1:18). Dentro del libro que se comenta basta «(1:18)»; **cualquier otro libro va siempre con su nombre**, aunque la cita anterior fuera de ese libro.
- Nunca de memoria: sácala con `python biblia.py ver "Libro c:v"`. Se puede cortar con «…».
- Referencias de varios versículos: «(1:18-20)», «(1:18; 2:3)»; nada de comas entre capítulos.
- Paráfrasis, glosas del diccionario, diálogos imaginados y traducciones de otras versiones van **en cursiva, sin comillas** (*prob. azafrán silvestre*; la LBLA traduce *…*).

## 5. El hebreo y el griego: las cuatro piezas

Cada palabra del original lleva, en este orden:

> «creó» (1:1) es בָּרָא *bará* (H1254)

1. la palabra castellana que traduce, entrecomillada; 2. el versículo; 3. la palabra en su alfabeto y la **transliteración en cursiva**, en el estilo sencillo del libro (*bará*, *rúaj*, *jésed*); 4. el número Strong **entre paréntesis**, **sobre el lema** (la forma del diccionario). Si interesa la forma del versículo: «*jimmadti*, de חָמַד *jamad* (H2530)».
- Nunca «en hebreo esta palabra significa» sin decir cuál es y dónde está.
- En prosa, nunca una H o G pegada a dígitos fuera de paréntesis (crea un número falso en la app): se escribe «el número 8000».
- Formas, recuentos y «misma palabra»: del **original de la app** (`biblia.py heb`, `strong`, `con`), numeración de la RVR1960. La RV1960+ (`biblia.py plus`) marca mal a veces: no cuentes con ella.
- La Septuaginta (`biblia.py lxx`), la tradición judía, la historia de la interpretación y las otras versiones son **dato de fuera**: se dicen como tales («la Septuaginta, la traducción griega antigua, dice… (dato de fuera)»; «Un dato de la historia.») y el argumento no depende de ellos. Nada de tradición rabínica posterior como autoridad en el cuerpo.

## 6. Lo ya estudiado: enlaces

Si algo ya se trató en otro capítulo de la serie, **dígaselo al lector y enlácelo**, con este formato exacto (el título, en cursiva, tal como está en la serie):

> como vimos en Cantares, tomo 1, capítulo 3 (*Tus ojos son como palomas*)

- `python biblia.py pasaje "Salmos 45:7"` dice qué capítulo tiene ese versículo como texto principal; `python biblia.py serie "frase"` dice dónde se trató algo.
- Un enlace por asunto y capítulo; nunca pegado dentro de una cita. Los capítulos del mismo libro que aún no existen se enlazan con el título del plan.
- Si el plan asigna un hilo a otro capítulo (su «dueño»), aquí solo se anuncia en una o dos frases y se enlaza.

## 7. Prohibido en el cuerpo, y la NOTA corta

- Nada de «grado de seguridad», actas («Cotejado sobre…»), fechas, «compruébelo», ni avisos al lector de que algo está sin verificar: **la verificación la hacemos nosotros**.
- **NOTA PARA EL AUTOR, 3 a 6 líneas**, solo con: (a) datos de fuera usados y de dónde; (b) lo que el autor tiene que decidir; (c) correcciones que tocan a otros libros de la serie. Nada de listas de citas, números Strong ni recuentos: eso lo registra el programa.

## 8. Herramientas (todo local, sin internet)

```
python biblia.py ver "Isaías 1:1-9"        python biblia.py heb "Isaías 1:18"
python biblia.py strong H3198              python biblia.py con H2530 H6529
python biblia.py busca "frase de la RVR"   python biblia.py serie "frase"
python biblia.py pasaje "Salmos 45:7"      python biblia.py cruzadas "Isaías 53:5"
python biblia.py lxx "Isaías 7:14"         python biblia.py sefaria "Malaquías 3:19"
python verificar.py <archivo.md> --plan <plan.json>
```
Antes de terminar, **pasa `verificar.py` a tu archivo y corrige todo lo que marque** (FALLO, SINREF, STRONG, FORMA). Escribe el archivo con la herramienta Write en la ruta que te dé el encargo, en UTF-8.
