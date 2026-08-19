from __future__ import annotations

import io
import unittest
import urllib.error
from contextlib import redirect_stdout
from email.message import Message
from unittest.mock import patch

from src.scripts import check_portfolio_mirror


class FakeResponse:
    def __init__(self, body: str) -> None:
        self.body = body.encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class PortfolioMirrorTests(unittest.TestCase):
    @staticmethod
    def complete_body() -> str:
        return "\n".join(check_portfolio_mirror.REQUIRED)

    def test_retries_temporary_fetch_failures_then_succeeds(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                check_portfolio_mirror.urllib.request,
                "urlopen",
                side_effect=[
                    OSError("temporary one"),
                    OSError("temporary two"),
                    FakeResponse(self.complete_body()),
                ],
            ) as urlopen,
            patch.object(check_portfolio_mirror.time, "sleep") as sleep,
            redirect_stdout(output),
        ):
            result = check_portfolio_mirror.main()

        self.assertEqual(result, 0)
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])
        self.assertIn("fetch attempt 1/3 failed", output.getvalue())
        self.assertIn("OK:", output.getvalue())

    def test_retries_http_429_then_succeeds(self) -> None:
        rate_limit = urllib.error.HTTPError(
            check_portfolio_mirror.PORTFOLIO_LLMS,
            429,
            "Too Many Requests",
            Message(),
            None,
        )
        with (
            patch.object(
                check_portfolio_mirror.urllib.request,
                "urlopen",
                side_effect=[rate_limit, FakeResponse(self.complete_body())],
            ) as urlopen,
            patch.object(check_portfolio_mirror.time, "sleep") as sleep,
        ):
            result = check_portfolio_mirror.main()

        self.assertEqual(result, 0)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_persistent_fetch_failure_is_a_real_failure(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                check_portfolio_mirror.urllib.request,
                "urlopen",
                side_effect=OSError("still unavailable"),
            ) as urlopen,
            patch.object(check_portfolio_mirror.time, "sleep"),
            redirect_stdout(output),
        ):
            result = check_portfolio_mirror.main()

        self.assertEqual(result, 1)
        self.assertEqual(urlopen.call_count, 3)
        self.assertIn("after 3 attempts", output.getvalue())

    def test_any_missing_cross_link_is_a_real_failure(self) -> None:
        output = io.StringIO()
        body = self.complete_body().replace("faq.jsonld", "")
        with (
            patch.object(
                check_portfolio_mirror.urllib.request,
                "urlopen",
                return_value=FakeResponse(body),
            ),
            redirect_stdout(output),
        ):
            result = check_portfolio_mirror.main()

        self.assertEqual(result, 1)
        self.assertIn("faq.jsonld", output.getvalue())


if __name__ == "__main__":
    unittest.main()
