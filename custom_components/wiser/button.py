
from .const import (
    ATTR_TIME_PERIOD,
    DATA,
    DEFAULT_BOOST_TEMP_TIME,
    DOMAIN,
    MANUFACTURER,
    WISER_SERVICES
)
from .helpers import get_device_name, get_unique_id, get_identifier
import asyncio
import voluptuous as vol
from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler


    _LOGGER.debug("Setting up Heating buttons")
    wiser_buttons = [
        WiserBoostAllHeatingButton(data),
        WiserCancelHeatingOverridesButton(data)
    ]

    if data.wiserhub.hotwater:
        _LOGGER.debug("Setting up Hot Water buttons")
        wiser_buttons.extend([
            WiserBoostHotWaterButton(data),
            WiserCancelHotWaterOverridesButton(data),
            WiserOverrideHotWaterButton(data),
        ])

    if data.enable_moments and data.wiserhub.moments:
        _LOGGER.debug("Setting up Moments buttons")
        for moment in data.wiserhub.moments.all:
            wiser_buttons.append(WiserMomentsButton(data, moment.id))

    async_add_entities(wiser_buttons, True)

class WiserButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, name = "Button"):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data = coordinator
        self._name = name
        _LOGGER.debug(f"{self._data.wiserhub.system.name} {self.name} initalise")

    async def async_force_update(self, delay: int = 0):
        _LOGGER.debug(f"Hub update initiated by {self.name}")
        if delay:
            asyncio.sleep(delay)
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self.__last_pressed = dt_util.parse_datetime(state.state)
        await self._data.async_refresh()

    @property
    def unique_id(self):
        """Return unique Id."""
        return get_unique_id(self._data, "button", self._name, 0)

    @property
    def name(self):
        return get_device_name(self._data, 0, self._name)
    
    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
                "name": get_device_name(self._data, 0),
                "identifiers": {(DOMAIN, get_identifier(self._data, 0))},
                "manufacturer": MANUFACTURER,
                "model": self._data.wiserhub.system.product_type,
                "sw_version": self._data.wiserhub.system.firmware_version,
                "via_device": (DOMAIN, self._data.wiserhub.system.name),
            }

class WiserBoostAllHeatingButton(WiserButton):
    def __init__(self, data):
        super().__init__(data, "Boost All Heating")

    async def async_press(self):
        boost_time = self._data.boost_time
        boost_temp = self._data.boost_temp
        await self._data.wiserhub.system.boost_all_rooms(boost_temp, boost_time)
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:fire"


class WiserCancelHeatingOverridesButton(WiserButton):
    def __init__(self, data):
        super().__init__(data, "Cancel All Heating Overrides")

    async def async_press(self):
        await self._data.wiserhub.system.cancel_all_overrides()
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:fire-off"


class WiserBoostHotWaterButton(WiserButton):
    def __init__(self, data):
        super().__init__(data, "Boost Hot Water")

    async def async_press(self):
        boost_time = self._data.hw_boost_time
        await self._data.wiserhub.hotwater.boost(boost_time)
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:water-plus"

class WiserCancelHotWaterOverridesButton(WiserButton):
    def __init__(self, data):
        super().__init__(data, "Cancel Hot Water Overrides")

    async def async_press(self):
        await self._data.wiserhub.hotwater.cancel_overrides()
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:water-off"


class WiserOverrideHotWaterButton(WiserButton):
    def __init__(self, data):
        super().__init__(data, "Toggle Hot Water")

    async def async_press(self):
        await self._data.wiserhub.hotwater.override_state( 
            "Off" if self._data.wiserhub.hotwater.current_state == "On" else "Off"
        )
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:water-boiler"


class WiserMomentsButton(WiserButton):
    def __init__(self, data, moment_id):
        self._moment_id = moment_id
        super().__init__(data, f"Moments {data.wiserhub.moments.get_by_id(moment_id).name}")

    async def async_press(self):
        await self._data.wiserhub.moments.get_by_id(self._moment_id).activate()
        await self.async_force_update()

    @property
    def icon(self):
        return "mdi:home-thermometer"
