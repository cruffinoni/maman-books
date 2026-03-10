"""
E2E tests for _get_download_links against the live Anna's Archive site.

These tests make real HTTP requests. They will fail if the site is unreachable
or if the page structure changes.

Known book: "Les secrets de la femme de ménage"
  md5 = e2bc19072aa5ad6691195d082d7a3c90
  Servers #1-4: "slightly faster but with waitlist"  → must be excluded
  Servers #5-9: "no waitlist, but can be very slow" → must be included
"""

import unittest

import httpx

from services.anna_archive import _get_download_links

_MD5 = "e2bc19072aa5ad6691195d082d7a3c90"
_BASE = "https://annas-archive.gl"
_FALLBACK = f"{_BASE}/slow_download/{_MD5}/0/0"

_WAITLISTED = [f"{_BASE}/slow_download/{_MD5}/0/{i}" for i in range(1, 4)]
_NO_WAITLIST = [f"{_BASE}/slow_download/{_MD5}/0/{i}" for i in range(4, 9)]


class TestGetDownloadLinksE2E(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        self.links = await _get_download_links(self.client, _MD5, _BASE)

    async def asyncTearDown(self):
        await self.client.aclose()

    def test_returns_list(self):
        self.assertIsInstance(self.links, list)
        self.assertGreater(len(self.links), 0)

    def test_fallback_always_present(self):
        self.assertIn(_FALLBACK, self.links)

    def test_fallback_not_duplicated(self):
        self.assertEqual(self.links.count(_FALLBACK), 1)

    def test_no_waitlist_servers_included(self):
        for url in _NO_WAITLIST:
            self.assertIn(url, self.links, msg=f"Expected no-waitlist link missing: {url}")

    def test_waitlisted_servers_excluded(self):
        for url in _WAITLISTED:
            self.assertNotIn(url, self.links, msg=f"Waitlisted link must not appear: {url}")

    def test_no_onion_links(self):
        for url in self.links:
            self.assertNotIn(".onion", url, msg=f"Onion URL leaked into results: {url}")

    def test_slow_partner_links_before_fallback(self):
        fallback_idx = self.links.index(_FALLBACK)
        for url in _NO_WAITLIST:
            self.assertLess(
                self.links.index(url),
                fallback_idx,
                msg=f"No-waitlist link should precede fallback: {url}",
            )

    def test_all_links_are_https_or_http(self):
        for url in self.links:
            self.assertTrue(
                url.startswith("http://") or url.startswith("https://"),
                msg=f"Link has unexpected scheme: {url}",
            )


if __name__ == "__main__":
    unittest.main()
