from __future__ import annotations

from pathlib import Path

import pandas as pd

from .crawler import AuditResult, SitemapRecord, UrlRecord


def build_issue_flags(record: UrlRecord) -> str:
    flags: list[str] = []

    if record.status_code is None:
        flags.append("status_missing")
    elif record.status_code >= 400:
        flags.append(f"http_{record.status_code}")

    if record.has_noindex:
        flags.append("noindex")
    if record.has_nofollow:
        flags.append("nofollow")
    if record.listed_in_sitemap and not record.discovered_via_crawl:
        flags.append("sitemap_only")
    if record.discovered_via_crawl and not record.listed_in_sitemap:
        flags.append("crawl_only")

    return ", ".join(flags)


def urls_dataframe(records: list[UrlRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "url": record.url,
                "depth": record.depth,
                "status_code": record.status_code,
                "source_url": record.source_url,
                "found_in_crawl": record.discovered_via_crawl,
                "listed_in_sitemap": record.listed_in_sitemap,
                "sitemap_count": len(record.sitemap_sources),
                "sitemap_sources": "\n".join(record.sitemap_sources),
                "meta_robots": record.meta_robots,
                "x_robots_tag": record.x_robots_tag,
                "has_noindex": record.has_noindex,
                "has_nofollow": record.has_nofollow,
                "issue_flags": build_issue_flags(record),
            }
            for record in records
        ]
    )


def issues_dataframe(records: list[UrlRecord]) -> pd.DataFrame:
    issue_records = [
        record for record in records if record.status_code is None or build_issue_flags(record)
    ]
    return urls_dataframe(issue_records)


def sitemaps_dataframe(records: list[SitemapRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sitemap_url": record.sitemap_url,
                "parent_sitemap": record.parent_sitemap,
                "status_code": record.status_code,
                "kind": record.kind,
                "url_count": record.url_count,
                "error": record.error,
            }
            for record in records
        ]
    )


def summary_dataframe(result: AuditResult) -> pd.DataFrame:
    urls = result.urls
    return pd.DataFrame(
        [
            {"metric": "total_urls", "value": len(urls)},
            {
                "metric": "urls_with_status",
                "value": sum(1 for item in urls if item.status_code is not None),
            },
            {
                "metric": "http_4xx_or_5xx",
                "value": sum(
                    1 for item in urls if item.status_code is not None and item.status_code >= 400
                ),
            },
            {
                "metric": "noindex_urls",
                "value": sum(1 for item in urls if item.has_noindex),
            },
            {
                "metric": "nofollow_urls",
                "value": sum(1 for item in urls if item.has_nofollow),
            },
            {
                "metric": "urls_listed_in_sitemap",
                "value": sum(1 for item in urls if item.listed_in_sitemap),
            },
            {
                "metric": "urls_found_in_crawl",
                "value": sum(1 for item in urls if item.discovered_via_crawl),
            },
            {"metric": "sitemaps_audited", "value": len(result.sitemaps)},
        ]
    )


def export_audit_to_excel(result: AuditResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_dataframe(result).to_excel(
            writer,
            index=False,
            sheet_name="summary",
        )
        urls_dataframe(result.urls).to_excel(
            writer,
            index=False,
            sheet_name="urls",
        )
        issues_dataframe(result.urls).to_excel(
            writer,
            index=False,
            sheet_name="issues",
        )
        sitemaps_dataframe(result.sitemaps).to_excel(
            writer,
            index=False,
            sheet_name="sitemaps",
        )


def export_urls_to_excel(records: list[UrlRecord], output_path: Path) -> None:
    export_audit_to_excel(
        AuditResult(urls=records, sitemaps=[]),
        output_path,
    )
