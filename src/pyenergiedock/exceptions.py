"""Exceptions raised by the EnergieDock client."""


class EdError(Exception):
    """Base exception for EnergieDock client errors."""


class EdAuthError(EdError):
    """Raised when credentials or an access token are rejected."""


class EdAPIError(EdError):
    """Raised when the EnergieDock API returns an unsuccessful response."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
