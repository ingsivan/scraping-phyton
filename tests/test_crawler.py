from __future__ import annotations

import threading
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from site_urls_scraper.crawler import CrawlConfig, audit_site, crawl_site


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "site"


class FixtureRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        if self.path.startswith("/contact"):
            self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@contextmanager
def run_fixture_server():
    handler = partial(FixtureRequestHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class CrawlSiteTests(unittest.TestCase):
    def test_crawl_site_discovers_internal_urls_only(self):
        with run_fixture_server() as base_url:
            results = crawl_site(
                CrawlConfig(
                    start_url=base_url,
                    max_pages=10,
                    timeout=5,
                    include_fragments=False,
                )
            )

        urls = {item.url for item in results}

        self.assertIn(f"{base_url}/", urls)
        self.assertIn(f"{base_url}/about.html", urls)
        self.assertIn(f"{base_url}/contact", urls)
        self.assertNotIn("https://external.example.com/page", urls)
        self.assertNotIn(f"{base_url}/asset.pdf", urls)

        visited = [item for item in results if item.status_code == 200]
        self.assertEqual(len(visited), 3)

    def test_audit_site_combines_sitemaps_and_indexability(self):
        with run_fixture_server() as base_url:
            result = audit_site(
                CrawlConfig(
                    start_url=base_url,
                    max_pages=10,
                    timeout=5,
                    include_fragments=False,
                ),
                audit_indexability=True,
                include_sitemaps=True,
            )

        records = {item.url: item for item in result.urls}
        hidden_url = f"{base_url}/hidden.html"
        contact_url = f"{base_url}/contact"

        self.assertIn(hidden_url, records)
        self.assertTrue(records[hidden_url].listed_in_sitemap)
        self.assertFalse(records[hidden_url].discovered_via_crawl)
        self.assertTrue(records[hidden_url].has_noindex)
        self.assertTrue(records[hidden_url].has_nofollow)

        self.assertIn(contact_url, records)
        self.assertEqual(records[contact_url].x_robots_tag, "noindex, nofollow")
        self.assertTrue(records[contact_url].has_noindex)
        self.assertTrue(records[contact_url].has_nofollow)

        sitemap_urls = {item.sitemap_url for item in result.sitemaps}
        self.assertIn(f"{base_url}/sitemap.xml", sitemap_urls)
        self.assertIn(f"{base_url}/sitemap-pages.xml", sitemap_urls)


if __name__ == "__main__":
    unittest.main()
