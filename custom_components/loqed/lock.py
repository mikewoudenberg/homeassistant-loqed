"""
Lock platform for Loqed
"""
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LoqedDataCoordinator
from .const import DOMAIN
from .loqed import LoqedLockClient

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
    coordinator: LoqedDataCoordinator = hass.data[DOMAIN]["coordinator"]

    entities = [
        LoqedLock(entry.data[CONF_MAC], hass.data[DOMAIN]["lock_client"], coordinator)
    ]
    async_add_entities(entities)


class LoqedLock(CoordinatorEntity[LoqedDataCoordinator], LockEntity):
    """
    Class representing a Loqed lock
    """

    _attr_name = "Loqed Lock status"
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(
        self,
        mac_address: str,
        client: LoqedLockClient,
        coordinator: LoqedDataCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac_address)},
            name="Loqed instance",
        )
        self._state = STATE_UNKNOWN
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
        self._state = STATE_LOCKING
        self.async_write_ha_state()

        await self._client.lock_lock("")

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        self._state = STATE_UNLOCKING
        self.async_write_ha_state()

        await self._client.latch_lock("")

    async def async_open(self, **kwargs: Any) -> None:
        """Open the door latch."""
        self._state = STATE_UNLOCKING
        self.async_write_ha_state()
        await self._client.open_lock("")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data

        if (
            "requested_state" in data
            and data["requested_state"] in LOCK_MESSAGE_STATE_TO_STATUS
        ):
            self._state = LOCK_MESSAGE_STATE_TO_STATUS[data["requested_state"]]
            self.async_schedule_update_ha_state()
        elif "go_to_state" in data and data["go_to_state"] in GO_TO_STATE_TO_STATUS:
            self._state = GO_TO_STATE_TO_STATUS[data["go_to_state"]]
            self.async_schedule_update_ha_state()
        elif (
            "bolt_state" in data
            and data["bolt_state"].upper() in LOCK_MESSAGE_STATE_TO_STATUS
        ):
            self._state = LOCK_MESSAGE_STATE_TO_STATUS[data["bolt_state"].upper()]
            self.async_schedule_update_ha_state()
