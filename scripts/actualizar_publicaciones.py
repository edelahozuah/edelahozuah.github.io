#!/usr/bin/env python3
"""Genera _data/publicaciones.yml y _data/metricas.yml a partir de ORCID y Google Scholar.

ORCID aporta la lista de trabajos, el tipo, el DOI y los autores; Google Scholar
aporta las citas (y los trabajos que no estén en ORCID). Los duplicados se
fusionan por título normalizado.

Las correcciones manuales van en _data/publicaciones_ajustes.yml y se aplican al
final, así que sobreviven a cada regeneración. Ver el README.

Además genera una página por publicación en _publicaciones/ (para Google
Scholar) y guarda en _data/publicaciones_resumenes.yml los resúmenes que
OpenAlex tiene de cada DOI (se consultan una sola vez; el fichero se puede
corregir a mano).

Uso:
    python3 scripts/actualizar_publicaciones.py            # ORCID + Scholar
    python3 scripts/actualizar_publicaciones.py --sin-scholar
    python3 scripts/actualizar_publicaciones.py --solo-paginas   # no consulta nada; regenera las páginas

Si Google Scholar bloquea la petición, el script sigue solo con ORCID y
conserva las citas y métricas de la ejecución anterior.
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import yaml

ORCID = "0000-0003-4837-3837"
SCHOLAR = "HBXLJGoAAAAJ"
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "_data" / "publicaciones.yml"
METRICAS = RAIZ / "_data" / "metricas.yml"
AJUSTES = RAIZ / "_data" / "publicaciones_ajustes.yml"
RESUMENES = RAIZ / "_data" / "publicaciones_resumenes.yml"
PAGINAS = RAIZ / "_publicaciones"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

# Orden de preferencia cuando un mismo trabajo aparece con varios tipos.
PRIORIDAD_TIPO = {"journal-article": 0, "conference-paper": 1, "book-chapter": 2, "book": 2}
CATEGORIA = {"journal-article": "revista", "conference-paper": "congreso",
             "book-chapter": "capitulo", "book": "capitulo"}
# ORCID etiqueta como artículo de revista muchas actas; estas pistas lo corrigen.
PISTAS_CONGRESO = re.compile(r"proceedings|proc\.|conference|congreso|jornadas|workshop|"
                             r"symposium|pricai|agents in principle|agreement technologies|dcnet|icete",
                             re.I)
# Arreglos de texto habituales en los metadatos de ORCID.
SUSTITUCIONES = [(r"\s*\(including subseries[^)]*\)", ""), (r"\bIeee\b", "IEEE"), (r"\bDcnet\b", "DCNET")]
# Abreviatura del medio que se muestra junto a cada publicación (gana la primera que casa).
ABREVIATURAS = [
    (r"Journal of Network and Computer Applications", "JNCA"),
    (r"IEEE Internet Computing", "IEEE IC"),
    (r"^Sensors", "Sensors"),
    (r"Group Decision and Negotiation", "GDN"),
    (r"Discrete Applied Mathematics", "DAM"),
    (r"Wireless Communications and Mobile Computing", "WCMC"),
    (r"^Symmetry", "Symmetry"),
    (r"Computers (and|&) Education", "C&E"),
    (r"^Computational Intelligence", "COIN"),
    (r"Electronic Notes in Discrete Mathematics", "ENDM"),
    (r"Multiagent and Grid Systems", "MAGS"),
    (r"Autonomous Agents and Multi-?[Aa]gent|AAMAS", "AAMAS"),
    (r"Cyber Conflict|cycon", "CyCon"),
    (r"EDUCON|educon", "EDUCON"),
    (r"PRICAI", "PRICAI"),
    (r"PRIMA|Principles and Practice of Multi|Agents in Principle", "PRIMA"),
    (r"JIE 2010", "JIE"),
    (r"Ubiquitous Computing", "ICUC"),
    (r"Pervasive Systems and Computing", "PSC"),
    (r"CSN'03", "CSN"),
    (r"CEUR", "CEUR"),
    (r"SOCA|Service-Oriented Computing|soca\.", "SOCA"),
    (r"SAINT|Saint|saint\.", "SAINT"),
    (r"DCNET|ICETE", "ICETE"),
    (r"JITEL|jitel", "JITEL"),
    (r"Studies in Computational Intelligence", "SCI"),
    (r"Lecture Notes in Networks and Systems", "LNNS"),
    (r"Lecture Notes in Computer Science", "LNCS"),
    (r"^Proceedings 10\.3390", "MDPI Proc."),
]


def abreviatura(p):
    texto = " ".join(filter(None, [p.get("medio"), p.get("doi")]))
    return next((abr for patron, abr in ABREVIATURAS if re.search(patron, texto)), None)


def pedir(url, json_=False):
    cab = {"User-Agent": UA}
    if json_:
        cab["Accept"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=30) as r:
        datos = r.read().decode("utf-8")
    return json.loads(datos) if json_ else datos


def clave(titulo):
    """Título reducido a letras y números: agrupa variantes de mayúsculas, guiones y espacios."""
    t = re.sub(r"<[^>]+>", "", html.unescape(titulo or "")).lower()
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t)[:60]


def limpiar(texto):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(texto or ""))).strip()
    for patron, nuevo in SUSTITUCIONES:
        t = re.sub(patron, nuevo, t)
    return t


def autor(nombre):
    """«Apellido, N.» → «N. Apellido», para que todas las listas sigan el mismo orden."""
    m = re.fullmatch(r"([^,]+),\s*([^,]+)", nombre)
    return f"{m.group(2)} {m.group(1)}" if m else nombre


# ---------------------------------------------------------------- ORCID

def trabajos_orcid():
    grupos = pedir(f"https://pub.orcid.org/v3.0/{ORCID}/works", json_=True)["group"]
    codigos = [str(s["put-code"]) for g in grupos for s in g["work-summary"]]
    trabajos = []
    for i in range(0, len(codigos), 100):
        lote = pedir(f"https://pub.orcid.org/v3.0/{ORCID}/works/{','.join(codigos[i:i + 100])}", json_=True)
        trabajos += [b["work"] for b in lote["bulk"] if "work" in b]
    return [normalizar_orcid(w) for w in trabajos]


def normalizar_orcid(w):
    ids = {}
    for e in (w.get("external-ids") or {}).get("external-id") or []:
        ids.setdefault(e["external-id-type"].lower(), e["external-id-value"])
    fecha = w.get("publication-date") or {}
    anio = (fecha.get("year") or {}).get("value")
    autores = [autor(limpiar((c.get("credit-name") or {}).get("value")))
               for c in (w.get("contributors") or {}).get("contributor") or []]
    doi = (ids.get("doi") or "").strip().lower().removeprefix("https://doi.org/") or None
    return {
        "titulo": limpiar(w["title"]["title"]["value"]),
        "anio": int(anio) if anio else None,
        "tipo_orcid": w.get("type"),
        "medio": limpiar((w.get("journal-title") or {}).get("value")) or None,
        "doi": doi,
        "autores": list(dict.fromkeys(a for a in autores if a)),  # ORCID a veces repite autores
        "url": (w.get("url") or {}).get("value"),
    }


# ---------------------------------------------------------------- Google Scholar

def trabajos_scholar():
    base = f"https://scholar.google.com/citations?user={SCHOLAR}&hl=en&view_op=list_works&sortby=pubdate&pagesize=100"
    filas, inicio, pagina = [], 0, ""
    while True:
        pagina = pedir(f"{base}&cstart={inicio}")
        nuevas = re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', pagina, re.S)
        if not nuevas:
            break
        filas += nuevas
        if len(nuevas) < 100:
            break
        inicio += 100
    if not filas:
        raise RuntimeError("Scholar no devolvió ninguna fila (¿bloqueo o captcha?)")

    trabajos = []
    for f in filas:
        enlace = re.search(r'href="([^"]+)" class="gsc_a_at">(.*?)</a>', f)
        grises = re.findall(r'<div class="gs_gray">(.*?)</div>', f)
        citas = re.search(r'class="gsc_a_ac gs_ibl">(\d*)<', f)
        anio = re.search(r'gsc_a_h gsc_a_hc gs_ibl">(\d*)<', f)
        trabajos.append({
            "titulo": limpiar(enlace.group(2)),
            "anio": int(anio.group(1)) if anio and anio.group(1) else None,
            "citas": int(citas.group(1)) if citas and citas.group(1) else 0,
            "autores_txt": limpiar(grises[0]) if grises else "",
            "medio_txt": limpiar(grises[1]) if len(grises) > 1 else "",
            "scholar": "https://scholar.google.com" + html.unescape(enlace.group(1)),
        })

    tabla = re.findall(r'class="gsc_rsb_std">(\d+)<', pagina)
    metricas = None
    if len(tabla) >= 6:
        metricas = {"citas": int(tabla[0]), "indice_h": int(tabla[2]), "i10": int(tabla[4])}
    return trabajos, metricas


# ---------------------------------------------------------------- Fusión

def rango(t):
    arxiv = (t.get("doi") or "").startswith("10.48550")
    return (arxiv, PRIORIDAD_TIPO.get(t.get("tipo_orcid"), 3), t.get("doi") is None)


def categoria(t):
    tipo = t.get("tipo_orcid")
    if tipo == "journal-article" and PISTAS_CONGRESO.search(t.get("medio") or ""):
        return "congreso"
    if (t.get("doi") or "").startswith("10.48550"):
        return "otros"
    return CATEGORIA.get(tipo, "otros")


def fusionar(orcid, scholar, previas):
    grupos = {}
    for t in orcid:
        grupos.setdefault(clave(t["titulo"]), {"orcid": [], "scholar": []})["orcid"].append(t)
    for t in scholar:
        k = clave(t["titulo"])
        if k in grupos or t["anio"]:  # sin año en Scholar suele ser basura; solo se usa si casa con ORCID
            grupos.setdefault(k, {"orcid": [], "scholar": []})["scholar"].append(t)

    salida = []
    for k, g in grupos.items():
        if g["orcid"]:
            mejor = sorted(g["orcid"], key=rango)[0]
            arxiv = next((t["doi"] for t in g["orcid"] if (t.get("doi") or "").startswith("10.48550")), None)
            p = {
                "id": k,
                "titulo": mejor["titulo"],
                "anio": mejor["anio"] or max((t["anio"] or 0) for t in g["orcid"]) or None,
                "categoria": categoria(mejor),
                "medio": mejor["medio"] or next((t["medio"] for t in g["orcid"] if t["medio"]), None),
                "autores": max((t["autores"] for t in g["orcid"]), key=len) or None,
                "doi": mejor["doi"] if not (mejor["doi"] or "").startswith("10.48550") else None,
                "arxiv": arxiv.removeprefix("10.48550/arxiv.") if arxiv else None,
            }
            if not p["doi"]:
                p["doi"] = next((t["doi"] for t in g["orcid"]
                                 if t["doi"] and not t["doi"].startswith("10.48550")), None)
        else:
            s = g["scholar"][0]
            p = {"id": k, "origen": "scholar", "titulo": s["titulo"], "anio": s["anio"], "categoria": "otros",
                 "medio": re.sub(r",?\s*\d{4}$", "", s["medio_txt"]) or None,
                 "autores": None, "doi": None, "arxiv": None}

        if g["scholar"]:
            p["citas"] = sum(s["citas"] for s in g["scholar"])
            p["scholar"] = max(g["scholar"], key=lambda s: s["citas"])["scholar"]
            if not p["autores"]:
                p["autores_txt"] = max((s["autores_txt"] for s in g["scholar"]), key=len)
        elif k in previas:  # Scholar no disponible: se conserva lo que aportó la vez anterior
            for campo in ("citas", "scholar", "autores_txt"):
                if campo in previas[k] and not p.get(campo):
                    p[campo] = previas[k][campo]
        salida.append({c: v for c, v in p.items() if v not in (None, [], "")})

    if not scholar:
        vistos = {p["id"] for p in salida}
        salida += [p for i, p in previas.items() if p.get("origen") == "scholar" and i not in vistos]
    return salida


def aplicar_ajustes(pubs):
    if not AJUSTES.exists():
        return pubs
    ajustes = yaml.safe_load(AJUSTES.read_text(encoding="utf-8")) or {}
    ocultas = set(ajustes.get("ocultar") or [])
    cambios = ajustes.get("corregir") or {}
    por_id = {p["id"]: p for p in pubs if p["id"] not in ocultas}
    for i, c in cambios.items():
        if i in por_id:
            por_id[i].update(c)
        else:
            print(f"  aviso: el ajuste «{i}» no corresponde a ninguna publicación", file=sys.stderr)
    for extra in ajustes.get("anadir") or []:
        extra.setdefault("id", clave(extra["titulo"]))
        por_id[extra["id"]] = extra
    for i in ajustes.get("destacadas") or []:
        if i in por_id:
            por_id[i]["destacada"] = True
    return list(por_id.values())


def resumenes_openalex(pubs):
    """Añade «resumen» (y «resumen_idioma») a cada publicación con DOI, desde OpenAlex.

    Los resúmenes se guardan en _data/publicaciones_resumenes.yml (por id) y solo
    se consultan los DOI que no estén ya ahí; un valor vacío evita volver a preguntar.
    """
    guardados = yaml.safe_load(RESUMENES.read_text(encoding="utf-8")) if RESUMENES.exists() else {}
    guardados = guardados or {}
    nuevos = 0
    for p in pubs:
        if p["id"] in guardados or not p.get("doi"):
            continue
        try:
            w = pedir("https://api.openalex.org/works/https://doi.org/" + p["doi"], json_=True)
        except Exception:
            continue
        inv = w.get("abstract_inverted_index") or {}
        texto = ""
        if inv:
            posiciones = sorted((i, palabra) for palabra, idxs in inv.items() for i in idxs)
            texto = " ".join(palabra for _, palabra in posiciones)
            texto = re.sub(r"\s+", " ", html.unescape(texto)).strip()
        guardados[p["id"]] = {"resumen": texto, "idioma": w.get("language") or ""}
        nuevos += 1
    if nuevos:
        cabecera = ("# Resúmenes de las publicaciones, tomados de OpenAlex por scripts/actualizar_publicaciones.py.\n"
                    "# Se pueden corregir o completar a mano (por id); una entrada vacía no se vuelve a consultar.\n")
        RESUMENES.write_text(cabecera + yaml.safe_dump(guardados, allow_unicode=True, sort_keys=True, width=1000),
                             encoding="utf-8")
        print(f"{nuevos} resúmenes nuevos → {RESUMENES.relative_to(RAIZ)}")
    for p in pubs:
        r = guardados.get(p["id"]) or {}
        if r.get("resumen"):
            p["resumen"] = r["resumen"]
            if r.get("idioma"):
                p["resumen_idioma"] = r["idioma"]
    return pubs


def generar_paginas(pubs):
    """Escribe _publicaciones/<id>.md y _publicaciones/en/<id>.md (y borra las que sobren)."""
    (PAGINAS / "en").mkdir(parents=True, exist_ok=True)
    vivos = set()
    for p in pubs:
        autores = p.get("autores") or [a.strip() for a in (p.get("autores_txt") or "").split(",") if a.strip()]
        firma = ", ".join(autores[:3]) + (" et al." if len(autores) > 3 else "")
        for en in (False, True):
            ruta = PAGINAS / ("en" if en else "") / f"{p['id']}.md"
            permalink = f"/en/publications/{p['id']}/" if en else f"/publicaciones/{p['id']}/"
            alterno = f"/publicaciones/{p['id']}/" if en else f"/en/publications/{p['id']}/"
            medio = f" {p['medio']}." if p.get("medio") else ""
            desc = (f"{firma} ({p.get('anio', '')}).{medio}" if en else f"{firma} ({p.get('anio', '')}).{medio}")
            fm = {
                "title": p["titulo"],
                "publicacion": p["id"],
                "permalink": permalink,
                "lang_alt": alterno,
                "description": desc.strip(),
                "volver": {"url": "/en/publications/" if en else "/publicaciones/",
                           "texto": "publications" if en else "publicaciones"},
            }
            if en:
                fm["lang"] = "en"
            contenido = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=1000) + "---\n"
            if not ruta.exists() or ruta.read_text(encoding="utf-8") != contenido:
                ruta.write_text(contenido, encoding="utf-8")
            vivos.add(ruta)
    for f in list(PAGINAS.glob("*.md")) + list((PAGINAS / "en").glob("*.md")):
        if f not in vivos:
            f.unlink()
    print(f"{len(vivos)} páginas → {PAGINAS.relative_to(RAIZ)}/")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-scholar", action="store_true", help="no consultar Google Scholar")
    ap.add_argument("--solo-paginas", action="store_true",
                    help="no consultar ORCID ni Scholar; regenerar las páginas desde publicaciones.yml")
    args = ap.parse_args()

    if args.solo_paginas:
        pubs = yaml.safe_load(SALIDA.read_text(encoding="utf-8")) or []
        generar_paginas(pubs)
        return

    previas = yaml.safe_load(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else []
    previas = {p["id"]: p for p in previas or []}

    print("ORCID…", end=" ", flush=True)
    orcid = trabajos_orcid()
    print(f"{len(orcid)} registros")

    scholar, metricas = [], None
    if not args.sin_scholar:
        print("Google Scholar…", end=" ", flush=True)
        try:
            scholar, metricas = trabajos_scholar()
            print(f"{len(scholar)} registros")
        except Exception as e:  # Scholar bloquea con frecuencia; no es motivo para fallar
            print(f"no disponible ({e}); se conservan las citas anteriores")

    pubs = fusionar(orcid, scholar, previas)
    for p in pubs:
        p.pop("abr", None)  # los trabajos que vienen de la ejecución anterior ya la traen
        if abreviatura(p):
            p["abr"] = abreviatura(p)
    pubs = aplicar_ajustes(pubs)
    pubs.sort(key=lambda p: (-(p.get("anio") or 0), p["titulo"].lower()))
    pubs = resumenes_openalex(pubs)

    cabecera = ("# Generado por scripts/actualizar_publicaciones.py; no editar a mano.\n"
                "# Las correcciones van en _data/publicaciones_ajustes.yml.\n")
    SALIDA.write_text(cabecera + yaml.safe_dump(pubs, allow_unicode=True, sort_keys=False, width=1000),
                      encoding="utf-8")
    print(f"{len(pubs)} publicaciones → {SALIDA.relative_to(RAIZ)}")
    generar_paginas(pubs)

    if metricas:
        metricas["fecha"] = dt.date.today().isoformat()
        metricas["fuente"] = f"https://scholar.google.com/citations?user={SCHOLAR}"
        METRICAS.write_text(yaml.safe_dump(metricas, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"métricas → {METRICAS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
