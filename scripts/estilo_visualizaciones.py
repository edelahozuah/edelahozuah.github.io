#!/usr/bin/env python3
"""Adapta las visualizaciones de docencia/ al aspecto de la web (al-folio).

Añade al final del <head> de cada visualización un bloque de estilo que
cambia el marco (fondo, texto, tipografía Roboto, bordes y el color de acento
de la web en botones, deslizadores y pestañas) y, al principio del <body>,
una barra con el nombre y el enlace a la asignatura. No toca los colores con
significado (zonas DNS, bits, paquetes, capas…), que siguen siendo los de cada
visualización.

Para buscadores y modelos de lenguaje añade también, con los datos de
_data/recursos.yml y _data/resumenes/*.yml: en el <head>, descripción, URL
canónica, enlaces hreflang, Open Graph y un JSON-LD LearningResource; y al
final del <body>, un bloque «Sobre esta visualización» con el resumen, los
conceptos y las fórmulas en texto estático, legible sin JavaScript.

Es idempotente: si el bloque ya está, lo sustituye. Los originales de las
carpetas AR1/SX.X/Visualizaciones no se modifican; el script actúa sobre las
copias de la web.

Uso:
    python3 scripts/estilo_visualizaciones.py              # todo docencia/
    python3 scripts/estilo_visualizaciones.py docencia/ar1/colas
    python3 scripts/estilo_visualizaciones.py --quitar     # deshace los cambios
"""

import argparse
import html as htmlmod
import json
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
INI_HEAD, FIN_HEAD = "<!-- estilo-sitio:inicio -->", "<!-- estilo-sitio:fin -->"
INI_BODY, FIN_BODY = "<!-- barra-sitio:inicio -->", "<!-- barra-sitio:fin -->"
INI_PIE, FIN_PIE = "<!-- acerca-sitio:inicio -->", "<!-- acerca-sitio:fin -->"
LICENCIA = "https://creativecommons.org/licenses/by-sa/4.0/"
ROBOTO = '"Roboto","Helvetica Neue",Arial,sans-serif'
MONO = 'ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace'

# Paleta de la web (assets/css/sitio.css).
CLARO = {"bg": "#ffffff", "panel": "#f8f9fa", "ink": "#000000", "muted": "#6b6b6b",
         "line": "#e3e3e3", "strong": "#b0b0b0"}
OSCURO = {"bg": "#1c1c1d", "panel": "#212529", "ink": "#e8e8e8", "muted": "#9c9c9c",
          "line": "#424246", "strong": "#6b6b70"}
ACENTO, ACENTO_OSCURO = "#b509ac", "#2698ba"


def familia(html):
    """Cada grupo de visualizaciones nombra sus variables CSS de una forma."""
    if "--f-disp" in html and "--rust" in html:
        return "dns"
    if "--rule-strong" in html and "--packet" in html:
        return "lab"
    if "--l-hi" in html and "--accent" in html:
        return "capas" if "--svc" in html else "colas"
    if "--paper" in html and "--data" in html:
        return "retardos"
    if "--lienzo" in html and ("--trama" in html or "--suave" in html):  # HTTP persistente, DNS paso a paso
        return "diagrama"
    return None


def variables(fam, p):
    """Variables neutras de cada familia, con la paleta p (clara u oscura)."""
    if fam == "dns":
        return {"--bg": p["bg"], "--surface": p["bg"] if p is CLARO else p["panel"],
                "--surface2": p["panel"] if p is CLARO else "#2a2e33", "--ink": p["ink"],
                "--muted": p["muted"], "--line": p["line"], "--rust": "var(--sitio-acento)",
                "--f-disp": ROBOTO, "--f-body": ROBOTO, "--f-mono": MONO}
    if fam in ("capas", "colas"):
        return {"--bg": p["bg"], "--surface": p["panel"], "--ink": p["ink"],
                "--muted": p["muted"], "--line": p["line"]}
    if fam == "lab":
        return {"--surface": p["bg"], "--panel": p["bg"] if p is CLARO else p["panel"],
                "--ink": p["ink"], "--ink-2": p["muted"], "--rule": p["line"],
                "--rule-strong": p["strong"]}
    if fam == "retardos":
        return {"--paper": p["bg"], "--panel": p["panel"], "--ink": p["ink"],
                "--ink-2": p["muted"], "--line": p["line"]}
    if fam == "diagrama":
        fondo = p["bg"] if p is CLARO else p["panel"]
        return {"--bg": p["bg"], "--panel": fondo, "--lienzo": fondo,
                "--suave": p["panel"] if p is CLARO else "#2a2e33", "--fg": p["ink"],
                "--muted": p["muted"], "--line": p["line"],
                "--display": ROBOTO, "--body": ROBOTO, "--mono": MONO}
    return {}


