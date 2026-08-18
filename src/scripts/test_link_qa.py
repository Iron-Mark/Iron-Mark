from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.scripts import link_qa


class LinkQaTests(unittest.TestCase):
    def test_http_status_classification(self) -> None:
        for status in (200, 204, 301, 399):
            with self.subTest(status=status):
                self.assertEqual(link_qa.classify_http_status(status), "ok")

        self.assertEqual(link_qa.classify_http_status(429), "transient:429")

        for status in (0, 404, 500):
            with self.subTest(status=status):
                self.assertEqual(link_qa.classify_http_status(status), f"fail:{status}")

    def run_main_with_status(self, status: str) -> tuple[int, str]:
        url = "https://example.com/test"
        output = io.StringIO()
        with (
            patch.object(link_qa, "extract_urls", return_value={url}),
            patch.object(link_qa, "check_local_links", return_value=[]),
            patch.object(link_qa, "check", return_value=(url, status)),
            patch("sys.argv", ["link_qa.py"]),
            redirect_stdout(output),
        ):
            result = link_qa.main()
        return result, output.getvalue()

    def test_429_is_visible_but_does_not_fail(self) -> None:
        result, output = self.run_main_with_status("transient:429")

        self.assertEqual(result, 0)
        self.assertIn("transient warnings 1", output)
        self.assertIn("warning:transient:429", output)

    def test_real_http_failure_still_fails(self) -> None:
        result, output = self.run_main_with_status("fail:404")

        self.assertEqual(result, 1)
        self.assertIn("issues 1", output)
        self.assertIn("fail:404", output)


if __name__ == "__main__":
    unittest.main()
