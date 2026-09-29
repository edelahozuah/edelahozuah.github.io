#!/usr/bin/env python3
"""Crea la página de un vídeo de YouTube en la web, sin descargar el vídeo.

Lee de YouTube solo la ficha (título, fecha, duración, descripción, capítulos)
y los subtítulos, y escribe en _videos/<asignatura>/ una página por idioma con
el reproductor incrustado, los capítulos y la transcripción por capítulos.
El vídeo sigue alojado en YouTube; la miniatura también se enlaza desde allí.

Necesita yt-dlp y Node.js (YouTube exige un intérprete de JavaScript):
    python3 -m venv /tmp/yt && /tmp/yt/bin/pip install yt-dlp

Uso:
    /tmp/yt/bin/python scripts/importar_video.py URL --asignatura ar1 \\
        --slug nucleo-de-la-red --slug-en network-core --sesion 1.3

Después hay que revisar a mano el front matter (título y descripción, sobre
todo en inglés, y los títulos de los capítulos en inglés, que se copian del
español) y añadir el vídeo a _data/recursos.yml; el script imprime la entrada.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
YTDLP = [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node", "--remote-components", "ejs:github"]


def ficha(url):
    salida = subprocess.run(YTDLP + ["--skip-download", "--dump-json", url],
                            capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


def subtitulos(url, idiomas):
    """{idioma: [(segundo, texto)]} de los subtítulos manuales (no los automáticos)."""
    res = {}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(YTDLP + ["--skip-download", "--write-subs", "--sub-langs", ",".join(idiomas),
                                "--sub-format", "vtt", "-o", f"{tmp}/v.%(ext)s", url],
                       capture_output=True, text=True, check=True)
        for f in Path(tmp).glob("v.*.vtt"):
            idioma = f.suffixes[0].strip(".")
            cues = re.findall(r"(\d\d):(\d\d):(\d\d)\.\d+ --> [^\n]+\n(.*?)(?:\n\n|\Z)",
                              f.read_text(encoding="utf-8"), re.S)
            res[idioma] = [(int(h) * 3600 + int(m) * 60 + int(s), " ".join(t.split()))
                           for h, m, s, t in cues]
    return res


def capitulos_de(descripcion, info):
    """Capítulos con el título escrito en la descripción («0:00 Título»); si no
    los hay, los que detecta YouTube."""
    caps = []
    for linea in descripcion.splitlines():
        # re.search: a veces la marca va pegada a otro texto («CAPÍTULOS0:00 …»).
        m = re.search(r"(?<![\d:])(?:(\d+):)?(\d{1,2}):(\d\d)\s+(.+)", linea)
        if m:
            h, mi, s, titulo = m.groups()
            caps.append({"inicio": int(h or 0) * 3600 + int(mi) * 60 + int(s), "titulo": titulo.strip()})
    if not caps:
        caps = [{"inicio": int(c["start_time"]), "titulo": c["title"]} for c in info.get("chapters") or []]
    return caps


def marca(seg):
    h, r = divmod(int(seg), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def transcripcion(cues, caps):
    """Markdown con un apartado por capítulo y párrafos de unas cinco frases."""
    if not caps:
        caps = [{"inicio": 0, "titulo": ""}]
    partes = []
    arrastre = ""  # final de frase del capítulo anterior, que pasa a este
    for i, c in enumerate(caps):
        fin = caps[i + 1]["inicio"] if i + 1 < len(caps) else float("inf")
        texto = (arrastre + " " + " ".join(t for s, t in cues if c["inicio"] <= s < fin)).strip()
        arrastre = ""
        if i + 1 < len(caps):  # la frase que queda a medias sigue en el capítulo siguiente
            m = re.search(r"[.!?…][\"»”)]?\s+(?=[^.!?…]*$)", texto)
            if m and not re.search(r"[.!?…][\"»”)]?$", texto):
                texto, arrastre = texto[:m.end()].strip(), texto[m.end():].strip()
        if not texto:
            continue
        frases = re.split(r"(?<=[.!?…])\s+(?=[¿¡A-ZÁÉÍÓÚÑ0-9])", texto)
        parrafos = [" ".join(frases[j:j + 5]) for j in range(0, len(frases), 5)]
        partes.append(f'### {c["titulo"]} {{#t{c["inicio"]}}}\n\n' + "\n\n".join(parrafos))
    return "\n\n".join(partes) + "\n"


def escribir(ruta, datos, cuerpo):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=1000)
    ruta.write_text(f"---\n{fm}---\n{cuerpo}", encoding="utf-8")
    print(f"  escrito {ruta.relative_to(RAIZ)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--asignatura", required=True)
    ap.add_argument("--slug", required=True, help="nombre de la página en español")
    ap.add_argument("--slug-en", help="nombre de la página en inglés (si hay subtítulos en inglés)")
    ap.add_argument("--sesion")
    args = ap.parse_args()

    asigs = {a["id"]: a for a in yaml.safe_load((RAIZ / "_data" / "asignaturas.yml").read_text(encoding="utf-8"))}
    a = asigs[args.asignatura]
    info = ficha(args.url)
    vid = info["id"]
    desc = info.get("description", "")
    caps = capitulos_de(desc, info)
    subs = subtitulos(args.url, ["es", "en"])
    fecha = datetime.fromtimestamp(info["timestamp"], timezone.utc).isoformat() if info.get("timestamp") \
        else datetime.strptime(info["upload_date"], "%Y%m%d").date().isoformat()
    resumen = desc.split("\n\n")[0].strip()
    url_es = f'{a["pagina"]}videos/{args.slug}/'
    url_en = f'{a.get("pagina_en", "/en/")}videos/{args.slug_en}/' if args.slug_en and "en" in subs else None

    comun = {"youtube": vid, "asignatura": args.asignatura, "fecha": fecha, "duracion": int(info["duration"]),
             "imagen": f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"}
    if args.sesion:
        comun["sesion"] = str(args.sesion)
    es = {"title": info["title"], "permalink": url_es, **({"lang_alt": url_en} if url_en else {}),
          "description": resumen, **comun, "capitulos": caps,
          "volver": {"url": a["pagina"], "texto": a["nombre"]}}
    escribir(RAIZ / "_videos" / args.asignatura / f"{args.slug}.md", es, transcripcion(subs.get("es", []), caps))
    if url_en:
        en = {"lang": "en", "title": info["title"] + "  # TRADUCIR", "permalink": url_en, "lang_alt": url_es,
              "description": resumen + "  # TRADUCIR", **comun, "capitulos": caps,
              "volver": {"url": a.get("pagina_en"), "texto": a.get("nombre_en")}}
        escribir(RAIZ / "_videos" / args.asignatura / f"{args.slug_en}.md", en, transcripcion(subs["en"], caps))

    print("\nAñade a _data/recursos.yml, en el tema que corresponda:\n")
    entrada = {"titulo": info["title"], "url": url_es, "tipo": "video", "imagen": comun["imagen"],
               **({"en": url_en, "titulo_en": "TRADUCIR"} if url_en else {}),
               **({"sesion": comun["sesion"]} if args.sesion else {}), "descripcion": resumen}
    print(yaml.safe_dump([entrada], allow_unicode=True, sort_keys=False, width=1000))


if __name__ == "__main__":
    main()
