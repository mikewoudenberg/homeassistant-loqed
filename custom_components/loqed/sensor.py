"""
Loqed sensor entities
"""
from __future__ import annotations

from .loqed import LoqedStatusClient
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, PERCENTAGE, SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import SENSOR_UPDATE
from .const import DOMAIN


SENSORS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        name="Loqed battery status",
        key="battery_percentage",
        device_class=SensorDeviceClass.BATTERY,
        unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    SensorEntityDescription(
        name="Loqed wifi signal strength",
        key="wifi_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        icon="mdi:signal",
    ),
    SensorEntityDescription(
        name="Loqed bluetooth signal strength",
        key="ble_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        icon="mdi:signal",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Loqed sensor."""
    status_client: LoqedStatusClient = hass.data[DOMAIN]["status_client"]
    status = await status_client.get_lock_status("")

    status_dict = vars(status)

    entities = [
        LoqedSensor(entry.data[CONF_MAC], sensor, status_dict[sensor.key])
        for sensor in SENSORS
    ]
    async_add_entities(entities, True)


class LoqedSensor(RestoreEntity, SensorEntity):
    """
    Class representing a LoqedSensor
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, mac_address: str, sensor_description: SensorEntityDescription, state: int
    ) -> None:
        """
        Initializes the loqed sensor
        """
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac_address)},
            name="Loqed instance",
        )
        self.entity_description = sensor_description
        self._attr_unique_id = f"{sensor_description.key}-{mac_address}"
        self._attr_native_value = state
        self._attr_native_unit_of_measurement = sensor_description.unit_of_measurement

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
        key = self.entity_description.key
        if key in message and message["mac_wifi"] in self.unique_id:
            self._attr_native_value = int(message[key])
            self.async_schedule_update_ha_state()
