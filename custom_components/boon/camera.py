"""Camera platform for Boon Smart Home (intercom & custom streams)."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .button import BoonBaseDeviceEntity
from .const import DOMAIN, CONF_CUSTOM_CAMERAS
from .coordinator import BoonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Boon camera entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BoonDataUpdateCoordinator = data["coordinator"]

    entities: list[Camera] = []
    devices = coordinator.data.get("devices", {})

    # 1. Native Intercom Cameras from Boon account
    for vendor_id, device in devices.items():
        meta = device.get("meta", {})
        rtsp_url = meta.get("cameraServerRTSP") or meta.get("cameraRtspUrl")
        snapshot_url = meta.get("cameraThumb")

        if rtsp_url or snapshot_url:
            vendor = device.get("vendor", "sputnik")
            entities.append(
                BoonIntercomCamera(
                    coordinator,
                    entry,
                    vendor_id,
                    vendor,
                    rtsp_url=rtsp_url,
                    snapshot_url=snapshot_url,
                )
            )

    # 2. Custom Manually Registered Cameras (from options or config flow)
    custom_cameras_str = entry.options.get(
        CONF_CUSTOM_CAMERAS, entry.data.get(CONF_CUSTOM_CAMERAS, "")
    )
    if custom_cameras_str:
        for idx, line in enumerate(custom_cameras_str.splitlines()):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            name = f"Boon Custom Camera {idx + 1}"
            stream_url = line
            if "=" in line:
                parts = line.split("=", 1)
                name = parts[0].strip()
                stream_url = parts[1].strip()

            if stream_url:
                entities.append(BoonCustomCamera(entry, idx, name, stream_url))

    async_add_entities(entities)


class BoonIntercomCamera(BoonBaseDeviceEntity, Camera):
    """Camera entity for Boon Intercom RTSP video feed."""

    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self,
        coordinator: BoonDataUpdateCoordinator,
        entry: ConfigEntry,
        vendor_id: str,
        vendor: str,
        rtsp_url: str | None,
        snapshot_url: str | None,
    ) -> None:
        """Initialize camera entity."""
        BoonBaseDeviceEntity.__init__(self, coordinator, entry, vendor_id, vendor)
        Camera.__init__(self)

        dev_name = self.device_data.get("name", "Entrance")
        self._attr_name = f"{dev_name} Camera"
        self._attr_unique_id = f"boon_{self.vendor_id}_camera"
        self._rtsp_url = rtsp_url
        self._snapshot_url = snapshot_url

    async def stream_source(self) -> str | None:
        """Return the RTSP stream URL for Home Assistant streaming engine."""
        return self._rtsp_url

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Fetch snapshot preview image."""
        if not self._snapshot_url:
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                self._snapshot_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                _LOGGER.debug(
                    "Snapshot URL %s returned HTTP %s", self._snapshot_url, resp.status
                )
        except Exception as err:
            _LOGGER.debug("Error fetching snapshot image from %s: %s", self._snapshot_url, err)

        return None


class BoonCustomCamera(Camera):
    """Camera entity for manually registered RTSP/HTTP camera URLs."""

    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self,
        entry: ConfigEntry,
        index: int,
        name: str,
        stream_url: str,
    ) -> None:
        """Initialize custom camera."""
        super().__init__()
        self.entry = entry
        self._attr_name = name
        self._attr_unique_id = f"boon_custom_camera_{entry.entry_id}_{index}"
        self._stream_url = stream_url

    @property
    def device_info(self) -> DeviceInfo:
        """Link to a custom cameras virtual device."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"custom_cameras_{self.entry.entry_id}")},
            name="Boon Additional Cameras",
            manufacturer="Boon",
            model="Custom Stream Feeds",
        )

    async def stream_source(self) -> str | None:
        """Return the stream URL."""
        return self._stream_url
