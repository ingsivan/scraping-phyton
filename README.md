# Scraper de URLs a Excel

CLI en Python para rastrear un sitio web, descubrir sus URLs internas y exportarlas a un archivo Excel.

Repositorio: [https://github.com/ingsivan/scraping-phyton](https://github.com/ingsivan/scraping-phyton)

## Que hace

- Recibe una URL inicial desde consola.
- Recorre las paginas internas del mismo dominio.
- Normaliza enlaces internos.
- Ignora enlaces como `mailto:`, `tel:` y archivos no HTML comunes.
- Puede auditar `noindex` y `nofollow` via `meta robots` y `X-Robots-Tag`.
- Puede descubrir `robots.txt`, recorrer todos los sitemaps del sitio y consolidar esas URLs en el Excel.
- Genera un archivo `.xlsx` con el listado encontrado.

## Requisitos

- Python 3.10 o superior
- `pip`
- Conexion a Internet para rastrear sitios reales

Para comprobar tu version de Python:

```bash
python3 --version
```

En Windows tambien puedes probar:

```powershell
py --version
```

## 1. Clonar el repositorio

```bash
git clone https://github.com/ingsivan/scraping-phyton.git
cd scraping-phyton
```

## 2. Instalacion en macOS

### Crear entorno virtual

```bash
python3 -m venv .venv
```

### Activar entorno virtual

```bash
source .venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

## 3. Instalacion en Windows

### Crear entorno virtual

En PowerShell:

```powershell
py -m venv .venv
```

O si `py` no existe:

```powershell
python -m venv .venv
```

### Activar entorno virtual

En PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

En CMD:

```cmd
.venv\Scripts\activate.bat
```

### Instalar dependencias

```powershell
pip install -r requirements.txt
```

## 4. Uso basico

Con el entorno virtual activado:

macOS:

```bash
python3 -m site_urls_scraper https://ejemplo.com
```

Windows:

```powershell
python -m site_urls_scraper https://ejemplo.com
```

Esto genera por defecto el archivo `urls.xlsx` en la carpeta actual.

## 5. Ejemplos de uso

Guardar con un nombre concreto:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --output tusitio_urls.xlsx
```

Limitar el numero maximo de paginas:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --max-pages 500
```

Agregar una pausa entre peticiones:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --delay 0.2
```

Permitir subdominios:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --allow-subdomains
```

Conservar fragmentos tipo `#seccion`:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --include-fragments
```

Ejemplo completo:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --output reporte.xlsx --max-pages 500 --timeout 10 --delay 0.2
```

Auditoria SEO completa con sitemaps e indexabilidad:

```bash
python3 -m site_urls_scraper https://www.tusitio.com --output auditoria.xlsx --max-pages 500 --audit-sitemaps --audit-indexability
```

Ejemplo para `https://www.garzablancaresort.com/`:

```bash
python3 -m site_urls_scraper https://www.garzablancaresort.com/ --output garzablanca_auditoria.xlsx --max-pages 5000 --delay 0.2 --audit-sitemaps --audit-indexability
```

## 6. Parametros disponibles

- `url`: URL inicial del sitio que quieres revisar.
- `--output`: nombre o ruta del archivo Excel de salida. Por defecto `urls.xlsx`.
- `--max-pages`: maximo de paginas a visitar. Por defecto `200`.
- `--timeout`: tiempo maximo por solicitud HTTP en segundos. Por defecto `10`.
- `--delay`: espera entre solicitudes para no golpear el servidor. Por defecto `0`.
- `--include-fragments`: conserva fragmentos como `#contacto`.
- `--allow-subdomains`: permite rastrear subdominios del dominio inicial.
- `--audit-indexability`: revisa `meta robots` y `X-Robots-Tag` para detectar `noindex` y `nofollow`.
- `--audit-sitemaps`: descubre sitemaps desde `robots.txt` y audita sus URLs.

## 7. Como funciona el script

El flujo interno del script es este:

1. El comando `python -m site_urls_scraper URL` entra por `site_urls_scraper/__main__.py`.
2. Ese archivo llama a `site_urls_scraper/cli.py`, donde se leen y validan los argumentos de consola.
3. `cli.py` construye una configuracion con la URL inicial, limite de paginas, timeout, delay y opciones adicionales.
4. Esa configuracion se envia a `site_urls_scraper/crawler.py`.
5. El crawler normaliza la URL inicial para trabajar siempre con una version consistente.
6. Luego crea una cola de URLs pendientes por visitar.
7. Hace una peticion HTTP a cada URL usando `requests`.
8. Si la respuesta es HTML, extrae los enlaces `<a href="...">` con `BeautifulSoup`.
9. Convierte los enlaces relativos en absolutos.
10. Filtra enlaces externos, enlaces no validos y archivos no HTML comunes como `.pdf`, `.jpg`, `.css` o `.js`.
11. Si activas `--audit-sitemaps`, descubre los sitemaps publicados por el sitio y agrega sus URLs al consolidado.
12. Si activas `--audit-indexability`, detecta `noindex` y `nofollow` desde HTML y cabeceras HTTP.
13. Cuando termina el recorrido, `site_urls_scraper/exporter.py` genera el archivo Excel con `pandas`.

### Archivos principales

- `site_urls_scraper/__main__.py`: punto de entrada para ejecutar el modulo con `python -m`.
- `site_urls_scraper/cli.py`: parsea los parametros de consola y lanza el proceso.
- `site_urls_scraper/crawler.py`: contiene la logica del rastreo, filtrado y normalizacion de URLs.
- `site_urls_scraper/exporter.py`: convierte los resultados a un archivo `.xlsx`.

### Comportamiento del rastreo

- Solo sigue enlaces internos por defecto.
- Puede incluir subdominios si usas `--allow-subdomains`.
- Puede conservar anclas `#fragmento` si usas `--include-fragments`.
- Sigue redirecciones HTTP.
- Detiene el rastreo al alcanzar el limite definido en `--max-pages`.
- Si una URL no responde, el script continua con las demas.

## 8. Salida del Excel

El archivo generado contiene estas hojas:

- `summary`: resumen general con total de URLs, errores HTTP, URLs con `noindex`, URLs con `nofollow` y sitemaps auditados.
- `urls`: consolidado principal por URL.
- `issues`: subset de URLs con problemas o señales relevantes.
- `sitemaps`: inventario de sitemaps auditados.

La hoja `urls` incluye:

- `url`: URL consolidada.
- `depth`: profundidad desde la URL inicial si fue descubierta por crawl.
- `status_code`: codigo HTTP obtenido al visitar la URL.
- `source_url`: pagina donde se encontro el enlace durante el crawl.
- `found_in_crawl`: indica si la URL fue encontrada navegando el sitio.
- `listed_in_sitemap`: indica si la URL aparecio en algun sitemap.
- `sitemap_count`: numero de sitemaps donde aparece la URL.
- `sitemap_sources`: listado de sitemaps donde aparecio.
- `meta_robots`: contenido de etiquetas `meta robots` detectadas.
- `x_robots_tag`: valor de la cabecera `X-Robots-Tag`.
- `has_noindex`: marca si la URL tiene `noindex`.
- `has_nofollow`: marca si la URL tiene `nofollow`.
- `issue_flags`: etiquetas rapidas como `http_404`, `noindex`, `nofollow`, `sitemap_only` o `crawl_only`.

## 9. Ejecutar pruebas

macOS:

```bash
.venv/bin/python -m unittest discover -s tests
```

Windows:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

## 10. Estructura del proyecto

```text
scraping-phyton/
├── requirements.txt
├── README.md
├── site_urls_scraper/
│   ├── __main__.py
│   ├── cli.py
│   ├── crawler.py
│   └── exporter.py
└── tests/
```

## 11. Problemas comunes

### `python3: command not found`

Python no esta instalado o no esta en el `PATH`.

### En Windows no puedes activar `.venv`

Prueba primero en PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Despues vuelve a ejecutar:

```powershell
.venv\Scripts\Activate.ps1
```

### El scraper no encuentra paginas

Revisa:

- Que la URL sea correcta.
- Que el sitio responda desde tu red.
- Que el sitio no bloquee scraping.
- Que no todo el contenido se cargue solo con JavaScript.

### El Excel sale vacio o con pocas URLs

Este proyecto rastrea HTML enlazado con etiquetas `<a>`. Si el sitio construye la navegacion enteramente con JavaScript, puede que no aparezcan todas las URLs.

## 12. Comandos rapidos

macOS:

```bash
git clone https://github.com/ingsivan/scraping-phyton.git
cd scraping-phyton
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m site_urls_scraper https://ejemplo.com --output urls.xlsx
```

Windows PowerShell:

```powershell
git clone https://github.com/ingsivan/scraping-phyton.git
cd scraping-phyton
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m site_urls_scraper https://ejemplo.com --output urls.xlsx
```
