from __future__ import annotations

import unittest
from typing import Any
from pyenergiedock import DynamiT


class MockResponse:
    def __init__(self, status: int, data: Any) -> None:
        self.status = status
        self.data = data

    async def __aenter__(self) -> MockResponse:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def json(self) -> Any:
        return self.data


class MockSession:
    def __init__(
        self,
        *,
        post_responses: list[MockResponse],
        get_responses: list[MockResponse],
    ) -> None:
        self.post_responses = post_responses
        self.get_responses = get_responses
        self.closed = False
        self.requests: list[tuple[str, str]] = []

    def post(self, url: str, **__: Any) -> MockResponse:
        self.requests.append(("POST", url))
        return self.post_responses.pop(0)

    def get(self, url: str, **__: Any) -> MockResponse:
        self.requests.append(("GET", url))
        return self.get_responses.pop(0)

    async def close(self) -> None:
        self.closed = True


class EnergieDockTests(unittest.IsolatedAsyncioTestCase):
    async def test_wws_client_name(self) -> None:
        session = MockSession(
            post_responses=[
                MockResponse(
                    200, {"access_token": "access", "refresh_token": "refresh"}
                )
            ],
            get_responses=[],
        )
        client = DynamiT(
            "user",
            "password",
            session=session,
            api_name="WWS",
        )

        await client.async_login()

        self.assertEqual(
            session.requests,
            [
                (
                    "POST",
                    "https://api.wws.tarifdynamik.de/public/tokens/"
                )
            ],
        )

    async def test_api(self) -> None:
        session = MockSession(
            post_responses=[
                MockResponse(
                    200, {"access_token": "access", "refresh_token": "refresh"}
                )
            ],
            get_responses=[
                MockResponse(200, {"data": []}),
                MockResponse(200, {"data": {"values": []}}),
            ],
        )
        client = DynamiT(
            "user",
            "password",
            session=session,
        )

        await client.async_get_latest_prices()
        await client.async_get_latest_measurements()
        self.assertEqual(
            session.requests,
            [
                (
                    "POST",
                    "https://api.ed-live.dynatarif.de/public/tokens/"
                ),
                (
                    "GET",
                    "https://api.ed-live.dynatarif.de/public/energyprices",
                ),
                (
                    "GET",
                    "https://api.ed-live.dynatarif.de/public/measurements/",
                ),
            ],
        )
        await client.close()
        self.assertFalse(session.closed)


if __name__ == "__main__":
    unittest.main()
