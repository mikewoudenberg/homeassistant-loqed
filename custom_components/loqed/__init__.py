"""The Loqed integration."""
from __future__ import annotations
import json
import logging

from aiohttp import ClientTimeout

from .loqed import (
    WEBHOOK_ALL_EVENTS_FLAG,
    LoqedLockClient,
    LoqedStatusClient,
    LoqedWebhookClient,
)
from aiohttp.web import Request

from homeassistant.helpers.network import get_url
from homeassistant.helpers.dispatcher import async_dispatcher_send
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.LOCK]
_LOGGER = logging.getLogger(__name__)
SENSOR_UPDATE = f"{DOMAIN}_sensor_update"


async def handle_webhook(hass: HomeAssistant, _: str, request: Request):
    """
    Handles incoming Loqed messages
    """
    _LOGGER.debug("Received request %s", request.headers)

    timestamp = request.headers.get("timestamp", "0")
    message_hash = request.headers.get("hash", "")

    body = await request.text()
    client: LoqedWebhookClient = hass.data[DOMAIN]["client"]

    valid = client.validate_message(body, int(timestamp), message_hash, True)
    if not valid:
        _LOGGER.debug("Received invalid message: %s", body)
        return

    message = json.loads(body)
    async_dispatcher_send(hass, SENSOR_UPDATE, message)


async def ensure_webhooks(
    hass: HomeAssistant, webhook_id: str, webhook_client: LoqedWebhookClient
) -> int:
    """
    Ensures the existence of the webhooks on both sides
    """

    webhook.async_register(hass, DOMAIN, "Loqed", webhook_id, handle_webhook)
    webhook_url = webhook.async_generate_url(hass, webhook_id)
    _LOGGER.info("Webhook URL: %s", webhook_url)

    webhooks = await webhook_client.get_all_webhooks("")
    webhook_index = next((x["id"] for x in webhooks if x["url"] == webhook_url), None)

    if not webhook_index:
        await webhook_client.setup_webhook("", webhook_url, WEBHOOK_ALL_EVENTS_FLAG)
        webhooks = await webhook_client.get_all_webhooks("")
        webhook_index = next(x["id"] for x in webhooks if x["url"] == webhook_url)

        _LOGGER.info("Webhook got index %s", webhook_index)

    return int(webhook_index)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loqed from a config entry."""
    entry_config = {}

    _LOGGER.debug("Current domain: %s", hass.data.get(DOMAIN, ""))
    hass.data.setdefault(DOMAIN, entry_config)

    websession = async_get_clientsession(hass)
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

    status_client = LoqedStatusClient(websession, entry.data[CONF_IP_ADDRESS])

    entry_config["client"] = webhook_client
    entry_config["lock_client"] = lock_client
    entry_config["webhook_id"] = webhook_index
    entry_config["status_client"] = status_client

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    client: LoqedWebhookClient = hass.data[DOMAIN]["client"]

    await client.remove_webhook("", hass.data[DOMAIN]["webhook_id"])

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN] = None

    return unload_ok