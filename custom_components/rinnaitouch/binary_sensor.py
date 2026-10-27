"""Binary sensors for heater state and connection"""
# import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME, CONF_HOST

from pyrinnaitouch import RinnaiSystem, RinnaiSystemMode, RinnaiSystemStatus
from .const import DEFAULT_NAME

# _LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):  # pylint: disable=unused-argument
    """Set up the binary sensor entities."""
    ip_address = entry.data.get(CONF_HOST)
    name = entry.data.get(CONF_NAME)
    if name == "":
        name = DEFAULT_NAME
    async_add_entities(
        [
            RinnaiConnectedBinarySensorEntity(ip_address, name),
            RinnaiPreheatBinarySensorEntity(ip_address, name),
            RinnaiGasValveBinarySensorEntity(ip_address, name),
            RinnaiCallingHeatBinarySensorEntity(ip_address, name),
            RinnaiFanOperatingBinarySensorEntity(ip_address, name),
            RinnaiTimeSettingSensorEntity(ip_address, name),
        ]
    )
    return True


class RinnaiBinarySensorEntity(BinarySensorEntity):
    """Base class for all binary sensor entities setting up names and system instance."""

    def __init__(self, ip_address, name) -> None:
        self._host = ip_address
        self._system: RinnaiSystem = RinnaiSystem.get_instance(ip_address)
        device_id = (
            str.lower(self.__class__.__name__) + "_" + str.replace(ip_address, ".", "_")
        )

        self._attr_unique_id = device_id
        self._attr_name = name + " Binary Sensor"
        self._attr_device_name = name
        self._system.subscribe_updates(self.system_updated)

    def system_updated(self):
        """After system is updated write the new state to HA."""
        # this very infrequently fails on startup so wrapping in try except
        try:
            self.schedule_update_ha_state()
        except:  # pylint: disable=bare-except
            pass

    @property
    def device_info(self):
        """Return device information about this heater."""
        return {
            # "connections": {(CONNECTION_NETWORK_MAC, self._host)},
            "identifiers": {("rinnai_touch", self._host)},
            "model": "Rinnai Touch Wifi",
            "name": self._attr_device_name,
            "manufacturer": "Rinnai/Brivis",
        }

    @property
    def name(self) -> str:
        """Name of the entity."""
        return self._attr_name

    @property
    def is_on(self) -> bool:
        return False


class RinnaiHeaterStateBinarySensorEntity(RinnaiBinarySensorEntity):
    """Binary sensor reflecting a unit status flag during heater operation."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_status_attr = None

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        if not self.available:
            return "mdi:eye"
        if self.is_on:
            return "mdi:eye-check"
        return "mdi:eye-remove"

    @property
    def is_on(self):
        """If the sensor is currently on or off."""
        state: RinnaiSystemStatus = self._system.get_stored_status()
        if self.available:
            return getattr(state.unit_status, self._attr_status_attr, False)
        return False

    @property
    def available(self):
        return self._system.get_stored_status().mode == RinnaiSystemMode.HEATING


class RinnaiPreheatBinarySensorEntity(RinnaiHeaterStateBinarySensorEntity):
    """Binary sensor for preheating on/off during heater operation."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_name = name + " Preheating Sensor"
        self._attr_status_attr = "preheating"

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        return "mdi:fire-alert"


class RinnaiGasValveBinarySensorEntity(RinnaiHeaterStateBinarySensorEntity):
    """Binary sensor for gas valve active during heater operation."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_name = name + " Gas Valve Active Sensor"
        self._attr_status_attr = "gas_valve_active"

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        return "mdi:gas-burner"


class RinnaiCallingHeatBinarySensorEntity(RinnaiHeaterStateBinarySensorEntity):
    """Binary sensor for calling for heat during heater operation."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_name = name + " Calling Heat Sensor"
        self._attr_status_attr = "calling_for_heat"

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        return "mdi:thermometer-alert"


class RinnaiFanOperatingBinarySensorEntity(RinnaiHeaterStateBinarySensorEntity):
    """Binary sensor for the fan operating."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_name = name + " Fan Active Sensor"
        self._attr_status_attr = "fan_operating"

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        return "mdi:fan-alert"


class RinnaiTimeSettingSensorEntity(RinnaiBinarySensorEntity):
    """Binary sensor for signaling the system is in time setting mode."""

    def __init__(self, ip_address, name):
        super().__init__(ip_address, name)
        self._attr_name = name + " Time Setting Sensor"

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        if self.is_on:
            return "mdi:clock-alert-outline"
        return "mdi:clock-outline"

    @property
    def is_on(self):
        """If the sensor is currently on or off."""
        state: RinnaiSystemStatus = self._system.get_stored_status()
        if self.available:
            return state.is_timesetting
        return False

    @property
    def available(self):
        """If the sensor is currently available."""
        return not self._system.get_stored_status().has_fault


class RinnaiConnectedBinarySensorEntity(RinnaiBinarySensorEntity):
    """Binary sensor for Rinnai connection state."""

    def __init__(self, ip_address, name) -> None:
        super().__init__(ip_address, name)
        self._attr_name = name + " Connected Sensor"
        self._attr_unique_id = "connected_" + str.replace(ip_address, ".", "_")
        self._connected = None

        # Subscribe to connection state changes
        self._system.register_socket_state_handler(self._connection_state_handler)

    def _connection_state_handler(self, state):
        """Handle connection state updates from pyrinnaitouch."""
        try:
            self._connected = getattr(state, "name", None) == "CONNECTED"
            self.schedule_update_ha_state()
        except Exception:  # pylint: disable=broad-except
            pass

    @property
    def is_on(self) -> bool:
        """Return True if connected, False otherwise."""
        return self._connected

    @property
    def available(self) -> bool:
        """Sensor is always available."""
        return True

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        if self.is_on:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"
