"""DataUpdateCoordinator for Boon Smart Home."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BoonApiClient, BoonApiError, BoonAuthError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class BoonDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Boon device data from cloud API."""

    def __init__(self, hass: HomeAssistant, api: BoonApiClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.api = api
        self._last_call_id: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch devices and properties from Boon API."""
        try:
            data = await self.api.async_get_devices()
            devices_list = data.get("devices", [])
            flats_list = data.get("flats", [])

            # Map devices by vendorId for fast lookup
            devices_by_id = {
                device.get("vendorId"): device
                for device in devices_list
                if device.get("vendorId")
            }

            # Fetch history if available
            history_list = await self.api.async_get_history(page=0, size=20)

            # Check for new incoming intercom calls and fire HA event
            if history_list:
                latest_call = history_list[0]
                latest_id = latest_call.get("id")
                if latest_id and self._last_call_id is not None and latest_id != self._last_call_id:
                    _LOGGER.info("New incoming Boon intercom call detected: %s", latest_id)
                    event_data = {
                        "call_id": latest_id,
                        "intercom_id": latest_call.get("intercomId"),
                        "intercom_name": latest_call.get("intercomName"),
                        "call_time": latest_call.get("callTime"),
                        "door_open_time": latest_call.get("doorOpenTime"),
                        "opened_by": latest_call.get("openedByName"),
                        "screenshot_url": latest_call.get("screenShotUrl"),
                        "flat_number": latest_call.get("address", {}).get("flatNumber", None),
                    }
                    self.hass.bus.async_fire("boon_intercom_call", event_data)

                if latest_id:
                    self._last_call_id = latest_id

            return {
                "devices": devices_by_id,
                "raw_devices": devices_list,
                "flats": flats_list,
                "history": history_list,
            }
        except BoonAuthError as err:
            _LOGGER.error("Authentication error updating Boon data: %s", err)
            raise UpdateFailed(f"Boon authorization failed: {err}") from err
        except BoonApiError as err:
            _LOGGER.warning("Error fetching Boon device updates: %s", err)
            raise UpdateFailed(f"Communication error with Boon API: {err}") from err
