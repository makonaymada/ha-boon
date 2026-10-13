"""Button entities for Boon Smart Home (door & gate unlock)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BoonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boon button entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BoonDataUpdateCoordinator = data["coordinator"]

    entities: list[ButtonEntity] = []
    devices = coordinator.data.get("devices", {})

    for vendor_id, device in devices.items():
        vendor = device.get("vendor", "sputnik")
        capabilities = device.get("capabilities", [])

        if "open" in capabilities or device.get("type") in ("intercom", "barrier", "gate"):
            entities.append(BoonOpenDoorButton(coordinator, entry, vendor_id, vendor))

            meta = device.get("meta", {})
            if meta.get("hasSecondDoor"):
                entities.append(BoonOpenSecondDoorButton(coordinator, entry, vendor_id, vendor))

    async_add_entities(entities)


class BoonBaseDeviceEntity(CoordinatorEntity[BoonDataUpdateCoordinator]):
    """Base entity for Boon devices."""

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.vendor_id = vendor_id
        self.vendor = vendor

    @property
    def device_data(self) -> dict[str, Any]:
        """Return the device data from coordinator."""
        return self.coordinator.data.get("devices", {}).get(self.vendor_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        dev = self.device_data
        meta = dev.get("meta", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self.vendor_id)},
            name=dev.get("name", "Boon Intercom"),
            manufacturer="Sputnik / Boon",
            model=f"Hardware {meta.get('hardwareVersion', 'Intercom')}",
            sw_version=meta.get("softwareVersion"),
            suggested_area="Entrance",
        )


class BoonOpenDoorButton(BoonBaseDeviceEntity, ButtonEntity):
    """Button entity to unlock building gate or intercom door."""

    _attr_icon = "mdi:door-open"

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize the unlock button."""
        super().__init__(coordinator, entry, vendor_id, vendor)
        name = self.device_data.get("name", "Intercom")
        self._attr_name = f"{name} Unlock"
        self._attr_unique_id = f"boon_{self.vendor_id}_unlock"

    async def async_press(self) -> None:
        """Handle button press to unlock door."""
        _LOGGER.info("Unlocking Boon door: %s (%s)", self.vendor_id, self.vendor)
        await self.coordinator.api.async_open_door(self.vendor, self.vendor_id, second_door=False)


class BoonOpenSecondDoorButton(BoonBaseDeviceEntity, ButtonEntity):
    """Button entity to unlock the second door if present."""

    _attr_icon = "mdi:door-open"

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize second door button."""
        super().__init__(coordinator, entry, vendor_id, vendor)
        name = self.device_data.get("name", "Intercom")
        second_name = self.device_data.get("meta", {}).get("secondDoorName", "Second Door")
        self._attr_name = f"{name} {second_name} Unlock"
        self._attr_unique_id = f"boon_{self.vendor_id}_unlock_second"

    async def async_press(self) -> None:
        """Handle button press to unlock second door."""
        _LOGGER.info("Unlocking Boon second door: %s (%s)", self.vendor_id, self.vendor)
        await self.coordinator.api.async_open_door(self.vendor, self.vendor_id, second_door=True)
