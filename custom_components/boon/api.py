"""API Client for Boon Smart Home (boon.systems)."""
from __future__ import annotations

import logging
from typing import Any, Callable

import aiohttp

from .const import (
    API_BASE_URL,
    DEVICE_BASE_URL,
    HEADER_ORIGIN_APP,
    DEFAULT_USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class BoonApiError(Exception):
    """General error communicating with Boon API."""


class BoonAuthError(BoonApiError):
    """Authentication or authorization failure."""


class BoonRateLimitError(BoonApiError):
    """Rate limit exceeded."""


class BoonApiClient:
    """Async API Client for interacting with Boon systems."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str | None = None,
        refresh_token: str | None = None,
        token_update_callback: Callable[[str, str], Any] | None = None,
    ) -> None:
        """Initialize the Boon API client."""
        self._session = session
        self._token = token
        self._refresh_token = refresh_token
        self._token_update_callback = token_update_callback

    @property
    def token(self) -> str | None:
        """Get the current access token."""
        return self._token

    @property
    def refresh_token(self) -> str | None:
        """Get the current refresh token."""
        return self._refresh_token

    def _headers(self, token: str | None = None) -> dict[str, str]:
        """Generate common headers for Boon API requests."""
        headers = {
            "x-origin-app": HEADER_ORIGIN_APP,
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        auth_token = token or self._token
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    async def async_send_otp(self, phone_number: str) -> bool:
        """Request an SMS verification code for a phone number."""
        url = f"{API_BASE_URL}/api/otp/send"
        payload = {"phoneNumber": phone_number}

        try:
            async with self._session.post(
                url, json=payload, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 429:
                    raise BoonRateLimitError("Too many OTP requests. Please wait a few minutes.")
                if response.status not in (200, 201):
                    text = await response.text()
                    raise BoonApiError(f"Failed to send OTP (HTTP {response.status}): {text}")
                data = await response.json()
                _LOGGER.debug("OTP request response: %s", data)
                return True
        except aiohttp.ClientError as err:
            raise BoonApiError(f"Network error sending OTP: {err}") from err

    async def async_verify_otp(self, phone_number: str, code: str) -> dict[str, Any]:
        """Verify the OTP code and obtain session tokens."""
        url = f"{API_BASE_URL}/api/otp/verify"
        payload = {"phoneNumber": phone_number, "code": code}

        try:
            async with self._session.post(
                url, json=payload, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (400, 401, 403):
                    text = await response.text()
                    raise BoonAuthError(f"Invalid verification code or unauthorized: {text}")
                if response.status not in (200, 201):
                    text = await response.text()
                    raise BoonApiError(f"Failed to verify OTP (HTTP {response.status}): {text}")

                res_json = await response.json()
                data = res_json.get("data", {})
                token = data.get("token")
                refresh_token = data.get("refreshToken")

                if not token:
                    raise BoonAuthError(f"Response missing access token: {res_json}")

                self._token = token
                self._refresh_token = refresh_token
                return data
        except aiohttp.ClientError as err:
            raise BoonApiError(f"Network error verifying OTP: {err}") from err

    async def async_refresh_tokens(self) -> tuple[str, str]:
        """Refresh the access token using the stored refresh token."""
        if not self._refresh_token:
            raise BoonAuthError("No refresh token available to renew session.")

        url = f"{API_BASE_URL}/api/users/token/refresh"
        headers = self._headers(token=self._refresh_token)

        try:
            async with self._session.post(
                url, json={}, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (401, 403):
                    text = await response.text()
                    raise BoonAuthError(f"Refresh token expired or rejected: {text}")
                if response.status != 200:
                    text = await response.text()
                    raise BoonApiError(f"Token refresh failed (HTTP {response.status}): {text}")

                res_json = await response.json()
                data = res_json.get("data", {})
                new_token = data.get("token")
                new_refresh = data.get("refreshToken", self._refresh_token)

                if not new_token:
                    raise BoonAuthError("Renewed token response did not contain access token.")

                self._token = new_token
                self._refresh_token = new_refresh

                if self._token_update_callback:
                    if callable(self._token_update_callback):
                        res = self._token_update_callback(new_token, new_refresh)
                        if hasattr(res, "__await__"):
                            await res

                _LOGGER.info("Successfully refreshed Boon session tokens.")
                return new_token, new_refresh
        except aiohttp.ClientError as err:
            raise BoonApiError(f"Network error refreshing token: {err}") from err

    async def async_request(self, method: str, url: str, json_body: dict[str, Any] | None = None) -> Any:
        """Perform an authenticated request with automatic token refresh on 401/403."""
        headers = self._headers()
        try:
            async with self._session.request(
                method, url, json=json_body or {}, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status in (401, 403) and self._refresh_token:
                    _LOGGER.warning("Boon API returned %s. Attempting token refresh...", response.status)
                    await self.async_refresh_tokens()
                    headers = self._headers()
                    async with self._session.request(
                        method, url, json=json_body or {}, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
                    ) as retry_resp:
                        if retry_resp.status in (401, 403):
                            raise BoonAuthError("Unauthorized after token refresh.")
                        if retry_resp.status not in (200, 204):
                            raise BoonApiError(f"Request failed after refresh: HTTP {retry_resp.status}")
                        if retry_resp.status == 204:
                            return {}
                        return await retry_resp.json()

                if response.status == 204:
                    return {}
                if response.status not in (200, 201):
                    text = await response.text()
                    raise BoonApiError(f"Request {method} {url} failed (HTTP {response.status}): {text}")

                return await response.json()
        except aiohttp.ClientError as err:
            raise BoonApiError(f"Network error for {url}: {err}") from err

    async def async_get_devices(self) -> dict[str, Any]:
        """Fetch all devices (intercoms, gates, elevators) associated with the account."""
        url = f"{DEVICE_BASE_URL}/devices"
        return await self.async_request("GET", url)

    async def async_open_door(self, vendor: str, vendor_id: str, second_door: bool = False) -> bool:
        """Send unlock/open signal to the specified intercom gate or door."""
        endpoint = "open-second" if second_door else "open"
        url = f"{DEVICE_BASE_URL}/devices/{vendor}/{vendor_id}/{endpoint}"
        await self.async_request("POST", url, json_body={})
        _LOGGER.info("Successfully sent open door signal to %s/%s (%s)", vendor, vendor_id, endpoint)
        return True

    async def async_link_intercom(self, code: str, name: str = "Home Assistant", flat_number: int | None = None) -> dict[str, Any]:
        """Link an intercom or flat to the account using an invite code."""
        # 1. Fetch intercom address metadata for this code if needed
        flat_num = flat_number
        if flat_num is None:
            try:
                info_res = await self.async_request("GET", f"{API_BASE_URL}/api/intercoms?code={code}")
                flat_num = info_res.get("data", {}).get("flatNumber", None)
            except Exception:
                flat_num = None

        url = f"{API_BASE_URL}/api/intercoms/link"
        body = {
            "code": code,
            "name": name,
            "flatNumber": flat_num,
        }
        res = await self.async_request("PUT", url, json_body=body)
        _LOGGER.info("Successfully linked intercom via code %s for flat %s", code, flat_num)
        return res

    async def async_get_history(self, page: int = 0, size: int = 20) -> list[dict[str, Any]]:
        """Fetch intercom call and door history from Boon API."""
        url = f"{API_BASE_URL}/api/history?page={page}&size={size}"
        try:
            res = await self.async_request("GET", url)
            if isinstance(res, dict):
                return res.get("data", [])
            if isinstance(res, list):
                return res
            return []
        except Exception as err:
            _LOGGER.debug("Could not fetch Boon history: %s", err)
            return []

