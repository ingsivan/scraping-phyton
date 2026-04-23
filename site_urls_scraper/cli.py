from __future__ import annotations

import argparse
from pathlib import Path

from .crawler import CrawlConfig, audit_site
from .exporter import export_audit_to_excel


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
    parser.add_argument(
        "--audit-indexability",
        action="store_true",
        help="Detecta meta robots y cabeceras X-Robots-Tag para marcar noindex/nofollow.",
    )
    parser.add_argument(
        "--audit-sitemaps",
        action="store_true",
        help="Descubre robots.txt y audita todos los sitemaps declarados por el sitio.",
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
    result = audit_site(
        config,
        audit_indexability=args.audit_indexability,
        include_sitemaps=args.audit_sitemaps,
    )

    output_path = Path(args.output).expanduser().resolve()
    export_audit_to_excel(result, output_path)

    visited_count = sum(1 for item in result.urls if item.status_code is not None)
    print(f"URLs encontradas: {len(result.urls)}")
    print(f"Paginas visitadas: {visited_count}")
    if args.audit_sitemaps:
        print(f"Sitemaps auditados: {len(result.sitemaps)}")
    if args.audit_indexability:
        noindex_count = sum(1 for item in result.urls if item.has_noindex)
        nofollow_count = sum(1 for item in result.urls if item.has_nofollow)
        print(f"URLs con noindex: {noindex_count}")
        print(f"URLs con nofollow: {nofollow_count}")
    print(f"Excel generado en: {output_path}")
    if visited_count == 0:
        print("Aviso: no se pudo visitar ninguna pagina. Revisa red, SSL o la URL indicada.")

    return 0
