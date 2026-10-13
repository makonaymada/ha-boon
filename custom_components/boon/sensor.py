"""Sensors for Boon Smart Home (offline keypad codes, status, and balance)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    """Set up Boon sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BoonDataUpdateCoordinator = data["coordinator"]

    entities: list[SensorEntity] = []
    devices = coordinator.data.get("devices", {})

    for vendor_id, device in devices.items():
        vendor = device.get("vendor", "sputnik")

        # 1. Online / Offline status sensor
        entities.append(BoonIntercomStatusSensor(coordinator, entry, vendor_id, vendor))

        # 2. Local / Offline door unlock passcode sensor
        meta = device.get("meta", {})
        if meta.get("offlineCode"):
            entities.append(BoonOfflineCodeSensor(coordinator, entry, vendor_id, vendor))

    # 3. Flat balance sensor
    flats = coordinator.data.get("flats", [])
    if flats:
        entities.append(BoonFlatBalanceSensor(coordinator, entry, flats[0]))

    async_add_entities(entities)


class BoonIntercomStatusSensor(BoonBaseDeviceEntity, SensorEntity):
    """Sensor reporting the cloud/connectivity state of the intercom."""

    _attr_icon = "mdi:network-outline"

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, entry, vendor_id, vendor)
        name = self.device_data.get("name", "Intercom")
        self._attr_name = f"{name} Status"
        self._attr_unique_id = f"boon_{self.vendor_id}_status"

    @property
    def native_value(self) -> str | None:
        """Return device state."""
        return self.device_data.get("state", "unknown")


class BoonOfflineCodeSensor(BoonBaseDeviceEntity, SensorEntity):
    """Sensor exposing the local physical keypad unlock code for internet/connectivity outages."""

    _attr_icon = "mdi:key-wireless"

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
    ) -> None:
        """Initialize offline code sensor."""
        super().__init__(coordinator, entry, vendor_id, vendor)
        name = self.device_data.get("name", "Intercom")
        self._attr_name = f"{name} Offline Door Code"
        self._attr_unique_id = f"boon_{self.vendor_id}_offline_code"

    @property
    def native_value(self) -> str | None:
        """Return the physical keypad offline code."""
        meta = self.device_data.get("meta", {})
        return meta.get("offlineCode")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details and instructions for offline keypad unlock."""
        meta = self.device_data.get("meta", {})
        return {
            "instructions": "Enter this code directly on the intercom physical keypad for emergency offline entry",
            "hardware_version": meta.get("hardwareVersion"),
            "software_version": meta.get("softwareVersion"),
            "ble_version": meta.get("bleVersion"),
            "serial_number": meta.get("serialNumber"),
            "motherboard_id": meta.get("motherboardId"),
        }


class BoonFlatBalanceSensor(SensorEntity):
    """Sensor displaying account/flat balance."""

    _attr_icon = "mdi:cash"

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        flat_data: dict[str, Any],
    ) -> None:
        """Initialize balance sensor."""
        super().__init__()
        self.coordinator = coordinator
        self.entry = entry
        self.flat_id = flat_data.get("id", "default")
        self._attr_name = "Boon Apartment Balance"
        self._attr_unique_id = f"boon_flat_balance_{self.flat_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking to Boon account."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"account_{self.entry.entry_id}")},
            name="Boon Account",
            manufacturer="Boon",
            model="Apartment Subscription",
        )

    @property
    def native_value(self) -> float | None:
        """Return current balance."""
        flats = self.coordinator.data.get("flats", [])
        if flats:
            return flats[0].get("balance")
        return None
