"""
A integration that allows you to get information about next departure from specified stop.
For more details about this component, please refer to the documentation at
https://github.com/custom-components/wienerlinien
"""
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import Entity

from custom_components.wienerlinien.api import WienerlinienAPI
from custom_components.wienerlinien.const import (
    DEPARTURES,
    DOMAIN,
    ICONS_URL,
    ICONS_PATH,
    METRO_LINES,
)

CONF_STOPS = "stops"
CONF_APIKEY = "apikey"
CONF_FIRST_NEXT = "firstnext"
CONF_EV_NEW_ARRIVAL = "newarrival"

SCAN_INTERVAL = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_APIKEY): cv.string,
        vol.Optional(CONF_STOPS, default=None): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_FIRST_NEXT, default="first"): cv.string,
        vol.Optional(CONF_EV_NEW_ARRIVAL, default=True): cv.boolean,
    }
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup."""
    stops = config.get(CONF_STOPS)
    firstnext = config.get(CONF_FIRST_NEXT)
    evNewArrival = config.get(CONF_EV_NEW_ARRIVAL)
    dev = []
    for stopid in stops:
        api = WienerlinienAPI(async_create_clientsession(hass), hass.loop, stopid)
        data = await api.get_json()
        try:
            monIx = 0
            for monitor in data["data"]["monitors"]:
                name = f'{monitor["locationStop"]["properties"]["title"]}'
                dev.append(
                    WienerlinienSensor(
                        api, name, monIx, firstnext, hass.bus, evNewArrival
                    )
                )
                monIx += 1

        except Exception:
            raise PlatformNotReady()
    add_devices_callback(dev, True)

    hass.http.register_static_path(ICONS_URL, hass.config.path(ICONS_PATH), True)


class WienerlinienSensor(Entity):
    """WienerlinienSensor."""

    def __init__(self, api, name, monitor, firstnext, eventbus, evNewArrival=True):
        """Initialize."""
        self.api = api
        self.monitor = monitor
        self.firstnext = firstnext
        self._name = name
        self._state = None
        self._icon = "train-car"
        self._oldstate = None
        self.eventbus = eventbus
        self.evNewArrival = evNewArrival

        self.attributes = {}

    async def async_update(self):
        """Update data."""
        try:
            data = await self.api.get_json()
            _LOGGER.debug(data)
            if data is None:
                return
            data = data.get("data", {})
        except Exception as err:
            _LOGGER.debug("Could not get new state")
            _LOGGER.warn(err)
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
            self.attributes = {
                "destination": line["towards"],
                "platform": line["platform"],
                "direction": line["direction"],
                "name": line["name"],
                "countdown": departure["departureTime"]["countdown"],
            }
            self.checkEventTriggers()
        except Exception as err:
            _LOGGER.warn(err)
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
        if self.evNewArrival:
            self.checkForNewArrival()

    def checkForNewArrival(self):
        """Check if the new arrival time has changed and trigger event"""

        if self._oldstate != self._state:
            self.eventbus.fire(
                f"{DOMAIN}_new_arrival",
                {
                    "sensor": self.name,
                    "line": self.attributes["name"],
                    "destination": self.attributes["destination"],
                    "oldTime": self._oldstate,
                    "newTime": self._state,
                },
            )
            self._oldstate = self._state
        pass

    @property
    def name(self):
        """Return name."""
        return DEPARTURES[self.firstnext]["name"].format(
            self.attributes["name"], self._name
        )

    @property
    def state(self):
        """Return state."""
        if self._state != None:
            return f"{self._state[:-2]}:{self._state[26:]}"
        else:
            return None

    @property
    def entity_picture(self):
        if self.attributes["name"] in METRO_LINES:
            return f"{ICONS_URL}/{self.attributes['name']}.svg"
        else:
            return f"{ICONS_URL}/{self._icon}.svg"

    @property
    def device_state_attributes(self):
        """Return attributes."""
        return self.attributes

    @property
    def device_class(self):
        """Return device_class."""
        return "timestamp"
