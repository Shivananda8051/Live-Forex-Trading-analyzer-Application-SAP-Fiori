"""
WebSocket consumers for real-time market data streaming.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class MarketConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for a specific currency pair.
    Clients connect to ws://localhost:8000/ws/pair/<symbol>/
    and receive live ticks + analysis updates.
    """

    async def connect(self):
        self.symbol = self.scope["url_route"]["kwargs"]["symbol"].upper()
        self.group_name = f"pair_{self.symbol.lower()}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WebSocket connected: %s", self.group_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WebSocket disconnected: %s", self.group_name)

    async def receive(self, text_data):
        """Handle messages from the client (e.g., subscribe to additional data)."""
        try:
            data = json.loads(text_data)
            # Client can request specific data
            if data.get("action") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def market_update(self, event):
        """Push market data update to the client."""
        await self.send(text_data=json.dumps(event["data"], default=str))

    async def alert_message(self, event):
        """Push alert to the client."""
        await self.send(text_data=json.dumps(event["data"], default=str))


class OverviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the market overview.
    Clients connect to ws://localhost:8000/ws/overview/
    and receive ticks for ALL pairs.
    """

    async def connect(self):
        self.group_name = "market_overview"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def market_update(self, event):
        await self.send(text_data=json.dumps(event["data"], default=str))


class AlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for alerts/notifications.
    Clients connect to ws://localhost:8000/ws/alerts/
    """

    async def connect(self):
        self.group_name = "alerts"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def alert_message(self, event):
        await self.send(text_data=json.dumps(event["data"], default=str))
