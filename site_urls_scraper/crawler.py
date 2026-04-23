from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from time import sleep
from urllib.parse import urljoin, urlparse, urlunparse
import warnings

import requests
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
from bs4.exceptions import FeatureNotFound


SKIPPED_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "ftp:")
SKIPPED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
    ".zip",
    ".rar",
    ".7z",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".woff",
    ".woff2",
    ".ttf",
    ".css",
    ".js",
    ".xml",
    ".ico",
)
SEO_META_NAMES = {"robots", "googlebot", "bingbot", "slurp"}


@dataclass(slots=True)
class CrawlConfig:
    start_url: str
    max_pages: int = 200
    timeout: float = 10.0
    delay: float = 0.0
    include_fragments: bool = False
    allow_subdomains: bool = False


@dataclass(slots=True)
class UrlRecord:
    url: str
    depth: int | None
    source_url: str | None
    status_code: int | None = None
    discovered_via_crawl: bool = False
    listed_in_sitemap: bool = False
    sitemap_sources: list[str] = field(default_factory=list)
    meta_robots: str | None = None
    x_robots_tag: str | None = None
    has_noindex: bool = False
    has_nofollow: bool = False


@dataclass(slots=True)
class SitemapRecord:
    sitemap_url: str
    parent_sitemap: str | None
    status_code: int | None = None
    kind: str | None = None
    url_count: int = 0
    error: str | None = None


@dataclass(slots=True)
class AuditResult:
    urls: list[UrlRecord]
    sitemaps: list[SitemapRecord]


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SiteUrlsScraper/1.0; +https://localhost)"
            )
        }
    )
    return session


def normalize_url(url: str, include_fragments: bool) -> str:
    raw_url = url.strip()
    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"

    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    fragment = parsed.fragment if include_fragments else ""
    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        params="",
        fragment=fragment,
    )
    return urlunparse(normalized)


def is_internal_url(target_url: str, base_url: str, allow_subdomains: bool) -> bool:
    target_host = urlparse(target_url).hostname or ""
    base_host = urlparse(base_url).hostname or ""

    if allow_subdomains:
        return target_host == base_host or target_host.endswith(f".{base_host}")

    return target_host == base_host


def should_skip_url(url: str) -> bool:
    lowered = url.lower()
    return lowered.startswith(SKIPPED_SCHEMES) or lowered.endswith(SKIPPED_EXTENSIONS)


def extract_links(
    html: str,
    current_url: str,
    start_url: str,
    include_fragments: bool,
    allow_subdomains: bool,
) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or should_skip_url(href):
            continue

        absolute_url = urljoin(current_url, href)
        normalized_url = normalize_url(absolute_url, include_fragments)

        if not is_internal_url(normalized_url, start_url, allow_subdomains):
            continue

        if should_skip_url(normalized_url):
            continue

        links.append(normalized_url)

    return links


def parse_directive_tokens(value: str | None) -> set[str]:
    if not value:
        return set()

    tokens: set[str] = set()
    normalized = value.replace(";", ",")
    for chunk in normalized.split(","):
        token = chunk.strip().lower()
        if token:
            tokens.add(token)

    return tokens


def extract_robots_directives(html: str) -> tuple[str | None, bool, bool]:
    soup = BeautifulSoup(html, "html.parser")
    directives: list[str] = []
    has_noindex = False
    has_nofollow = False

    for meta_tag in soup.find_all("meta"):
        name = meta_tag.get("name", "").strip().lower()
        if name not in SEO_META_NAMES:
            continue

        content = meta_tag.get("content", "").strip()
        if not content:
            continue

        directives.append(f"{name}: {content}")
        tokens = parse_directive_tokens(content)
        has_noindex = has_noindex or "noindex" in tokens
        has_nofollow = has_nofollow or "nofollow" in tokens

    if not directives:
        return None, False, False

    return " | ".join(directives), has_noindex, has_nofollow


def apply_response_metadata(
    record: UrlRecord,
    response: requests.Response,
    audit_indexability: bool,
) -> str:
    record.status_code = response.status_code
    record.x_robots_tag = response.headers.get("X-Robots-Tag") or None

    header_tokens = parse_directive_tokens(record.x_robots_tag)
    has_noindex = "noindex" in header_tokens
    has_nofollow = "nofollow" in header_tokens

    content_type = response.headers.get("Content-Type", "").lower()
    if audit_indexability and "text/html" in content_type:
        meta_robots, meta_noindex, meta_nofollow = extract_robots_directives(
            response.text
        )
        record.meta_robots = meta_robots
        has_noindex = has_noindex or meta_noindex
        has_nofollow = has_nofollow or meta_nofollow

    record.has_noindex = has_noindex
    record.has_nofollow = has_nofollow
    return content_type


