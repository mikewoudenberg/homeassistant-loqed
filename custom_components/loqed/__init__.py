"""The Loqed integration."""
from __future__ import annotations

import json
import logging

from aiohttp.web import Request
import async_timeout

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_IP_ADDRESS,
    CONF_WEBHOOK_ID,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_COORDINATOR,
    CONF_LOCK_CLIENT,
    CONF_WEBHOOK_CLIENT,
    CONF_WEBHOOK_INDEX,
    DOMAIN,
)
from .loqed import (
    WEBHOOK_ALL_EVENTS_FLAG,
    LoqedException,
    LoqedLockClient,
    LoqedStatusClient,
    LoqedWebhookClient,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK]
_LOGGER = logging.getLogger(__name__)


async def handle_webhook(hass: HomeAssistant, _: str, request: Request) -> None:
    """
    Handles incoming Loqed messages
    """
    _LOGGER.debug("Received request %s", request.headers)

    timestamp = request.headers.get("timestamp", "0")
    message_hash = request.headers.get("hash", "")

    body = await request.text()
    client: LoqedWebhookClient = hass.data[DOMAIN][CONF_WEBHOOK_CLIENT]

    valid = client.validate_message(body, int(timestamp), message_hash, True)
    if not valid:
        _LOGGER.debug("Received invalid message: %s", body)
        return

    message = json.loads(body)
    coordinator: LoqedDataCoordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.async_set_updated_data(message)


async def ensure_webhooks(
    hass: HomeAssistant, webhook_id: str, webhook_client: LoqedWebhookClient
) -> int:
    """
    Ensures the existence of the webhooks on both sides
    """

    webhook.async_register(hass, DOMAIN, "Loqed", webhook_id, handle_webhook)
    webhook_url = webhook.async_generate_url(hass, webhook_id)
    _LOGGER.info("Webhook URL: %s", webhook_url)

    webhooks = await webhook_client.get_all_webhooks()
    webhook_index = next((x["id"] for x in webhooks if x["url"] == webhook_url), None)

    if not webhook_index:
        await webhook_client.setup_webhook(webhook_url, WEBHOOK_ALL_EVENTS_FLAG)
        webhooks = await webhook_client.get_all_webhooks()
        webhook_index = next(x["id"] for x in webhooks if x["url"] == webhook_url)

        _LOGGER.info("Webhook got index %s", webhook_index)

    return int(webhook_index)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loqed from a config entry."""
    _LOGGER.debug("Current domain: %s", hass.data.get(DOMAIN, ""))
    entry_config = hass.data.setdefault(DOMAIN, {})

    websession = async_get_clientsession(hass)
    status_client = LoqedStatusClient(websession, entry.data[CONF_IP_ADDRESS])
    coordinator = LoqedDataCoordinator(hass, status_client)
    await coordinator.async_config_entry_first_refresh()

    webhook_id = entry.data[CONF_WEBHOOK_ID]

    webhook_client = LoqedWebhookClient(
        websession, entry.data[CONF_IP_ADDRESS], entry.data[CONF_API_KEY]
    )

    webhook_index = await ensure_webhooks(hass, webhook_id, webhook_client)

    lock_client = LoqedLockClient(
        websession,
        entry.data[CONF_IP_ADDRESS],
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
    )

    entry_config[CONF_WEBHOOK_CLIENT] = webhook_client
    entry_config[CONF_LOCK_CLIENT] = lock_client
    entry_config[CONF_WEBHOOK_INDEX] = webhook_index
    entry_config[CONF_COORDINATOR] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    client: LoqedWebhookClient = hass.data[DOMAIN][CONF_WEBHOOK_CLIENT]

    await client.remove_webhook(hass.data[DOMAIN][CONF_WEBHOOK_INDEX])

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN] = None

    return unload_ok


class LoqedDataCoordinator(DataUpdateCoordinator):
    """
    Data update coordinator for the loqed platform
    """

    def __init__(
        self,
        hass: HomeAssistant,
        status_client: LoqedStatusClient,
    ) -> None:
        super().__init__(hass, _LOGGER, name="Loqed sensors")
        self.status_client = status_client

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                return await self.status_client.get_lock_status()
        except LoqedException as err:
            raise ConfigEntryAuthFailed from err
