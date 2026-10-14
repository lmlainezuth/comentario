# Script del comentario

Todo en local: nada de Supabase ni internet mientras escribe.

## Una sola vez

1. Datos que faltan (en la carpeta `descargar biblia`):
   `python descargar_tablas.py` (strong_diccionario, libros, capitulos, referencias cruzadas…)
2. Instalar Claude Code en Windows (instalador nativo) y entrar con tu cuenta Max:
   en PowerShell `irm https://claude.ai/install.ps1 | iex`, luego `claude` y elegir la cuenta.
   Necesita Git para Windows (git-scm.com) para poder ejecutar comandos.
3. Preparar la base local (tarda un minuto):
   ```
   cd C:\Users\sinle\AndroidStudioProjects\sophia\herramientas\comentario
   python preparar.py
   ```

## Cada libro

```
python orquestador.py plan Isaías          # propone tomos, capítulos, títulos y perlas
```
Revisa `trabajo\Isaias\plan.json` y `trabajo\Isaias\brief-libro.md` (puedes editarlos a mano).

```
python orquestador.py capitulo Isaías 1 1  # prueba: solo el capítulo 1 del tomo 1
python orquestador.py tomo Isaías 1        # el tomo entero: capítulos, introducción, volumenes.txt e índice
python orquestador.py estado Isaías        # qué está hecho y cuánto gastó cada llamada
```

- Cada capítulo: Claude lo escribe con `biblia.py`, `verificar.py` lo comprueba (citas, Strong, forma) y, si hay fallos, Claude los corrige (hasta 2 veces).
- Se guarda en `libros levin\Isaias\capitulo N\`. Los borradores y el registro quedan en `trabajo\Isaias\`.
- Si se acaba el límite semanal, para solo. Vuelve a lanzar el mismo comando y sigue donde se quedó.

## Herramientas sueltas

- `python biblia.py` — consultas (ver, heb, strong, con, busca, serie, pasaje, cruzadas, lxx, sefaria, titulos)
- `python verificar.py archivo.md` — comprobar cualquier capítulo, también los ya escritos
- `python serie.py` — reconstruir `_indice` (respeta las líneas que ya había)
- `BRIEF.md` — las reglas comunes que recibe Claude en cada capítulo (edítalas aquí si cambias de criterio)
