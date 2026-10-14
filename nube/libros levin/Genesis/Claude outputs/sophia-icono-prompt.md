# Icono de Sophia — prompt para el render 3D

## Antes de nada: un aviso que le va a ahorrar un disgusto

**Los generadores de imágenes no escriben hebreo ni griego de verdad.** Inventan letras que *parecen* hebreo y griego, y no lo son. A veces salen consonantes al revés, a veces signos que no existen.

En una app de dibujo eso da igual. **En una app para predicadores, no**: el día que alguien amplíe el icono y vea que el hebreo es falso, se acabó la credibilidad.

Así que le propongo esto, y es lo que yo haría:

**1. Usted genera el render 3D con las páginas del libro con renglones, pero SIN letras reales** — líneas de texto insinuadas, como cuando se ve un libro de lejos. El prompt de abajo ya lo pide así.

**2. Yo le monto encima el hebreo y el griego de verdad**, con el texto correcto y bien vocalizado, en el tamaño y la opacidad que toquen.

Así tiene las dos cosas: **el realismo del render y letras que aguantan que las amplíen.**

---

## El texto que yo pondría

La app se llama **Sophia**. En griego, **σοφία** es *sabiduría*. Y en hebreo, sabiduría es **חָכְמָה** (*jokmá*).

**Página izquierda: חָכְמָה — Página derecha: σοφία**

*(Los dos comprobados en el diccionario Strong: el hebreo es el número 2451 y el griego el 4678.)*

Es la misma palabra en los dos idiomas de la Biblia, y es el nombre de la app. No hace falta explicarlo: el que sepa, lo ve.

**Si prefiere otra cosa, dos alternativas buenas:**

- **«En el principio»** en los dos: **בְּרֵאשִׁית** (Génesis 1:1) y **ἐν ἀρχῇ** (Juan 1:1). Los dos Testamentos empiezan igual.
- **«Palabra»**: **דָּבָר** (*davar*) y **λόγος** (*logos*).

Dígame cuál y lo monto.

---

## El prompt (en inglés, que es como mejor responden)

Cópielo entero:

```
A premium 3D rendered mobile app icon. Squircle format (rounded square,
iOS/Android style), perfectly centered and symmetrical composition.

BACKGROUND: deep navy blue, rich and slightly gradated from a lighter
center to darker corners, with a soft warm radial glow behind the book.
Subtle vignette. No pattern, no texture, no border.

MAIN OBJECT: an open book, viewed from slightly above and in front,
occupying the lower two thirds of the icon. The covers and the page
edges are polished gold with realistic reflections, warm highlights and
a brushed metallic finish along the spine and the gilded edges. The
pages are thick cream-coloured vellum, gently curved and fanned, each
page catching light differently, with soft self-shadowing between them.
The paper has a fine grain, like real book paper. On the visible pages,
faint horizontal lines suggesting rows of printed text — blurred,
low contrast, no legible letters.

LIGHT SOURCE: above the book, a brilliant four-pointed star with a long
vertical axis and a shorter horizontal one, a warm white-gold core and a
soft radiant halo. Delicate lens flare. The star is the key light: it
casts a warm glow down onto the open pages and lights the golden edges
from above.

MATERIALS AND LIGHTING: photorealistic render, physically based
materials, real gold specular highlights, soft global illumination,
gentle contact shadow under the book, shallow depth of field kept
minimal so everything stays sharp.

STYLE: elegant, reverent, premium. Cinema4D / Octane quality. Clean and
uncluttered — it must remain recognisable at 48 pixels.

IMPORTANT: no lettering, no words, no alphabet characters anywhere,
no watermark, no signature, no frame. Square 1:1 aspect ratio,
1024x1024. Generous empty margin around the composition so nothing
touches the edges.
```

---

## Si el generador le pide un «negative prompt»

```
text, letters, words, typography, watermark, signature, logo, frame,
border, people, hands, cross, crucifix, dove, cluttered, busy detail,
low contrast, flat lighting, cartoon, flat vector, blurry, noisy
```

---

## Cómo sacarle el mejor resultado

**Genere varias.** Cuatro o cinco tiradas con el mismo prompt y quédese con la que tenga el libro más centrado y el margen más limpio.

**Lo que hay que mirar al elegir:**

1. **Que el libro no toque los bordes.** Android le recorta las esquinas, y en algunos móviles lo recorta en círculo. Si el libro llega al borde, se corta.
2. **Que sea simétrico.** Un icono torcido se nota mucho en la pantalla de inicio.
3. **Que el azul sea el mismo azul en toda la imagen de fondo** — sin manchas ni degradados raros en las esquinas.
4. **Que la estrella no se coma el libro.** Tiene que iluminarlo, no taparlo.
5. **Achíquela en la pantalla.** Si a tamaño de uña se sigue viendo «libro con estrella», está bien. Si se convierte en una mancha dorada, pruebe otra.

**Un truco:** si el generador le insiste en meter letras, añada al final del prompt «*the pages are blank, only faint horizontal ruling lines*».

---

## Qué necesito de usted, y qué hago yo

**Usted me manda:** el PNG que más le guste, lo más grande que se lo dé el generador (1024×1024 o más).

**Yo hago todo lo demás:**

- Le monto el **hebreo y el griego de verdad** en las páginas, con el texto correcto.
- Le recorto y ajusto el margen para que cumpla la zona segura de Android.
- Le genero **todos los tamaños que necesita la app**: mdpi 48, hdpi 72, xhdpi 96, xxhdpi 144, xxxhdpi 192, en `.webp` como ya los tiene.
- Le hago el **icono adaptativo** (el de Android 8 en adelante): fondo y primer plano separados, que es lo que hace que se vea bien tanto en cuadrado como en círculo o en gota.
- Le hago el de **512×512 para la ficha de Google Play**.
- Y le dejo todo instalado en `app\src\main\res\`, sustituyendo el icono por defecto que tiene ahora.

*(He mirado el proyecto: está en `AndroidStudioProjects\sophia` y **sigue con el icono verde por defecto de Android Studio**. Los archivos que hay que sustituir son los `ic_launcher.webp` y `ic_launcher_round.webp` de las cinco carpetas `mipmap`, más `ic_launcher_background.xml` e `ic_launcher_foreground.xml`.)*

---

## Una idea más, por si le interesa

El icono tiene que ser simple, pero **la pantalla de bienvenida de la app no**.

Ahí sí cabe el libro grande, con el hebreo y el griego legibles de verdad, el nombre **Sophia** debajo, y la estrella arriba. Es donde la gente se para dos segundos y donde una imagen bonita hace su trabajo.

Si quiere, cuando tengamos el icono le monto también esa pantalla con la misma imagen.