def fetch_url_record(
    session: requests.Session,
    record: UrlRecord,
    config: CrawlConfig,
    audit_indexability: bool,
) -> tuple[str, str, str | None] | None:
    try:
        response = session.get(
            record.url,
            timeout=config.timeout,
            allow_redirects=True,
        )
    except requests.RequestException:
        return None

    final_url = normalize_url(response.url, config.include_fragments)
    content_type = apply_response_metadata(record, response, audit_indexability)
    html = response.text if "text/html" in content_type else None

    if config.delay > 0:
        sleep(config.delay)

    return final_url, content_type, html


def merge_url_records(target: UrlRecord, incoming: UrlRecord) -> None:
    if target.depth is None or (
        incoming.depth is not None and incoming.depth < target.depth
    ):
        target.depth = incoming.depth

    if target.source_url is None and incoming.source_url is not None:
        target.source_url = incoming.source_url

    if target.status_code is None and incoming.status_code is not None:
        target.status_code = incoming.status_code

    if target.meta_robots is None and incoming.meta_robots is not None:
        target.meta_robots = incoming.meta_robots

    if target.x_robots_tag is None and incoming.x_robots_tag is not None:
        target.x_robots_tag = incoming.x_robots_tag

    target.discovered_via_crawl = target.discovered_via_crawl or incoming.discovered_via_crawl
    target.listed_in_sitemap = target.listed_in_sitemap or incoming.listed_in_sitemap
    target.has_noindex = target.has_noindex or incoming.has_noindex
    target.has_nofollow = target.has_nofollow or incoming.has_nofollow

    existing_sources = set(target.sitemap_sources)
    for sitemap_url in incoming.sitemap_sources:
        if sitemap_url not in existing_sources:
            target.sitemap_sources.append(sitemap_url)
            existing_sources.add(sitemap_url)


def sort_url_records(records: list[UrlRecord]) -> list[UrlRecord]:
    return sorted(
        records,
        key=lambda item: (
            item.depth is None,
            item.depth if item.depth is not None else 10**9,
            item.url,
        ),
    )


def crawl_site(
    config: CrawlConfig,
    *,
    session: requests.Session | None = None,
    audit_indexability: bool = False,
) -> list[UrlRecord]:
    start_url = normalize_url(config.start_url, config.include_fragments)
    http = session or build_session()

    queue = deque([(start_url, 0, None)])
    seen: dict[str, UrlRecord] = {}
    pages_visited = 0

    while queue and pages_visited < config.max_pages:
        current_url, depth, source_url = queue.popleft()

        if current_url in seen:
            existing = seen[current_url]
            if existing.source_url is None and source_url is not None:
                existing.source_url = source_url
            continue

        record = UrlRecord(
            url=current_url,
            depth=depth,
            source_url=source_url,
            discovered_via_crawl=True,
        )
        seen[current_url] = record

        fetch_result = fetch_url_record(
            http,
            record,
            config,
            audit_indexability=audit_indexability,
        )
        if fetch_result is None:
            continue

        final_url, content_type, html = fetch_result
        pages_visited += 1

        if final_url != current_url:
            seen.pop(current_url, None)
            record.url = final_url
            current_url = final_url
            existing = seen.get(current_url)
            if existing is not None:
                merge_url_records(existing, record)
                continue
            seen[current_url] = record

        if "text/html" not in content_type:
            continue

        child_links = extract_links(
            html=html or "",
            current_url=current_url,
            start_url=start_url,
            include_fragments=config.include_fragments,
            allow_subdomains=config.allow_subdomains,
        )

        for link in child_links:
            if link not in seen:
                queue.append((link, depth + 1, current_url))

    return sort_url_records(list(seen.values()))


def parse_robots_sitemaps(robots_text: str, start_url: str, include_fragments: bool) -> list[str]:
    sitemap_urls: list[str] = []

    for line in robots_text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue

        field_name, _, raw_value = stripped.partition(":")
        if field_name.strip().lower() != "sitemap":
            continue

        sitemap_url = urljoin(start_url, raw_value.strip())
        sitemap_urls.append(normalize_url(sitemap_url, include_fragments))

    return sitemap_urls


def discover_sitemap_urls(
    config: CrawlConfig,
    session: requests.Session,
) -> list[str]:
    start_url = normalize_url(config.start_url, config.include_fragments)
    robots_url = urljoin(start_url, "/robots.txt")

    try:
        response = session.get(
            robots_url,
            timeout=config.timeout,
            allow_redirects=True,
        )
    except requests.RequestException:
        response = None

    if response is not None and config.delay > 0:
        sleep(config.delay)

    if response is not None and response.ok:
        sitemap_urls = parse_robots_sitemaps(
            response.text,
            start_url,
            config.include_fragments,
        )
        if sitemap_urls:
            return sitemap_urls

    return [normalize_url(urljoin(start_url, "/sitemap.xml"), config.include_fragments)]


