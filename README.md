# Scraper de URLs a Excel

Proyecto en Python para rastrear un sitio web, obtener todas las URLs internas encontradas y exportarlas a un archivo Excel.

## Requisitos

- Python 3.10 o superior
- `pip`

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar pruebas

```bash
.venv/bin/python -m unittest discover -s tests
```

## Uso

```bash
python3 -m site_urls_scraper https://ejemplo.com
```

Esto genera por defecto el archivo `urls.xlsx`.

### Opciones utiles

```bash
python3 -m site_urls_scraper https://ejemplo.com \
  --output reporte_urls.xlsx \
  --max-pages 500 \
  --timeout 10 \
  --delay 0.2
```

### Parametros

- `url`: URL inicial del sitio que quieres revisar.
- `--output`: nombre del archivo Excel de salida.
- `--max-pages`: maximo de paginas a visitar.
- `--timeout`: tiempo maximo por solicitud HTTP.
- `--delay`: pausa entre solicitudes para no golpear el servidor.
- `--include-fragments`: conserva fragmentos tipo `#seccion`.
- `--allow-subdomains`: permite rastrear subdominios del dominio inicial.

## Que exporta el Excel

La hoja `urls` contiene:

- `url`: URL encontrada.
- `depth`: profundidad desde la URL inicial.
- `status_code`: codigo HTTP obtenido si esa URL fue visitada.
- `source_url`: pagina donde se encontro el enlace.

## Notas

- El crawler sigue solo enlaces internos por defecto.
- Ignora `mailto:`, `tel:`, `javascript:` y archivos no HTML obvios.
- Respeta redirecciones HTTP de `requests`.

## Ejemplo completo

```bash
python3 -m site_urls_scraper https://www.tusitio.com --output tusitio_urls.xlsx
```
