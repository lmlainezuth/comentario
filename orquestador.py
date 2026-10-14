"""
Escribe el comentario tomo por tomo con Claude Code (tu plan Max), verificando cada capítulo en local.

  python orquestador.py plan Isaías            propone el plan del libro (tomos, capítulos, títulos, perlas)
  python orquestador.py tomo Isaías 1          escribe, verifica y guarda el tomo 1; luego para
  python orquestador.py capitulo Isaías 1 3    solo un capítulo (para probar)
  python orquestador.py estado Isaías          qué está hecho y cuánto ha gastado
Requisitos: Claude Code instalado ('claude' en el PATH) y 'python preparar.py' hecho una vez.
"""
import json, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
import config
from config import AQUI, TRABAJO, LIBROS, MODELO, MAX_TURNOS, REINTENTOS_CORRECCION
from comun import db, ORDEN, PREFIJOS, libro_canonico, carpeta_de, parse_ref, norm, sin_tildes
import verificar, serie

PY = Path(sys.executable).name.replace(".exe", "") or "python"


class LimiteAlcanzado(Exception):
    pass


# --- utilidades ---------------------------------------------------------------
def dir_libro(libro):
    d = TRABAJO / carpeta_de(libro)
    (d / "borrador").mkdir(parents=True, exist_ok=True)
    return d


def cargar_plan(libro):
    p = dir_libro(libro) / "plan.json"
    if not p.exists():
        sys.exit(f"No hay plan para {libro}. Ejecuta: python orquestador.py plan {libro}")
    return json.loads(p.read_text(encoding="utf-8"))


