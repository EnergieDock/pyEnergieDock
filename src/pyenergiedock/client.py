"""Asynchronous client for the EnergieDock API."""

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin
from aiohttp import ClientError, ClientSession, ClientTimeout 
from .const import BASE_URL, WWS_BASE_URL
from .exceptions import EdAPIError, EdAuthError


class DynamiT:
    """Asynchronous EnergieDock API client.
    """
    def __init__(
        self,
        username: str,
        password: str,
        *,
        session: ClientSession | None = None,
        api_name: str = "ED",
    ) -> None:
        if not username or not password:
            raise ValueError("username and password must not be empty")
        
        # Select the appropriate base URL based on the api_name
        if api_name.upper() == "WWS":
            base_url = WWS_BASE_URL
        elif api_name.upper() == "ED":
            base_url = BASE_URL
        else:
            base_url = BASE_URL

        self._base_url = f"{base_url.rstrip('/')}/"
        self._username = username
        self._password = password
        self._session = session
        self._owns_session = session is None

        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def __aenter__(self) -> DynamiT:
        self._get_session()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the HTTP session if it was created by this client."""
        if self._owns_session:
            if not self._session.closed:
                await self._session.close()
            self._session = None

    def _get_session(self) -> ClientSession:
        """Get or create the aiohttp session."""
        if self._owns_session or self._session.closed:
            self._session = ClientSession(
                base_url=self._base_url,
                timeout=ClientTimeout(total=30.0)
            )
            self._owns_session = True
        return self._session

    def _url(self, path: str) -> str:
        """Return the full URL for a given API path."""
        return urljoin(self._base_url, path.lstrip("/"))

    async def async_login(self) -> None:
        """Authenticate the user with the provided credentials."""
        await self._async_get_token(
            {
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
            }
        )

    async def async_refresh_login(self) -> None:
        """Refresh the access token, logging in again if refresh fails."""
        if self._refresh_token is None:
            await self.async_login()
            return

        await self._async_get_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            }
        )

    async def _async_get_token(self, data: dict[str, str]) -> None:
        try:
            async with self._get_session().post(
                self._url("tokens/"), data=data
            ) as response:
                if response.status in (400, 401, 403):
                    raise EdAuthError("The credentials were rejected.")
                if response.status != 200:
                    raise EdAPIError(
                        f"Token request failed with HTTP {response.status}",
                        status=response.status,
                    )
                token_data = await response.json()
        
        except ClientError as err:
            raise EdAPIError("Could not communicate with the EnergieDock API") from err

        if "access_token" not in token_data or "refresh_token" not in token_data:
            raise EdAPIError("Token response is missing the access- or refresh-token")
        else:
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

    async def _get_authenticated_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        allow_conflict: bool = False,
    ) -> Any:
        if self._access_token is None:
            await self.async_login()

        for attempt in range(2):
            try:
                async with self._get_session().get(
                    self._url(path),
                    params=params,
                    headers={"Authorization": f"Bearer {self._access_token}"},
                ) as response:
                    if response.status in (401, 403):
                        if attempt == 0:
                            # Try to refresh the token and retry the request
                            self._access_token = None
                            await self.async_refresh_login()
                            continue
                        raise EdAuthError("The refreshed access token was rejected.")
                    if response.status == 409 and allow_conflict:
                        return None
                    if response.status != 200:
                        raise EdAPIError(
                            f"API request failed with HTTP {response.status}",
                            status=response.status,
                        )
                    return await response.json()
            except ClientError as err:
                raise EdAPIError(
                    "Could not communicate with the EnergieDock API."
                ) from err

        raise EdAuthError("Could not authenticate with the EnergieDock API")

    async def async_get_latest_prices(self) -> list[dict[str, Any]]:
        """Return the latest tariff periods."""
        data = await self._get_authenticated_json(
            "/energyprices",
            params={
                "page_size": 100,
                "sort": "valid_from:desc",
            },
        )
        prices = data.get("data") if isinstance(data, dict) else None
        if not isinstance(prices, list):
            raise EdAPIError("Price response does not contain a data list")
        return prices

    async def async_get_latest_measurements(self) -> list[dict[str, Any]]:
        """Return the latest quarter-hour measurements for the logged-in user."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=1, minutes=15)
        data = await self._get_authenticated_json(
            "/measurements/",
            params={
                "resolution": "QUARTER_HOUR",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "aggregation_timezone": "Europe/Berlin",
            },
            allow_conflict=True,
        )
        if data is None:
            return []

        measurement_data = data.get("data") if isinstance(data, dict) else None
        if isinstance(measurement_data, list):
            return measurement_data
        if not isinstance(measurement_data, dict):
            raise EdAPIError("Measurement response has an invalid data value")

        values = measurement_data.get("values", [])
        if not isinstance(values, list):
            raise EdAPIError("Measurement response values must be a list")

        measurements: list[dict[str, Any]] = []
        for value in values:
            if not isinstance(value, dict):
                raise EdAPIError("Measurement response contains an invalid value")
            timestamp = value.get("dt")
            consumption = value.get("measurement_kwh")
            if not isinstance(timestamp, str) or not isinstance(
                consumption, (float, int)
            ):
                raise EdAPIError("Measurement value is missing dt or measurement_kwh")
            try:
                parsed_datetime = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
            except ValueError as err:
                raise EdAPIError(f"Invalid measurement timestamp: {timestamp}") from err
            measurements.append(
                {
                    "start": timestamp,
                    "end": (parsed_datetime + timedelta(minutes=15)).isoformat(),
                    "consumption_kwh": consumption,
                }
            )
        return measurements
