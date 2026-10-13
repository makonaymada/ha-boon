"""Boon Smart Home Integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BoonApiClient
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_TOKEN,
    CONF_REFRESH_TOKEN,
)
from .coordinator import BoonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Boon Smart Home from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    token = entry.data.get(CONF_TOKEN)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)

    async def async_token_updated(new_token: str, new_refresh: str) -> None:
        """Callback when API client refreshes tokens."""
        _LOGGER.debug("Persisting newly refreshed tokens to ConfigEntry")
        new_data = dict(entry.data)
        new_data[CONF_TOKEN] = new_token
        new_data[CONF_REFRESH_TOKEN] = new_refresh
        hass.config_entries.async_update_entry(entry, data=new_data)

    api = BoonApiClient(
        session=session,
        token=token,
        refresh_token=refresh_token,
        token_update_callback=async_token_updated,
    )

    coordinator = BoonDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Boon config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
