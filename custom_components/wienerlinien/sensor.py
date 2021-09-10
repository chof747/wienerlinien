"""
A integration that allows you to get information about next departure from specified stop.
For more details about this component, please refer to the documentation at
https://github.com/custom-components/wienerlinien
"""
import logging
from datetime import timedelta
from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import Entity

from custom_components.wienerlinien.const import DEPARTURES
from custom_components.wienerlinien.api import WienerlinienAPI

CONF_STOPS = "stops"
CONF_APIKEY = "apikey"
CONF_FIRST_NEXT = "firstnext"
CONF_NAME_DISPLAY = "displayname"

SCAN_INTERVAL = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_APIKEY): cv.string,
        vol.Optional(CONF_STOPS, default=None): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_FIRST_NEXT, default="first"): cv.string,
        vol.Optional(CONF_NAME_DISPLAY, default="simple"): cv.string,
    }
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup."""
    stops = config.get(CONF_STOPS)
    firstnext = config.get(CONF_FIRST_NEXT)
    displayname = config.get(CONF_NAME_DISPLAY)

    dev = []
    for stopid in stops:
        api = WienerlinienAPI(async_create_clientsession(hass), hass.loop, stopid)
        data = await api.get_json()
        try:
            i = 0
            for monitor in data["data"]["monitors"]:
                name = f'{monitor["lines"][0]["name"]} {monitor["locationStop"]["properties"]["title"]}'
                dev.append(
                    WienerlinienSensor(api, name, i, firstnext, displayname, hass.bus)
                )
                i = i + 1

        except Exception:
            raise PlatformNotReady()

    add_devices_callback(dev, True)


class WienerlinienSensor(Entity):
    """WienerlinienSensor."""

    def __init__(self, api, name, monitor, firstnext, displayname, eventbus):
        """Initialize."""
        self.api = api
        self.eventbus = eventbus
        self.firstnext = firstnext
        self.displayname = displayname
        self._name = name
        self._state = None
        self._icon = "train-car"
        self._direction = ""
        self.monitor = monitor

        self.attributes = {}

    async def async_update(self):
        """Update data."""
        try:
            data = await self.api.get_json()
            _LOGGER.debug(data)
            if data is None:
                return
            data = data.get("data", {})
        except:
            _LOGGER.debug("Could not get new state")
            return

        if data is None:
            return
        try:
            line = data["monitors"][self.monitor]["lines"][0]
            departure = line["departures"]["departure"][
                DEPARTURES[self.firstnext]["key"]
            ]

            self.setState(departure)
            self.setIcon(line["type"])
            self._direction = line["towards"]
            self.attributes = {
                "destination": line["towards"],
                "platform": line["platform"],
                "direction": line["direction"],
                "line": line["name"],
                "barrierFree": line["barrierFree"],
                "realtimeSupported": line["realtimeSupported"],
                "trafficJam": line["trafficjam"],
                "countdown": departure["departureTime"]["countdown"],
            }

            self.checkEventTriggers()
        except Exception:
            pass

    def setState(self, departure):
        """Get the right time signal depending on the available signals"""
        if "timeReal" in departure["departureTime"]:
            self._state = departure["departureTime"]["timeReal"]
        elif "timePlanned" in departure["departureTime"]:
            self._state = departure["departureTime"]["timePlanned"]
        else:
            self._state = self._state

    def setIcon(self, lineType):
        """Determines the icon type based on the typecode of the vehicle"""
        if "ptBus" in lineType:
            self._icon = "bus"
        elif "ptTram" in lineType:
            self._icon = "tram"
        elif "ptMetro" in lineType:
            self._icon = "subway-variant"
        else:
            self._icon = "train-car"

    def checkEventTriggers(self):
        """Evaluate the state and attribute of the sensor to check if any events need to be fired"""
        self.checkForTrafficJam()
        self.checkForNewArrival()

    def checkForTrafficJam(self):
        """Check if the sensor reports a traffic jam and send a warning"""
        if self.attributes["trafficJam"]:
            self.eventbus.fire(
                "wienerlinien_traffic_jam",
                {
                    "line": self.attributes["line"],
                    "direction": self._direction,
                    "station": self._name,
                    "expected": self._state,
                },
            )
        pass

    def checkForNewArrival(self):
        """Check if the new arrival time has changed and trigger event"""
        pass

    @property
    def name(self):
        """Return name."""
        return DEPARTURES[self.firstnext]["name"][self.displayname].format(
            self._name, self._direction
        )

    @property
    def state(self):
        """Return state."""
        return f"{self._state[:-2]}:{self._state[26:]}"

    @property
    def icon(self):
        """Return icon."""
        return f"mdi:{self._icon}"

    @property
    def device_state_attributes(self):
        """Return attributes."""
        return self.attributes

    @property
    def device_class(self):
        """Return device_class."""
        return "timestamp"