# Elementos de interfaz que pasan al color de acento de la web. Solo selectores
# de marco: los colores con significado se quedan como están.
INTERFAZ = {
    "dns": "header{border-top:0}",
    "capas": ('h1{color:var(--ink)}'
              'nav button[aria-selected="true"]{color:var(--sitio-acento);border-bottom-color:var(--sitio-acento)}'
              '.btn.primary{background:var(--sitio-acento);border-color:var(--sitio-acento)}'
              'input[type=range],label.tog input{accent-color:var(--sitio-acento)}'),
    "colas": ('h1{color:var(--ink)}'
              '.btn.primary{background:var(--sitio-acento);border-color:var(--sitio-acento)}'
              'input[type=range]{accent-color:var(--sitio-acento)}'
              '.chip{border-color:var(--sitio-acento);color:var(--sitio-acento)}'),
    "lab": ('button.primary{background:var(--sitio-acento);border-color:var(--sitio-acento)}'
            '.field input[type=range]{accent-color:var(--sitio-acento)}'
            '.keyframes button.cur{border-color:var(--sitio-acento);box-shadow:inset 0 -3px 0 var(--sitio-acento)}'),
    "retardos": ('input[type=range]{accent-color:var(--sitio-acento)}'
                 'button:focus-visible,input:focus-visible,select:focus-visible{outline-color:var(--sitio-acento)}'),
    "diagrama": ('h1 span{color:inherit}.sitio-acerca h2{color:var(--fg)}'
                 '.seg button[aria-pressed="true"],button.btn.prim{background:var(--sitio-acento);'
                 'border-color:var(--sitio-acento);color:#fff}'
                 'input[type=range],input[type=checkbox]{accent-color:var(--sitio-acento)}'
                 'button:focus-visible,input:focus-visible,select:focus-visible{outline-color:var(--sitio-acento)}'),
}
LINEA = {"dns": "--line", "capas": "--line", "colas": "--line", "lab": "--rule", "retardos": "--line",
         "diagrama": "--line"}
TIENE_OSCURO = {"dns", "capas", "colas", "lab", "diagrama"}


def bloque_css(fam, html):
    decl = lambda d: ";".join(f"{k}:{v}" for k, v in d.items())
    css = [f":root{{--sitio-acento:{ACENTO};{decl(variables(fam, CLARO))}}}"]
    if fam in TIENE_OSCURO:
        oscuro = f"--sitio-acento:{ACENTO_OSCURO};{decl(variables(fam, OSCURO))}"
        css.append(f'@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{oscuro}}}}}')
        css.append(f':root[data-theme="dark"]{{{oscuro}}}')
    css.append(f"body{{font-family:{ROBOTO}}}")
    css.append(f"h1{{font-family:{ROBOTO};font-weight:400;letter-spacing:0}}")
    # Las etiquetas en mayúsculas espaciadas pasan a texto normal, como en la web.
    estilos = "".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    mayus = sorted({s.strip() for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", estilos)
                    if "text-transform:uppercase" in b.replace(" ", "") and not s.strip().startswith("@")})
    if mayus:
        css.append(f"{','.join(mayus)}{{text-transform:none;letter-spacing:normal;font-family:{ROBOTO}}}")
    css.append(INTERFAZ[fam])
    margen = "margin:0 -16px 4px;" if fam == "dns" else "margin:0 0 4px;"
    css.append(
        f".sitio-barra{{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;"
        f"gap:4px 16px;{margen}padding:12px 16px;border-bottom:1px solid var({LINEA[fam]});"
        f"font:300 16px/1.3 {ROBOTO};color:var(--ink)}}"
        ".sitio-barra a{color:inherit;text-decoration:none}"
        ".sitio-barra a:hover{color:var(--sitio-acento)}"
        ".sitio-barra .sitio-marca{font-size:1.15rem}.sitio-barra b{font-weight:700}")
    # Sin relleno en el <body>, el bloque final lleva su propio margen lateral.
    relleno = "16px 16px 0" if fam == "diagrama" else "16px 0 0"
    css.append(
        f".sitio-acerca{{max-width:80ch;margin:40px auto 24px;padding:{relleno};"
        f"border-top:1px solid var({LINEA[fam]});font:400 15px/1.55 {ROBOTO};color:var(--ink)}}"
        ".sitio-acerca h2{font-size:1.1rem;font-weight:500;line-height:1.3;margin:0 0 8px}"
        ".sitio-acerca p{margin:0 0 8px}.sitio-acerca ul{margin:0 0 8px;padding-left:1.4em}"
        f".sitio-acerca code{{font-family:{MONO};font-size:.92em}}"
        ".sitio-acerca a{color:var(--sitio-acento)}.sitio-acerca .sitio-pie{opacity:.75;font-size:.9em}")
    return "\n".join(css)


