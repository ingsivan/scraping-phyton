from __future__ import annotations

import threading
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from site_urls_scraper.crawler import CrawlConfig, crawl_site


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "site"


@contextmanager
def run_fixture_server():
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
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


if __name__ == "__main__":
    unittest.main()