def estado(libro):
    p = dir_libro(libro) / "estado.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def guardar_estado(libro, e):
    (dir_libro(libro) / "estado.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def slug(s):
    s = sin_tildes(s).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def nombre_archivo(plan, tomo, cap=None):
    base = f"{plan['prefijo']}-{tomo['tomo']:02d}-{tomo.get('slug') or slug(tomo['titulo'])}"
    return f"{base}-cap{cap:02d}.md" if cap else f"{base}-introduccion.md"


def destino(plan, tomo, archivo):
    return LIBROS / carpeta_de(plan["libro"]) / f"capitulo {tomo['tomo']}" / archivo


# --- Claude Code ---------------------------------------------------------------
def claude(encargo, instruccion, libro, etiqueta, reanudar=None, turnos=MAX_TURNOS):
    exe = shutil.which("claude")
    if not exe:
        sys.exit("No encuentro 'claude'. Instala Claude Code y entra con tu cuenta (claude en una terminal).")
    herramientas = [f"Bash({PY} biblia.py:*)", f"Bash({PY} verificar.py:*)", "Read", "Write", "Edit", "Glob", "Grep"]
    cmd = [exe, "-p", instruccion, "--output-format", "stream-json", "--verbose", "--include-partial-messages", "--strict-mcp-config", "--model", MODELO,
           "--max-turns", str(turnos), "--permission-mode", "acceptEdits",
           "--allowedTools", *herramientas, "--add-dir", str(TRABAJO)]
    if reanudar:
        cmd += ["--resume", reanudar]
    t0 = time.time()
    print(f"   [{etiqueta}] trabajando...", flush=True)
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", cwd=str(AQUI),
                          env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    pr.stdin.write(encargo); pr.stdin.close()
    salida, otras, escrito = None, [], 0
    for linea in pr.stdout:
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            if linea.strip():
                otras.append(linea.rstrip()); print("   !", linea.rstrip()[:200], flush=True)
            continue
        if ev.get("type") == "stream_event":
            d = ev.get("event", {}).get("delta", {})
            n = len(d.get("text") or d.get("partial_json") or d.get("thinking") or "")
            if n:
                escrito += n
                if escrito // 3000 != (escrito - n) // 3000:
                    print(f"     {time.time() - t0:5.0f}s escribiendo... {escrito // 1000} mil caracteres", flush=True)
            continue
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    x = c.get("input", {})
                    det = x.get("command") or x.get("file_path") or x.get("pattern") or ""
                    print(f"   · {time.time() - t0:5.0f}s {c.get('name')}: {str(det)[:110]}", flush=True)
        elif ev.get("type") == "result":
            salida = ev
    pr.wait()
    if salida is None:
        salida = {"is_error": True, "result": "\n".join(otras) or f"claude terminó con código {pr.returncode}"}
    texto = str(salida.get("result", ""))
    reg = {"cuando": datetime.now().isoformat(timespec="seconds"), "que": etiqueta,
           "segundos": round(time.time() - t0), "turnos": salida.get("num_turns"),
           "coste_equivalente_usd": salida.get("total_cost_usd"), "uso": salida.get("usage"),
           "error": salida.get("is_error")}
    with open(dir_libro(libro) / "registro.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    bajo = texto.lower()
    if salida.get("is_error") and any(k in bajo for k in ("limit", "límite", "usage", "rate")):
        raise LimiteAlcanzado(texto[:300])
    if salida.get("is_error"):
        print("   Claude devolvió un error:", texto[:300])
    return salida.get("session_id"), texto


# --- encargo de un capítulo ------------------------------------------------------
def texto_pasaje(libro, pasaje):
    _, vv = parse_ref(f"{libro} {pasaje}")
    q = "select texto from rvr where lo=? and cap=? and ver=?"
    return vv, "\n".join(f"{c}:{v} {db().execute(q, (lo, c, v)).fetchone()[0]}" for lo, c, v in vv)


def hebreo_pasaje(vv):
    lineas = []
    for lo, c, v in vv:
        ps = db().execute("select palabra, translit, group_concat(strong,'/') from orig where lo=? and cap=? and ver=? "
                          "group by pos order by pos", (lo, c, v)).fetchall()
        lineas.append(f"{c}:{v} " + " · ".join(f"{p} {t} {s}" for p, t, s in ps))
    return "\n".join(lineas)


def ya_en_la_serie(libro, vv, maximo=40):
    vistos, out = set(), []
    for lo, c, v in vv:
        clave = f"%{norm(libro)} {c} {v} %"
        for lib, tomo, cap, tit in db().execute(
                "select libro, tomo, cap, titulo from serie where n like ? limit 6", (clave,)):
            k = (lib, tomo, cap)
            if k not in vistos:
                vistos.add(k)
                donde = "introducción" if cap == "intro" else f"capítulo {cap}"
                out.append(f"- {c}:{v} ya citado en {lib}, tomo {tomo}, {donde} (*{tit}*)")
    return "\n".join(out[:maximo]) or "(ningún capítulo de la serie cita todavía estos versículos)"


def lista_capitulos(plan):
    out = []
    for t in plan["tomos"]:
        out.append(f"Tomo {t['tomo']} «{t['titulo']}» ({t['pasaje']}); introducción: *{t.get('titulo_intro', '')}*")
        for c in t["capitulos"]:
            dueno = f" — dueño de: {', '.join(c.get('hilos', []))}" if c.get("hilos") else ""
            out.append(f"  cap {c['cap']} ({c['pasaje']}) *{c['titulo']}*{dueno}")
    return "\n".join(out)


def encargo_capitulo(plan, tomo, cap, ruta):
    libro = plan["libro"]
    vv, rvr = texto_pasaje(libro, cap["pasaje"])
    brief_libro = (dir_libro(libro) / "brief-libro.md")
    return f"""{(AQUI / 'BRIEF.md').read_text(encoding='utf-8')}

# Encargo del libro: {libro}

{brief_libro.read_text(encoding='utf-8') if brief_libro.exists() else ''}

## Plan del libro (títulos para enlazar dentro de {libro})
{lista_capitulos(plan)}

# ESTE CAPÍTULO

- {libro}, tomo {tomo['tomo']} «{tomo['titulo']}», capítulo {cap['cap']}
- Título (literal de la RVR1960): «{cap['titulo']}»
- Pasaje: {libro} {cap['pasaje']}
- Perla prevista: {cap.get('perla', '(búscala tú)')}
- Hilos de los que este capítulo es dueño: {', '.join(cap.get('hilos', [])) or '(ninguno)'}
- Notas del plan: {cap.get('notas', '')}
- Escribe el archivo en: {ruta}
- Comprueba con: {PY} verificar.py "{ruta}" --plan "{dir_libro(libro) / 'plan.json'}"

## Texto RVR1960 del pasaje
{rvr}

## Original (TAHOT/TAGNT, numeración RVR): palabra · transliteración · Strong
{hebreo_pasaje(vv)}

## Dónde cita ya la serie estos versículos (para enlazar)
{ya_en_la_serie(libro, vv)}
"""


def encargo_intro(plan, tomo, ruta):
    libro = plan["libro"]
    resumenes = []
    for c in tomo["capitulos"]:
        p = destino(plan, tomo, nombre_archivo(plan, tomo, c["cap"]))
        if p.exists():
            t = p.read_text(encoding="utf-8")
            i, j = t.find("## Resumen del capítulo"), t.find("## Preguntas de estudio")
            resumenes.append(f"### Capítulo {c['cap']} *{c['titulo']}* ({c['pasaje']})\n{t[i:j] if i >= 0 else ''}")
    brief_libro = dir_libro(libro) / "brief-libro.md"
    return f"""{(AQUI / 'BRIEF.md').read_text(encoding='utf-8')}

# Encargo del libro: {libro}
{brief_libro.read_text(encoding='utf-8') if brief_libro.exists() else ''}

## Plan del libro
{lista_capitulos(plan)}

# ESTA INTRODUCCIÓN
- {libro}, tomo {tomo['tomo']} «{tomo['titulo']}» ({tomo['pasaje']}). Título propio: «{tomo.get('titulo_intro', '')}»
- {'Es también la introducción de todo el libro.' if tomo['tomo'] == 1 else ''}
- Escribe el archivo en: {ruta}
- Comprueba con: {PY} verificar.py "{ruta}" --plan "{dir_libro(libro) / 'plan.json'}"
- Puedes leer los capítulos del tomo en: {destino(plan, tomo, 'x').parent}

## Resúmenes de los capítulos del tomo
{chr(10).join(resumenes)}
"""


# --- un archivo: escribir, verificar, corregir, guardar ----------------------------
INSTRUCCION = ("Lee el encargo que te paso por la entrada estándar y escribe el archivo que pide, "
               "en la ruta indicada, siguiendo todas sus reglas. Usa las herramientas locales para "
               "cada cita y cada dato del original. Al terminar, pasa verificar.py y corrige lo que marque. "
               "Responde solo con una línea: HECHO.")


def producir(plan, tomo, cap=None):
    libro = plan["libro"]
    archivo = nombre_archivo(plan, tomo, cap["cap"] if cap else None)
    borrador = dir_libro(libro) / "borrador" / archivo
    final = destino(plan, tomo, archivo)
    e = estado(libro)
    if e.get(archivo, {}).get("hecho") and final.exists():
        print(f"   {archivo}: ya estaba")
        return True
    print(f"-> {archivo}")
    encargo = encargo_capitulo(plan, tomo, cap, borrador) if cap else encargo_intro(plan, tomo, borrador)
    sesion, _ = claude(encargo, INSTRUCCION, libro, archivo)
    validos = verificar.titulos_validos(plan)
    for intento in range(REINTENTOS_CORRECCION + 1):
        if not borrador.exists():
            print("   no se escribió el archivo")
            return False
        inf = verificar.verificar(borrador, libro, plan, validos)
        print("   " + verificar.resumen(inf).replace("\n", "\n   "))
        if inf["limpio"] or intento == REINTENTOS_CORRECCION:
            break
        sesion, _ = claude("Informe de verificar.py:\n\n" + verificar.resumen(inf),
                           "Corrige en el archivo todo lo que marca este informe (lo tienes en la entrada estándar). "
                           "Cita siempre desde biblia.py. Vuelve a pasar verificar.py. Responde: HECHO.",
                           libro, archivo + " (corrección)", reanudar=sesion)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(borrador.read_bytes())
    e[archivo] = {"hecho": True, "limpio": inf["limpio"], "cuando": datetime.now().isoformat(timespec="seconds"),
                  "fallos": len(inf["cotejo"]["fallos"]), "avisos": len(inf["strong"]["avisos"]) + len(inf["forma"])}
    guardar_estado(libro, e)
    print(f"   guardado en {final}")
    return True


def volumenes(plan, tomo):
    vt = LIBROS / carpeta_de(plan["libro"]) / "volumenes.txt"
    lineas = vt.read_text(encoding="utf-8").splitlines() if vt.exists() else []
    clave = f"{tomo['tomo']:02d}="
    lineas = [l for l in lineas if not l.startswith(clave)] + [clave + tomo["titulo"]]
    vt.write_text("\n".join(sorted(lineas)) + "\n", encoding="utf-8")


def actualizar_indices(plan, tomo):
    rg = {nombre_archivo(plan, tomo): f"{plan['libro']} {tomo['pasaje'].replace('-', ' – ', 1)}"}
    n = serie.reconstruir_indice(rangos=rg)
    import preparar, sqlite3
    con = sqlite3.connect(str(config.DB))
    con.execute("delete from serie"); con.execute("delete from pasajes"); con.commit()
    preparar.cargar_serie(con); con.commit(); con.close()
    print(f"Índice y base actualizados ({n} archivos en la serie).")


# --- comandos ------------------------------------------------------------------
def cmd_plan(libro):
    d = dir_libro(libro)
    lo = ORDEN[libro]
    caps = db().execute("select max(cap) from rvr where lo=?", (lo,)).fetchone()[0]
    titulos = "\n".join(f"{c}:{vi} {t}" for c, vi, t in db().execute(
        "select cap, vi, titulo from titulos where lo=? order by cap, vi", (lo,)))
    usados = {t for (t,) in db().execute("select distinct titulo from serie")}
    # Tambien los titulos ya planeados en otros libros (tomos aun sin escribir)
    for otro in TRABAJO.glob("*/plan.json"):
        if otro.parent == d:
            continue
        try:
            op = json.loads(otro.read_text(encoding="utf-8"))
            for t in op["tomos"]:
                usados.add(t["titulo"]); usados.update(c["titulo"] for c in t["capitulos"])
        except (ValueError, KeyError):
            pass
    usados = "\n".join(f"- {t}" for t in sorted(usados))
    # Bloques de lectura de unos 6 capitulos, calculados para este libro
    fin = dict(db().execute("select cap, max(ver) from rvr where lo=? group by cap", (lo,)).fetchall())
    bloques = [f'"{libro} {a}:1-{min(a + 5, caps)}:{fin[min(a + 5, caps)]}"' for a in range(1, caps + 1, 6)]
    bloques = ", ".join(bloques)
    encargo = f"""{(AQUI / 'BRIEF.md').read_text(encoding='utf-8')}

# TAREA: el plan de {libro} ({caps} capítulos)

Lee el libro entero por bloques, una llamada `biblia.py ver` por bloque y no capítulo a capítulo: {bloques}. Después propón:

1. **{d / 'plan.json'}** con esta forma exacta:
{{"libro": "{libro}", "prefijo": "{PREFIJOS.get(libro, slug(libro)[:4])}", "serie": "profetas",
  "tomos": [{{"tomo": 1, "titulo": "frase literal de la RVR1960 del tomo", "slug": "slug-del-titulo",
             "pasaje": "1:1-5:30", "titulo_intro": "título propio de la introducción",
             "capitulos": [{{"cap": 1, "pasaje": "1:1-9", "titulo": "frase literal de la RVR1960",
                            "perla": "la perla prevista en una frase", "hilos": ["hilo del que es dueño"],
                            "notas": "lo que este capítulo debe anunciar y enlazar"}}]}}]}}
   - **`cap` vuelve a empezar en 1 en cada tomo** (como en toda la serie). Para nombrar un capítulo de este libro en las notas, siempre «tomo T, capítulo N».
   - Tomos de 5-8 capítulos; capítulos por unidades de sentido del texto (no por los capítulos de la Biblia), de 8 a 25 versículos. Todo el libro cubierto, sin huecos ni solapes.
   - Títulos de tomo y capítulo: **frases literales de la RVR1960** (compruébalas con `biblia.py busca`), con sentido, y **que no estén ya usadas en la serie** (lista abajo).
2. **{d / 'brief-libro.md'}**: la postura del libro (lo que todos los capítulos dicen igual: autor, contexto, cómo se lee la profecía y su cumplimiento, cómo aparece Cristo), el **mapa de hilos** (palabra o imagen que recorre el libro → capítulo dueño que la desarrolla; los demás la anuncian y enlazan) y las perlas previstas. Máximo 2 páginas.

Busca perlas de verdad con las herramientas (`strong`, `con`, `cruzadas`, `pasaje`, `serie`): ecos con otros libros ya escritos de la serie, palabras raras, hilos que cruzan la Biblia. Responde solo: HECHO.

## Títulos de sección de la RVR (orientación)
{titulos}

## Títulos ya usados en la serie (no repetir)
{usados}
"""
    claude(encargo, "Lee la tarea de la entrada estándar y escribe los dos archivos que pide. Responde: HECHO.",
           libro, "plan", turnos=150)
    p = d / "plan.json"
    if p.exists():
        plan = json.loads(p.read_text(encoding="utf-8"))
        n = sum(len(t["capitulos"]) for t in plan["tomos"])
        print(f"Plan: {len(plan['tomos'])} tomos, {n} capítulos -> {p}")
        problemas = revisar_plan(libro)
        if problemas:
            print("PROBLEMAS en el plan (corrígelos o pásamelos antes de escribir):")
            print("\n".join("   - " + x for x in problemas))
        else:
            print("Plan revisado: todo el libro cubierto, títulos literales y sin repetir. Puedes lanzar los tomos.")
    else:
        print("No se escribió el plan.")


def revisar_plan(libro):
    """Lo que antes revisaba Claude a mano: todo el libro cubierto sin huecos ni
    solapes, titulos literales de la RVR1960 y sin repetir en la serie ni en otros
    planes, y capitulos numerados desde 1 en cada tomo (eso lo arregla solo).
    Tambien aparta los archivos sueltos que deja el plan. Devuelve los problemas."""
    d = dir_libro(libro)
    p = d / "plan.json"
    plan = json.loads(p.read_text(encoding="utf-8"))
    lo = ORDEN[plan["libro"]]
    llano = lambda t: " ".join(re.sub(r"[^a-zñ ]", "", sin_tildes(t).lower()).split())
    texto = " ".join(llano(t) for (t,) in db().execute("select texto from rvr where lo=?", (lo,)))
    fin = dict(db().execute("select cap, max(ver) from rvr where lo=? group by cap", (lo,)).fetchall())
    # Los del propio libro no cuentan: ya escritos, sus titulos estan en la serie
    usados = {llano(t) for (t,) in db().execute(
        "select distinct titulo from serie where libro <> ?", (plan["libro"],))}
    for otro in TRABAJO.glob("*/plan.json"):
        if otro.parent != d:
            try:
                for t in json.loads(otro.read_text(encoding="utf-8"))["tomos"]:
                    usados.add(llano(t["titulo"])); usados.update(llano(c["titulo"]) for c in t["capitulos"])
            except (ValueError, KeyError):
                pass
    problemas, vistos, cambiado = [], [], False
    for t in plan["tomos"]:
        base = min(c["cap"] for c in t["capitulos"]) - 1
        if base:
            for c in t["capitulos"]:
                c["cap"] -= base
            cambiado = True
            print(f"   Tomo {t['tomo']}: capítulos renumerados desde 1 (revisa en las notas las referencias «capítulo N»).")
        for nombre, titulo in [(f"tomo {t['tomo']}", t["titulo"])] + \
                [(f"tomo {t['tomo']} cap {c['cap']}", c["titulo"]) for c in t["capitulos"]]:
            if llano(titulo) not in texto:
                problemas.append(f"{nombre}: «{titulo}» no es literal de la RVR1960")
            if llano(titulo) in usados:
                problemas.append(f"{nombre}: «{titulo}» ya está usado en la serie o en otro plan")
        for c in t["capitulos"]:
            try:
                a, b = c["pasaje"].split("-")
                c1, v1 = map(int, a.split(":"))
                c2, v2 = map(int, b.split(":")) if ":" in b else (c1, int(b))
            except ValueError:
                problemas.append(f"tomo {t['tomo']} cap {c['cap']}: pasaje raro «{c['pasaje']}»"); continue
            vistos += [(k, v) for k in range(c1, c2 + 1)
                       for v in range(v1 if k == c1 else 1, (v2 if k == c2 else fin.get(k, 0)) + 1)]
    todos = {(k, v) for k in fin for v in range(1, fin[k] + 1)}
    huecos = sorted(todos - set(vistos)); dobles = sorted({x for x in vistos if vistos.count(x) > 1})
    if huecos:
        problemas.append(f"versículos sin cubrir: {len(huecos)} (el primero, {huecos[0][0]}:{huecos[0][1]})")
    if dobles:
        problemas.append(f"versículos repetidos: {len(dobles)} (el primero, {dobles[0][0]}:{dobles[0][1]})")
    if cambiado:
        p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    # Los archivos de consulta que deja Claude, fuera, para que no los lea al escribir
    sueltos = [f for f in d.iterdir() if f.is_file() and f.name not in
               ("plan.json", "brief-libro.md", "estado.json", "registro.jsonl")]
    if sueltos:
        aparte = TRABAJO / "_viejo" / d.name
        aparte.mkdir(parents=True, exist_ok=True)
        for f in sueltos:
            shutil.move(str(f), str(aparte / f.name))
    return problemas


def cmd_tomo(libro, n, solo_cap=None):
    plan = cargar_plan(libro)
    problemas = revisar_plan(libro)
    if problemas:
        print("El plan tiene problemas; corrígelos en plan.json (o pásamelos) antes de escribir:")
        print("\n".join("   - " + x for x in problemas))
        sys.exit(1)
    plan = cargar_plan(libro)
    tomo = next((t for t in plan["tomos"] if t["tomo"] == n), None)
    if not tomo:
        sys.exit(f"El plan no tiene tomo {n}")
    try:
        for cap in tomo["capitulos"]:
            if solo_cap and cap["cap"] != solo_cap:
                continue
            producir(plan, tomo, cap)
        if solo_cap:
            return
        producir(plan, tomo, None)
        volumenes(plan, tomo)
        actualizar_indices(plan, tomo)
    except LimiteAlcanzado as ex:
        print(f"\nSe acabó el límite de uso de Claude: {ex}\nCuando se renueve, vuelve a lanzar el mismo comando: sigue donde se quedó.")
        return
    cmd_estado(libro)
    print(f"\nTomo {n} terminado. Revísalo en {LIBROS / carpeta_de(libro) / f'capitulo {n}'} antes de seguir.")


def cmd_estado(libro):
    d = dir_libro(libro)
    e = estado(libro)
    print(f"{libro}: {len(e)} archivos hechos; con avisos: {[a for a, v in e.items() if not v.get('limpio')]}")
    reg = d / "registro.jsonl"
    if reg.exists():
        filas = [json.loads(l) for l in reg.read_text(encoding="utf-8").splitlines() if l.strip()]
        coste = sum(f.get("coste_equivalente_usd") or 0 for f in filas)
        print(f"Llamadas: {len(filas)}; coste equivalente en API: {coste:.2f} USD "
              f"(con el plan Max no se paga: sirve para medir cuánto del límite gasta cada capítulo)")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__); return
    libro = libro_canonico(a[1])
    if not libro:
        sys.exit(f"No conozco el libro {a[1]}")
    if a[0] == "plan":
        cmd_plan(libro)
    elif a[0] == "tomo":
        cmd_tomo(libro, int(a[2]))
    elif a[0] == "capitulo":
        cmd_tomo(libro, int(a[2]), int(a[3]))
    elif a[0] == "estado":
        cmd_estado(libro)
    else:
        print(__doc__)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