def asignaturas():
    datos = yaml.safe_load((RAIZ / "_data" / "asignaturas.yml").read_text(encoding="utf-8")) or []
    return {a["id"]: a for a in datos}


def pares_idioma():
    """{url_es: url_en} y su inversa, leídos de _data/recursos.yml, para enlazar
    cada visualización con su pareja en el otro idioma."""
    datos = yaml.safe_load((RAIZ / "_data" / "recursos.yml").read_text(encoding="utf-8")) or {}
    es_a_en = {}
    for temas in datos.values():
        for t in temas:
            for r in t.get("recursos", []):
                if r.get("en"):
                    es_a_en[r["url"]] = r["en"]
    en_a_es = {v: k for k, v in es_a_en.items()}
    return es_a_en, en_a_es


def recursos_por_url(asigs):
    """{url: datos} de cada visualización (en español y en inglés), con lo que
    hace falta para sus metadatos: título, descripción, imagen, pareja de
    idioma, asignatura y sesión o etiqueta."""
    datos = yaml.safe_load((RAIZ / "_data" / "recursos.yml").read_text(encoding="utf-8")) or {}
    res = {}
    for id_asig, temas in datos.items():
        a = asigs.get(id_asig, {})
        for t in temas:
            for r in t.get("recursos", []):
                comun = {"imagen": r.get("imagen"), "sesion": r.get("sesion"), "tema": t.get("tema")}
                res[r["url"]] = dict(comun, en=False, titulo=r["titulo"], descripcion=r.get("descripcion"),
                                     etiqueta=r.get("etiqueta"), pareja=r.get("en"),
                                     asignatura=a.get("nombre"), pagina=a.get("pagina"),
                                     desc_asignatura=a.get("descripcion"))
                if r.get("en"):
                    res[r["en"]] = dict(comun, en=True, titulo=r.get("titulo_en") or r["titulo"],
                                        descripcion=r.get("descripcion_en") or r.get("descripcion"),
                                        etiqueta=r.get("etiqueta_en"), pareja=r["url"],
                                        asignatura=a.get("nombre_en") or a.get("nombre"),
                                        pagina=a.get("pagina_en") or a.get("pagina"),
                                        desc_asignatura=a.get("descripcion_en") or a.get("descripcion"))
    return res


def resumenes():
    """{url: {resumen, conceptos, formulas}} de todos los _data/resumenes/*.yml."""
    res = {}
    for f in sorted((RAIZ / "_data" / "resumenes").glob("*.yml")):
        res.update(yaml.safe_load(f.read_text(encoding="utf-8")) or {})
    return res


def config():
    return yaml.safe_load((RAIZ / "_config.yml").read_text(encoding="utf-8"))