def parse_sitemap_document(xml_text: str) -> tuple[str | None, list[str]]:
    try:
        soup = BeautifulSoup(xml_text, "xml")
    except FeatureNotFound:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(xml_text, "html.parser")

    sitemap_nodes = soup.find_all("sitemap")
    if sitemap_nodes:
        return (
            "index",
            [
                node.loc.get_text(strip=True)
                for node in sitemap_nodes
                if node.loc and node.loc.get_text(strip=True)
            ],
        )

    url_nodes = soup.find_all("url")
    if url_nodes:
        return (
            "urlset",
            [
                node.loc.get_text(strip=True)
                for node in url_nodes
                if node.loc and node.loc.get_text(strip=True)
            ],
        )

    loc_nodes = [node.get_text(strip=True) for node in soup.find_all("loc")]
    if loc_nodes:
        return "urlset", [loc for loc in loc_nodes if loc]

    return None, []


def audit_sitemaps(
    config: CrawlConfig,
    session: requests.Session,
) -> tuple[dict[str, set[str]], list[SitemapRecord]]:
    queued_sitemaps = deque(
        (sitemap_url, None) for sitemap_url in discover_sitemap_urls(config, session)
    )
    seen_sitemaps: set[str] = set()
    sitemap_records: list[SitemapRecord] = []
    sitemap_urls_by_page: dict[str, set[str]] = defaultdict(set)

    while queued_sitemaps:
        sitemap_url, parent_sitemap = queued_sitemaps.popleft()
        if sitemap_url in seen_sitemaps:
            continue

        seen_sitemaps.add(sitemap_url)
        record = SitemapRecord(
            sitemap_url=sitemap_url,
            parent_sitemap=parent_sitemap,
        )
        sitemap_records.append(record)

        try:
            response = session.get(
                sitemap_url,
                timeout=config.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            record.error = str(exc)
            if config.delay > 0:
                sleep(config.delay)
            continue

        record.status_code = response.status_code
        final_sitemap_url = normalize_url(response.url, config.include_fragments)
        if final_sitemap_url != sitemap_url:
            record.sitemap_url = final_sitemap_url
            seen_sitemaps.add(final_sitemap_url)

        kind, discovered_locs = parse_sitemap_document(response.text)
        record.kind = kind or "unknown"
        record.url_count = len(discovered_locs)

        if kind == "index":
            for discovered_url in discovered_locs:
                child_sitemap = normalize_url(
                    urljoin(record.sitemap_url, discovered_url),
                    config.include_fragments,
                )
                queued_sitemaps.append((child_sitemap, record.sitemap_url))
        elif kind == "urlset":
            for discovered_url in discovered_locs:
                normalized_url = normalize_url(
                    urljoin(record.sitemap_url, discovered_url),
                    config.include_fragments,
                )
                sitemap_urls_by_page[normalized_url].add(record.sitemap_url)
        else:
            record.error = "No se pudo identificar sitemapindex o urlset"

        if config.delay > 0:
            sleep(config.delay)

    return sitemap_urls_by_page, sitemap_records


def audit_site(
    config: CrawlConfig,
    *,
    audit_indexability: bool = False,
    include_sitemaps: bool = False,
) -> AuditResult:
    session = build_session()
    records = {
        record.url: record
        for record in crawl_site(
            config,
            session=session,
            audit_indexability=audit_indexability,
        )
    }
    sitemap_records: list[SitemapRecord] = []

    if include_sitemaps:
        sitemap_urls_by_page, sitemap_records = audit_sitemaps(config, session)
        for url, sitemap_sources in sitemap_urls_by_page.items():
            existing = records.get(url)
            if existing is None:
                existing = UrlRecord(url=url, depth=None, source_url=None)
                records[url] = existing

            existing.listed_in_sitemap = True
            existing_sources = set(existing.sitemap_sources)
            for sitemap_url in sorted(sitemap_sources):
                if sitemap_url not in existing_sources:
                    existing.sitemap_sources.append(sitemap_url)
                    existing_sources.add(sitemap_url)

        pending_urls = [url for url, record in records.items() if record.status_code is None]
        for pending_url in pending_urls:
            record = records.get(pending_url)
            if record is None:
                continue

            fetch_result = fetch_url_record(
                session,
                record,
                config,
                audit_indexability=audit_indexability,
            )
            if fetch_result is None:
                continue

            final_url, _, _ = fetch_result
            if final_url == pending_url:
                continue

            records.pop(pending_url, None)
            record.url = final_url
            existing = records.get(final_url)
            if existing is not None:
                merge_url_records(existing, record)
            else:
                records[final_url] = record

    return AuditResult(
        urls=sort_url_records(list(records.values())),
        sitemaps=sorted(
            sitemap_records,
            key=lambda item: (item.parent_sitemap or "", item.sitemap_url),
        ),
    )
