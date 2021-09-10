import async_timeout
from custom_components.wienerlinien.const import BASE_URL


class WienerlinienAPI:
    """Call API."""

    def __init__(self, session, loop, stopid):
        """Initialize."""
        self.session = session
        self.loop = loop
        self.stopid = stopid

    async def get_json(self):
        """Get json from API endpoint."""
        value = None
        url = BASE_URL.format(self.stopid)
        try:
            async with async_timeout.timeout(10, loop=self.loop):
                response = await self.session.get(url)
                value = await response.json()
        except Exception:
            pass

        return value