def metadatos(web, html, r, resumen, conf):
    """Etiquetas del <head>: descripción, canónica, hreflang, Open Graph y JSON-LD."""
    url = conf["url"].rstrip("/")
    absoluta = lambda ruta: url + ruta
    esc = lambda t: htmlmod.escape(" ".join(str(t).split()), quote=True)
    en = r["en"]
    desc = r["descripcion"] or (resumen or {}).get("resumen", "")
    lineas = []
    if not re.search(r'<meta\s+name="description"', html):
        lineas.append(f'<meta name="description" content="{esc(desc)}">')
    lineas.append(f'<meta name="author" content="{esc(conf["autor"]["nombre"])}">')
    lineas.append(f'<link rel="canonical" href="{absoluta(web)}">')
    if r["pareja"]:
        yo, otro = ("en", "es") if en else ("es", "en")
        lineas.append(f'<link rel="alternate" hreflang="{yo}" href="{absoluta(web)}">')
        lineas.append(f'<link rel="alternate" hreflang="{otro}" href="{absoluta(r["pareja"])}">')
        defecto = r["pareja"] if en else web
        lineas.append(f'<link rel="alternate" hreflang="x-default" href="{absoluta(defecto)}">')
    lineas += [f'<meta property="og:type" content="website">',
               f'<meta property="og:site_name" content="{esc(conf["title"])}">',
               f'<meta property="og:title" content="{esc(r["titulo"])}">',
               f'<meta property="og:description" content="{esc(desc)}">',
               f'<meta property="og:url" content="{absoluta(web)}">',
               f'<meta property="og:locale" content="{"en_US" if en else "es_ES"}">']
    if r["imagen"]:
        lineas.append(f'<meta property="og:image" content="{absoluta(r["imagen"])}">')
        lineas.append('<meta name="twitter:card" content="summary_large_image">')
    ld = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "@id": absoluta(web),
        "url": absoluta(web),
        "name": r["titulo"],
        "description": " ".join(((resumen or {}).get("resumen") or desc).split()),
        "inLanguage": "en" if en else "es",
        "learningResourceType": "interactive visualization" if en else "visualización interactiva",
        "interactivityType": "active",
        "educationalLevel": "Undergraduate" if en else "Grado universitario",
        "isAccessibleForFree": True,
        "license": LICENCIA,
        "author": {"@type": "Person", "@id": url + "/#persona", "name": conf["autor"]["nombre"],
                   "url": url + "/", "sameAs": ["https://orcid.org/" + conf["autor"]["orcid"]]},
    }
    if resumen and resumen.get("conceptos"):
        ld["teaches"] = resumen["conceptos"]
    if r["imagen"]:
        ld["image"] = absoluta(r["imagen"])
    if r["asignatura"]:
        ld["isPartOf"] = {"@type": "Course", "name": r["asignatura"], "url": absoluta(r["pagina"]),
                          "description": r["desc_asignatura"] or r["asignatura"],
                          "provider": {"@type": "CollegeOrUniversity",
                                       "name": "University of Alcalá" if en else "Universidad de Alcalá"}}
    if r["pareja"]:
        ld["translationOfWork" if en else "workTranslation"] = {"@id": absoluta(r["pareja"])}
    texto = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
    lineas.append(f'<script type="application/ld+json">\n{texto}\n</script>')
    return "\n".join(lineas)


def acerca(r, resumen, conf):
    """Bloque «Sobre esta visualización», en texto estático."""
    en = r["en"]
    e = htmlmod.escape
    partes = [f'<section class="sitio-acerca" aria-labelledby="sitio-acerca-t">',
              f'<h2 id="sitio-acerca-t">{"About this visualization" if en else "Sobre esta visualización"}</h2>']
    if resumen:
        partes.append(f'<p>{e(" ".join(resumen["resumen"].split()))}</p>')
        if resumen.get("conceptos"):
            partes.append(f'<p><b>{"Concepts" if en else "Conceptos"}:</b> {e(", ".join(resumen["conceptos"]))}.</p>')
        if resumen.get("formulas"):
            partes.append(f'<p><b>{"Formulas" if en else "Fórmulas"}:</b></p><ul>'
                          + "".join(f"<li><code>{e(x)}</code></li>" for x in resumen["formulas"]) + "</ul>")
    elif r["descripcion"]:
        partes.append(f'<p>{e(r["descripcion"])}</p>')
    pie = []
    if r["asignatura"]:
        contexto = r["etiqueta"] or (f'{"Session" if en else "Sesión"} {r["sesion"]}' if r["sesion"] else "")
        pie.append(f'<a href="{r["pagina"]}">{e(r["asignatura"])}</a>' + (f", {e(contexto)}" if contexto else ""))
    pie.append(f'{e(conf["autor"]["nombre"])}, {"University of Alcalá" if en else "Universidad de Alcalá"}')
    pie.append(f'{"License" if en else "Licencia"} <a href="{LICENCIA}" rel="license">CC BY-SA 4.0</a>')
    partes.append(f'<p class="sitio-pie">{" · ".join(pie)}</p>')
    partes.append("</section>")
    return f"{INI_PIE}{''.join(partes)}{FIN_PIE}"


