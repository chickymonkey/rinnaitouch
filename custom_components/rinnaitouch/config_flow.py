"""Config flow for rinnai-brivis-wifi."""
import logging
import socket
import time

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import AbortFlow

from pyrinnaitouch import RinnaiSystem

from .const import (
    DOMAIN,
    CONF_TEMP_SENSOR,
    DEFAULT_NAME,
)

_LOGGER = logging.getLogger(__name__)

# The N-BW2 broadcasts this to UDP port 50000 about once a second while no
# client is connected to it.
BROADCAST_PORT = 50000
BROADCAST_MAGIC = b"Rinnai_NBW2_Module"
DISCOVERY_SECONDS = 3


def discover_modules(timeout: float = DISCOVERY_SECONDS) -> list:
    """Listen for N-BW2 broadcasts and return the addresses heard, in order."""
    found = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(("", BROADCAST_PORT))
    except OSError as err:
        _LOGGER.debug("Cannot listen for N-BW2 broadcasts: %s", err)
        return found

    with sock:
        end = time.monotonic() + timeout
        while (remaining := end - time.monotonic()) > 0:
            sock.settimeout(remaining)
            try:
                data, addr = sock.recvfrom(1024)
            except OSError:  # includes the timeout
                break
            if data.startswith(BROADCAST_MAGIC) and addr[0] not in found:
                found.append(addr[0])
    _LOGGER.debug("Discovered N-BW2 modules: %s", found)
    return found


def user_schema(host: str = "") -> vol.Schema:
    """Return the setup form, with the host field pre-filled if known."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, description={"suggested_value": host}): str,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(CONF_TEMP_SENSOR): str,
        }
    )


class RinnaiTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rinnai Touch."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            system: RinnaiSystem = RinnaiSystem.get_instance(user_input[CONF_HOST])
            device_id = "rinnaitouch_" + str.replace(user_input[CONF_HOST], ".", "_")
            try:
                await self.hass.async_add_executor_job(system.get_status)
            except AbortFlow:
                return self.async_abort(reason="single_instance_allowed")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
            host = user_input[CONF_HOST]
        else:
            # Pre-fill the first bridge heard broadcasting that isn't set up yet.
            configured = {
                entry.data.get(CONF_HOST) for entry in self._async_current_entries()
            }
            discovered = await self.hass.async_add_executor_job(discover_modules)
            host = next((ip for ip in discovered if ip not in configured), "")

        return self.async_show_form(
            step_id="user", data_schema=user_schema(host), errors=errors
        )
