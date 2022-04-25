"""
Lock platform for Loqed
"""
import logging
from typing import Any

from .loqed import LoqedLockClient
from . import SENSOR_UPDATE

from .const import DOMAIN

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.lock import LockEntity, SUPPORT_OPEN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    STATE_JAMMED,
    STATE_LOCKED,
    STATE_LOCKING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNKNOWN,
    STATE_UNLOCKED,
    STATE_UNLOCKING,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

LOCK_UNLOCK_DELAY = 2

LOCK_MESSAGE_STATE_TO_STATUS = {
    "DAY_LOCK": STATE_UNLOCKED,
    "NIGHT_LOCK": STATE_LOCKED,
    "OPEN": STATE_OPEN,
}

GO_TO_STATE_TO_STATUS = {
    "NIGHT_LOCK": STATE_LOCKING,
    "DAY_LOCK": STATE_UNLOCKING,
    "OPEN": STATE_OPENING,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Loqed sensor."""

    entities = [LoqedLock(entry.data[CONF_MAC], hass.data[DOMAIN]["lock_client"])]
    async_add_entities(entities, True)


class LoqedLock(RestoreEntity, LockEntity):
    """
    Class representing a Loqed lock
    """

    _attr_name = "Loqed Lock status"
    _attr_supported_features = SUPPORT_OPEN
    _attr_should_poll = False

    def __init__(self, mac_address: str, client: LoqedLockClient) -> None:
        self._client = client
        self._state = STATE_UNKNOWN
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac_address)},
            name="Loqed instance",
        )
        self._attr_unique_id = f"loqed-lock-{mac_address}"

    @property
    def is_locking(self):
        """Return true if lock is locking."""
        return self._state == STATE_LOCKING

    @property
    def is_unlocking(self):
        """Return true if lock is unlocking."""
        return self._state == STATE_UNLOCKING

    @property
    def is_jammed(self):
        """Return true if lock is jammed."""
        return self._state == STATE_JAMMED

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._state == STATE_LOCKED

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        _LOGGER.info("Locking the lock")
        self._state = STATE_LOCKING
        self.async_write_ha_state()

        await self._client.lock_lock("")

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        _LOGGER.info("Unlocking the lock")
        self._state = STATE_UNLOCKING
        self.async_write_ha_state()

        await self._client.latch_lock("")

    async def async_open(self, **kwargs: Any) -> None:
        """Open the door latch."""
        _LOGGER.info("Opening the lock")
        self._state = STATE_UNLOCKING
        self.async_write_ha_state()
        await self._client.open_lock("")

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SENSOR_UPDATE, self._message_callback)
        )

        if not (state := await self.async_get_last_state()):
            return
        self._state = state.state

    @callback
    def _message_callback(self, message):
        # Process message contents here
        if (
            "requested_state" in message
            and message["requested_state"] in LOCK_MESSAGE_STATE_TO_STATUS
            and message["mac_wifi"] in self.unique_id
        ):
            self._state = LOCK_MESSAGE_STATE_TO_STATUS[message["requested_state"]]
            self.async_schedule_update_ha_state()
        elif (
            "go_to_state" in message
            and message["go_to_state"] in GO_TO_STATE_TO_STATUS
            and message["mac_wifi"] in self.unique_id
        ):
            self._state = GO_TO_STATE_TO_STATUS[message["go_to_state"]]
            self.async_schedule_update_ha_state()
