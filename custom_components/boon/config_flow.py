"""Config flow for Boon Smart Home integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BoonApiClient, BoonApiError, BoonAuthError, BoonRateLimitError
from .const import (
    DOMAIN,
    CONF_PHONE_NUMBER,
    CONF_OTP_CODE,
    CONF_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    CONF_CUSTOM_CAMERAS,
)

_LOGGER = logging.getLogger(__name__)


class BoonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Boon Smart Home."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._phone_number: str | None = None
        self._custom_cameras: str | None = None
        self._api: BoonApiClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Input phone number and optional custom camera URLs."""
        errors: dict[str, str] = {}

        if user_input is not None:
            phone_number = user_input[CONF_PHONE_NUMBER].strip()
            custom_cameras = user_input.get(CONF_CUSTOM_CAMERAS, "").strip()

            if not phone_number.startswith("+") or len(phone_number) < 8:
                errors[CONF_PHONE_NUMBER] = "invalid_phone_format"
            else:
                self._phone_number = phone_number
                self._custom_cameras = custom_cameras

                session = async_get_clientsession(self.hass)
                self._api = BoonApiClient(session=session)

                try:
                    await self._api.async_send_otp(phone_number)
                    return await self.async_step_otp()
                except BoonRateLimitError:
                    errors["base"] = "rate_limit"
                except BoonApiError as err:
                    _LOGGER.error("Error sending OTP code: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.exception("Unexpected exception sending OTP: %s", err)
                    errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_PHONE_NUMBER): str,
                vol.Optional(CONF_CUSTOM_CAMERAS, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Enter SMS verification code."""
        errors: dict[str, str] = {}

        if user_input is not None and self._phone_number and self._api:
            code = user_input[CONF_OTP_CODE].strip()

            try:
                auth_data = await self._api.async_verify_otp(self._phone_number, code)
                token = auth_data.get("token")
                refresh_token = auth_data.get("refreshToken")
                user = auth_data.get("user", {})
                user_id = user.get("id", self._phone_number)

                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()

                # Fetch devices to set informative title
                title = f"Boon ({self._phone_number})"
                try:
                    devices_data = await self._api.async_get_devices()
                    flats = devices_data.get("flats", [])
                    if flats and flats[0].get("address"):
                        flat_num = flats[0].get("flatNumber")
                        title = f"Boon - {flats[0]['address']}" + (f" (Apt {flat_num})" if flat_num else "")
                except Exception:
                    pass

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_PHONE_NUMBER: self._phone_number,
                        CONF_TOKEN: token,
                        CONF_REFRESH_TOKEN: refresh_token,
                        CONF_USER_ID: user_id,
                        CONF_CUSTOM_CAMERAS: self._custom_cameras or "",
                    },
                )
            except BoonAuthError:
                errors["base"] = "invalid_code"
            except BoonApiError as err:
                _LOGGER.error("Error verifying OTP: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected exception verifying OTP: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_OTP_CODE): str,
            }
        )

        return self.async_show_form(
            step_id="otp",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "phone_number": self._phone_number or "",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BoonOptionsFlowHandler:
        """Get options flow for this handler."""
        return BoonOptionsFlowHandler(config_entry)


class BoonOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Boon (e.g. manual camera URLs)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage Boon integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_custom_cameras = self.config_entry.options.get(
            CONF_CUSTOM_CAMERAS,
            self.config_entry.data.get(CONF_CUSTOM_CAMERAS, ""),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CUSTOM_CAMERAS,
                    default=current_custom_cameras,
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
