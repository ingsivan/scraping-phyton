from __future__ import annotations

import argparse
from pathlib import Path

from .crawler import CrawlConfig, crawl_site
from .exporter import export_urls_to_excel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rastrea un sitio web y exporta sus URLs internas a Excel."
    )
    parser.add_argument("url", help="URL inicial del sitio a analizar.")
    parser.add_argument(
        "--output",
        default="urls.xlsx",
        help="Ruta del archivo Excel de salida. Por defecto: urls.xlsx",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximo de paginas a visitar. Por defecto: 200",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout por solicitud HTTP en segundos. Por defecto: 10",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Espera entre solicitudes en segundos. Por defecto: 0",
    )
    parser.add_argument(
        "--include-fragments",
        action="store_true",
        help="Conserva fragmentos tipo #ancla en las URLs.",
    )
    parser.add_argument(
        "--allow-subdomains",
        action="store_true",
        help="Permite rastrear subdominios del dominio inicial.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.max_pages <= 0:
        parser.error("--max-pages debe ser mayor a 0")

    if args.timeout <= 0:
        parser.error("--timeout debe ser mayor a 0")

    if args.delay < 0:
        parser.error("--delay no puede ser negativo")

    config = CrawlConfig(
        start_url=args.url,
        max_pages=args.max_pages,
        timeout=args.timeout,
        delay=args.delay,
        include_fragments=args.include_fragments,
        allow_subdomains=args.allow_subdomains,
    )

    print(f"Rastreando {config.start_url} ...")
    results = crawl_site(config)

    output_path = Path(args.output).expanduser().resolve()
    export_urls_to_excel(results, output_path)

    visited_count = sum(1 for item in results if item.status_code is not None)
    print(f"URLs encontradas: {len(results)}")
    print(f"Paginas visitadas: {visited_count}")
    print(f"Excel generado en: {output_path}")
    if visited_count == 0:
        print("Aviso: no se pudo visitar ninguna pagina. Revisa red, SSL o la URL indicada.")

    return 0
