"""Lock platform for Boon Smart Home (momentary buzzer strike)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .button import BoonBaseDeviceEntity
from .const import DOMAIN
from .coordinator import BoonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boon lock entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BoonDataUpdateCoordinator = data["coordinator"]

    entities: list[LockEntity] = []
    devices = coordinator.data.get("devices", {})

    for vendor_id, device in devices.items():
        vendor = device.get("vendor", "sputnik")
        capabilities = device.get("capabilities", [])

        if "open" in capabilities or device.get("type") in ("intercom", "barrier", "gate"):
            entities.append(BoonDoorLock(coordinator, entry, vendor_id, vendor))

    async_add_entities(entities)


class BoonDoorLock(BoonBaseDeviceEntity, LockEntity):
    """Lock entity representing the entrance gate."""

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize lock entity."""
        super().__init__(coordinator, entry, vendor_id, vendor)
        name = self.device_data.get("name", "Entrance Gate")
        self._attr_name = name
        self._attr_unique_id = f"boon_{self.vendor_id}_lock"
        self._attr_is_locked = True
        self._attr_is_unlocking = False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including offline access code."""
        meta = self.device_data.get("meta", {})
        code = meta.get("offlineCode")
        flat = meta.get("address", {}).get("flatNumber", None)
        attrs: dict[str, Any] = {}
        if code:
            attrs["offline_code"] = code
            attrs["keypad_code"] = code
            attrs["tooltip"] = f"Keypad code: #{flat} {code}"
            attrs["instructions"] = f"To unlock manually on the intercom keypad, enter: #{flat} followed by {code}"
        return attrs

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the entrance door via Boon API and auto-relock after buzzer delay."""
        _LOGGER.info("Unlocking Boon lock entity: %s", self.vendor_id)
        self._attr_is_unlocking = True
        self.async_write_ha_state()

        try:
            await self.coordinator.api.async_open_door(self.vendor, self.vendor_id, second_door=False)
            self._attr_is_unlocking = False
            self._attr_is_locked = False
            self.async_write_ha_state()

            # Momentary strike buzzer duration (5 seconds)
            await asyncio.sleep(5)
        finally:
            self._attr_is_locked = True
            self._attr_is_unlocking = False
            self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the door (immediately reset state if unlocked)."""
        self._attr_is_locked = True
        self.async_write_ha_state()