def barra(ruta, html, asigs, idiomas):
    partes = ruta.relative_to(RAIZ).parts  # docencia/<id>/…
    a = asigs.get(partes[1]) if len(partes) > 2 else None
    en = re.search(r'<html[^>]*lang="en', html) is not None
    web = "/" + "/".join(partes)
    es_a_en, en_a_es = idiomas
    enlace = ""
    if a:
        pagina = a.get("pagina_en") if en else a.get("pagina")
        if pagina:
            nombre = a.get("nombre_en") if en else a.get("nombre")
            enlace = f'<a href="{pagina}">{nombre or a["nombre"]}</a>'
    pareja = en_a_es.get(web) if en else es_a_en.get(web)
    if pareja:
        etiqueta = "Español" if en else "English"
        enlace += f'<a href="{pareja}" hreflang="{"es" if en else "en"}" lang="{"es" if en else "en"}">{etiqueta}</a>'
    inicio = "/en/" if en else "/"
    return (f'{INI_BODY}<div class="sitio-barra" role="navigation" aria-label="{"Site" if en else "Sitio"}">'
            f'<a class="sitio-marca" href="{inicio}"><b>Enrique</b> de la Hoz</a>{enlace}</div>{FIN_BODY}')


def quitar(html):
    html = re.sub(re.escape(INI_HEAD) + r".*?" + re.escape(FIN_HEAD) + r"\n?", "", html, flags=re.S)
    html = re.sub(re.escape(INI_PIE) + r".*?" + re.escape(FIN_PIE) + r"\n?", "", html, flags=re.S)
    # La barra se inserta con un salto de línea a cada lado; se quitan los dos.
    return re.sub(r"\n?" + re.escape(INI_BODY) + r".*?" + re.escape(FIN_BODY) + r"\n?", "", html, flags=re.S)


def adaptar(ruta, asigs, idiomas, recursos, textos, conf):
    html = quitar(ruta.read_text(encoding="utf-8"))
    fam = familia(html)
    if not fam:
        return None
    web = "/" + "/".join(ruta.relative_to(RAIZ).parts)
    r = recursos.get(web)
    meta = metadatos(web, html, r, textos.get(web), conf) + "\n" if r else ""
    cabeza = (f'{INI_HEAD}\n{meta}<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
              f'family=Roboto:wght@300;400;500;700&display=swap">\n'
              f'<style id="estilo-sitio">\n{bloque_css(fam, html)}\n</style>\n{FIN_HEAD}\n')
    if "</head>" in html:
        html = html.replace("</head>", cabeza + "</head>", 1)
    else:  # HTML sin <head> explícito: el bloque va tras el último <style>
        corte = html.rfind("</style>") + len("</style>")
        html = html[:corte] + "\n" + cabeza + html[corte:]
    m = re.search(r"<body[^>]*>", html)
    if m:
        html = html[:m.end()] + "\n" + barra(ruta, html, asigs, idiomas) + "\n" + html[m.end():]
    else:  # sin <body>: la barra va justo después del bloque de estilo
        corte = html.find(FIN_HEAD) + len(FIN_HEAD)
        html = html[:corte] + "\n" + barra(ruta, html, asigs, idiomas) + html[corte:]
    if r:
        pie = acerca(r, textos.get(web), conf) + "\n"
        if "</body>" in html:
            html = html.replace("</body>", pie + "</body>", 1)
        else:  # sin </body>: antes del último <script> de primer nivel
            corte = html.rfind("\n<script")
            corte = corte + 1 if corte >= 0 else len(html)
            html = html[:corte] + pie + html[corte:]
    ruta.write_text(html, encoding="utf-8")
    return fam


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rutas", nargs="*", default=["docencia"])
    ap.add_argument("--quitar", action="store_true", help="elimina el estilo y la barra añadidos")
    args = ap.parse_args()
    asigs = asignaturas()
    idiomas = pares_idioma()
    recursos, textos, conf = recursos_por_url(asigs), resumenes(), config()
    for r in args.rutas:
        base = (RAIZ / r) if not Path(r).is_absolute() else Path(r)
        for f in sorted([base] if base.is_file() else base.rglob("*.html")):
            texto = f.read_text(encoding="utf-8")
            if texto.startswith("---"):  # páginas de Jekyll, no visualizaciones
                continue
            if args.quitar:
                f.write_text(quitar(texto), encoding="utf-8")
                print(f"  sin estilo  {f.relative_to(RAIZ)}")
                continue
            fam = adaptar(f, asigs, idiomas, recursos, textos, conf)
            print(f"  {fam or 'sin familia, no se toca':<10} {f.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
