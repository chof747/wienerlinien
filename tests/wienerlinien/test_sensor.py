import logging
from types import SimpleNamespace
from pytest_homeassistant_custom_component.common import AsyncMock
from pytest_homeassistant_custom_component.plugins import MagicMock
from custom_components.wienerlinien.sensor import WienerlinienSensor
from custom_components.wienerlinien.api import WienerlinienAPI
import custom_components.wienerlinien.sensor as sensor_module


from .fixtures import stop_response, stopCallStub


async def test_async_update_failed(hass):
    wiener_linien_api = MagicMock()
    wiener_linien_api.get_json = AsyncMock(return_value=None)

    sensor = WienerlinienSensor(wiener_linien_api, "test", 0, False, hass.bus)
    await sensor.async_update()

    assert sensor.state == None
    pass


async def test_async_update_ok(stopCallStub, hass):
    api = WienerlinienAPI(stopCallStub, None, "651")
    sensor = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor.async_update()

    time = "2021-09-21T19:03:58.000+0200"
    exp = f"{time[:-2]}:{time[26:]}"

    assert sensor.state == exp


async def test_async_update_allows_departure_without_vehicle(stopCallStub, hass):
    api = WienerlinienAPI(stopCallStub, None, "651")
    sensor = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor.async_update()

    assert sensor.state == "2021-09-21T19:03:58.000+02:00"
    assert sensor.attributes["cooling"] is False
    assert sensor.attributes["name"] == "12A"


_LOGGER = logging.getLogger(__name__)


async def test_seticon(stopCallStub, hass):
    api = WienerlinienAPI(stopCallStub, None, "651")
    sensor = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor.async_update()
    assert sensor.entity_picture == "/wienerlinien/icons/bus.svg"

    api = WienerlinienAPI(stopCallStub, None, "4939")
    sensor = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor.async_update()
    assert sensor.entity_picture == "/wienerlinien/icons/U3.svg"

    api = WienerlinienAPI(stopCallStub, None, "3435")
    sensor = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor.async_update()
    assert sensor.entity_picture == "/wienerlinien/icons/tram.svg"


async def test_alternate_monitors_on_sensor(stopCallStub, hass):
    api = WienerlinienAPI(stopCallStub, None, "3435")
    sensor1 = WienerlinienSensor(api, "test_0", 0, "first", hass.bus)
    await sensor1.async_update()
    sensor2 = WienerlinienSensor(api, "test_0", 1, "first", hass.bus)
    await sensor2.async_update()

    assert sensor1.name == f"(11) test_0 first departure"
    assert sensor2.name == f"(6) test_0 first departure"
    assert sensor1.attributes["name"] == "11"
    assert sensor2.attributes["name"] == "6"


async def test_async_setup_platform_uses_new_static_path_api(hass, monkeypatch):
    class StaticPathConfigStub:
        def __init__(self, url_path, path, cache_headers=True):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    api = MagicMock()
    api.get_json = AsyncMock(
        return_value={
            "data": {
                "monitors": [{"locationStop": {"properties": {"title": "Test Stop"}}}]
            }
        }
    )
    monkeypatch.setattr(sensor_module, "WienerlinienAPI", MagicMock(return_value=api))
    monkeypatch.setattr(sensor_module, "async_create_clientsession", MagicMock())
    monkeypatch.setattr(sensor_module, "StaticPathConfig", StaticPathConfigStub)

    http = SimpleNamespace(async_register_static_paths=AsyncMock())
    hass.http = http
    add_devices_callback = MagicMock()

    await sensor_module.async_setup_platform(
        hass,
        {
            sensor_module.CONF_STOPS: ["651"],
            sensor_module.CONF_FIRST_NEXT: "first",
            sensor_module.CONF_EV_NEW_ARRIVAL: True,
        },
        add_devices_callback,
    )

    add_devices_callback.assert_called_once()
    http.async_register_static_paths.assert_awaited_once()
    [config] = http.async_register_static_paths.await_args.args[0]
    assert config.url_path == sensor_module.ICONS_URL
    assert config.path == hass.config.path(sensor_module.ICONS_PATH)
    assert config.cache_headers is True


async def test_async_setup_platform_falls_back_to_legacy_static_path_api(
    hass, monkeypatch
):
    api = MagicMock()
    api.get_json = AsyncMock(
        return_value={
            "data": {
                "monitors": [{"locationStop": {"properties": {"title": "Test Stop"}}}]
            }
        }
    )
    monkeypatch.setattr(sensor_module, "WienerlinienAPI", MagicMock(return_value=api))
    monkeypatch.setattr(sensor_module, "async_create_clientsession", MagicMock())

    http = SimpleNamespace(register_static_path=MagicMock())
    hass.http = http

    await sensor_module.async_setup_platform(
        hass,
        {
            sensor_module.CONF_STOPS: ["651"],
            sensor_module.CONF_FIRST_NEXT: "first",
            sensor_module.CONF_EV_NEW_ARRIVAL: True,
        },
        MagicMock(),
    )

    http.register_static_path.assert_called_once_with(
        sensor_module.ICONS_URL,
        hass.config.path(sensor_module.ICONS_PATH),
        True,
    )
