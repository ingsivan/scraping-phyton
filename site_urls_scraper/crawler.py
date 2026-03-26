from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import sleep
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


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
    depth: int
    source_url: str | None
    status_code: int | None = None


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


def crawl_site(config: CrawlConfig) -> list[UrlRecord]:
    start_url = normalize_url(config.start_url, config.include_fragments)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SiteUrlsScraper/1.0; +https://localhost)"
            )
        }
    )

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

        record = UrlRecord(url=current_url, depth=depth, source_url=source_url)
        seen[current_url] = record

        try:
            response = session.get(
                current_url,
                timeout=config.timeout,
                allow_redirects=True,
            )
            record.status_code = response.status_code
            pages_visited += 1
        except requests.RequestException:
            continue

        final_url = normalize_url(response.url, config.include_fragments)
        if final_url != current_url:
            seen.pop(current_url, None)
            record.url = final_url
            current_url = final_url
            if current_url in seen:
                continue
            seen[current_url] = record

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            continue

        child_links = extract_links(
            html=response.text,
            current_url=current_url,
            start_url=start_url,
            include_fragments=config.include_fragments,
            allow_subdomains=config.allow_subdomains,
        )

        for link in child_links:
            if link not in seen:
                queue.append((link, depth + 1, current_url))

        if config.delay > 0:
            sleep(config.delay)

    return sorted(seen.values(), key=lambda item: (item.depth, item.url))
