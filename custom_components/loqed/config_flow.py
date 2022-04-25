"""Config flow for Loqed integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .loqed import LoqedLockClient
from homeassistant.const import (
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_IP_ADDRESS,
    CONF_MAC,
    CONF_WEBHOOK_ID,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DO_NOT_COMMIT_API_KEY,
    DO_NOT_COMMIT_CLIENT_SECRET,
    DO_NOT_COMMIT_IP_ADDRESS,
    DO_NOT_COMMIT_LOCAL_KEY_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_CLIENT_ID): int,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass."""

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.ip_address = host

    async def authenticate(
        self,
        api_token: str,
    ) -> bool:
        """Test if we can authenticate with the host."""

        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = PlaceholderHub(data[CONF_IP_ADDRESS])

    if not await hub.authenticate(data[CONF_API_KEY]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth
    try:
        mac = (
            await LoqedLockClient(
                async_get_clientsession(hass),
                data[CONF_IP_ADDRESS],
                data[CONF_CLIENT_ID],
                data[CONF_CLIENT_SECRET],
            ).get_lock_status("")
        )["bridge_mac_wifi"]
    except Exception:  # pylint: disable=broad-except
        raise CannotConnect from Exception

    return {"title": f"Loqed bridge {data[CONF_IP_ADDRESS]}", CONF_MAC: mac}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Loqed."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:

            await self.async_set_unique_id(info[CONF_MAC])
            self._abort_if_unique_id_configured()
            webhook_id = webhook.async_generate_id()
            return self.async_create_entry(
                title=info["title"],
                data=(user_input | {CONF_WEBHOOK_ID: webhook_id} | info),
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
