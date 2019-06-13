"""Alexa HTTP interface."""
import logging

from homeassistant import core
from homeassistant.components.http.view import HomeAssistantView

from .auth import Auth
from .config import Config
from .const import (
    AUTH_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENDPOINT,
    CONF_ENTITY_CONFIG,
    CONF_FILTER
)
from .state_report import async_enable_proactive_mode
from .smart_home import async_handle_message

_LOGGER = logging.getLogger(__name__)
SMART_HOME_HTTP_ENDPOINT = '/api/alexa/smart_home'


async def async_setup(hass, config):
    """Activate Smart Home functionality of Alexa component.

    This is optional, triggered by having a `smart_home:` sub-section in the
    alexa configuration.

    Even if that's disabled, the functionality in this module may still be used
    by the cloud component which will call async_handle_message directly.
    """
    if config.get(CONF_CLIENT_ID) and config.get(CONF_CLIENT_SECRET):
        hass.data[AUTH_KEY] = Auth(hass, config[CONF_CLIENT_ID],
                                   config[CONF_CLIENT_SECRET])

    async_get_access_token = \
        hass.data[AUTH_KEY].async_get_access_token if AUTH_KEY in hass.data \
        else None

    smart_home_config = Config(
        endpoint=config.get(CONF_ENDPOINT),
        async_get_access_token=async_get_access_token,
        should_expose=config[CONF_FILTER],
        entity_config=config.get(CONF_ENTITY_CONFIG),
    )
    hass.http.register_view(SmartHomeView(smart_home_config))

    if AUTH_KEY in hass.data:
        await async_enable_proactive_mode(hass, smart_home_config)


class SmartHomeView(HomeAssistantView):
    """Expose Smart Home v3 payload interface via HTTP POST."""

    url = SMART_HOME_HTTP_ENDPOINT
    name = 'api:alexa:smart_home'

    def __init__(self, smart_home_config):
        """Initialize."""
        self.smart_home_config = smart_home_config

    async def post(self, request):
        """Handle Alexa Smart Home requests.

        The Smart Home API requires the endpoint to be implemented in AWS
        Lambda, which will need to forward the requests to here and pass back
        the response.
        """
        hass = request.app['hass']
        user = request['hass_user']
        message = await request.json()

        _LOGGER.debug("Received Alexa Smart Home request: %s", message)

        response = await async_handle_message(
            hass, self.smart_home_config, message,
            context=core.Context(user_id=user.id)
        )
        _LOGGER.debug("Sending Alexa Smart Home response: %s", response)
        return b'' if response is None else self.json(response)