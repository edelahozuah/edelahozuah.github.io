# edelahozuah.github.io

Web personal de Enrique de la Hoz (Universidad de Alcalá): docencia, recursos
docentes e investigación. Jekyll publicado con GitHub Pages; no hay paso de
compilación propio.

## Estructura

| Qué | Dónde |
|---|---|
| Datos personales, menú | `_config.yml` |
| Asignaturas | `_data/asignaturas.yml` |
| Recursos docentes (índice) | `_data/recursos.yml` |
| Recursos docentes (los HTML) | `docencia/<asignatura>/<tema>/` |
| Líneas de investigación | `_data/lineas.yml` |
| Publicaciones (generado) | `_data/publicaciones.yml` |
| Correcciones a publicaciones | `_data/publicaciones_ajustes.yml` |
| Estilos | `assets/css/sitio.css` |

## Añadir un recurso

1. Copia el HTML autocontenido en `docencia/<asignatura>/<tema>/`, por ejemplo
   `docencia/ar1/tcp/ventana.html`. Sin cabecera YAML: Jekyll lo publica tal cual.
2. Añade una entrada en `_data/recursos.yml` (título, url, descripción, sesión y,
   si la hay, versión en inglés).

Aparece solo en la página de la asignatura, en `/recursos/` y en la portada.

## Añadir una asignatura

1. Añade `pagina: /docencia/<id>/` a su entrada en `_data/asignaturas.yml`.
2. Copia `docencia/ar1/index.html` a `docencia/<id>/index.html` y cambia
   `title`, `permalink` y `asignatura`.
3. Añade sus temas y recursos en `_data/recursos.yml` bajo la clave `<id>`.

## Actualizar las publicaciones

```sh
python3 scripts/actualizar_publicaciones.py
```

Lee ORCID (trabajos, DOI, autores) y Google Scholar (citas, índice h), fusiona
los duplicados y reescribe `_data/publicaciones.yml` y `_data/metricas.yml`.
Necesita PyYAML. Si Scholar bloquea la petición, conserva las citas anteriores;
`--sin-scholar` se salta Scholar a propósito.

No edites `_data/publicaciones.yml` a mano: las correcciones (ocultar
duplicados, cambiar tipo o título, destacar en portada, enlazar un PDF, añadir
trabajos que no estén en ORCID) van en `_data/publicaciones_ajustes.yml`, que el
script aplica en cada ejecución.

## Ver la web en local

Con Docker, usando las mismas versiones que GitHub Pages:

```sh
docker run --rm -it -p 4000:4000 -v "$PWD":/srv -w /srv ruby:3.3 \
  bash -c "bundle config set path vendor/bundle && bundle install && bundle exec jekyll serve --host 0.0.0.0"
```

y abre <http://localhost:4000>.
