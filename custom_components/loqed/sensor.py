"""
Loqed sensor entities
"""
from __future__ import annotations
import logging

from .const import DOMAIN
from . import SENSOR_UPDATE

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

ICON = "mdi:battery"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Loqed sensor."""
    entities = [LoqedSensor(entry.data[CONF_MAC])]
    async_add_entities(entities, True)


class LoqedSensor(RestoreEntity, SensorEntity):
    """
    Class representing a LoqedSensor
    """

    _attr_name = "Loqed battery status"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, mac_address: str) -> None:
        """
        Initializes the loqed sensor
        """
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac_address)},
            name="Loqed instance",
        )
        self._attr_unique_id = f"loqed-battery-{mac_address}"

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SENSOR_UPDATE, self._message_callback)
        )

        if not (state := await self.async_get_last_state()):
            return
        self._attr_native_value = state.state

    @callback
    def _message_callback(self, message):
        if "battery_percentage" in message and message["mac_wifi"] in self.unique_id:
            self._attr_native_value = int(message["battery_percentage"])
            self.async_schedule_update_ha_state()
