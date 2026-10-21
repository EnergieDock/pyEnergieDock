# pyEnergieDock

[![Version](https://img.shields.io/badge/dynamic/json?url=https:%2F%2Fpypi.org%2Fpypi%2FpyEnergieDock%2Fjson&query=$.info.version&label=PyPi%20Package&color=teal)](https://pypi.org/project/pyEnergieDock/)
[![License](https://img.shields.io/badge/dynamic/json?url=https:%2F%2Fpypi.org%2Fpypi%2FpyEnergieDock%2Fjson&query=$.info.license_expression&label=License&color=green)](https://pypi.org/project/pyEnergieDock/)

An asynchronous Python client for the EnergieDock API. It is intended as a
small API layer for applications and integrations such as Home Assistant.

## Install

```shell
pip install pyEnergieDock
```

## Usage

Provide the account credentials `username` and `password` when creating the client. It authenticates on the first data request and refreshes the access token when the API rejects it.

Optional: Pass your Home Assistant Client Session with the `session` parameter*. The `api_name` parameter selects the API endpoint (default: `"ED"`).

```python
import asyncio

from pyenergiedock import DynamiT


async def main() -> None:
    async with DynamiT(
        username="<username>",
        password="<password>",
        session=ClientSession(),
        api_name="WWS",
    ) as client:
        prices = await client.async_get_latest_prices()
        measurements = await client.async_get_latest_measurements()


asyncio.run(main())
```

*If the session is passed by the Home Assistant integration, it retains ownership.

## Client API

- `async_login()` authenticates explicitly. Data requests log in automatically
  when needed.
- `async_refresh_login()` refreshes the access token, or logs in if no refresh token
  is available.
- `async_get_latest_prices()` returns today's tariff periods as a list of
  dictionaries, including the final 15-minute interval from the previous day, using the `Europe/Berlin` aggregation timezone.
- `async_get_latest_measurements()` requests quarter-hour data for the last
  24 hours and 15 minutes, using the `Europe/Berlin` aggregation timezone.
- `close()` closes only a session created by this client.
