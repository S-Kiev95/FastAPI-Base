from typing import Dict, List, Set
from fastapi import WebSocket
import json
from datetime import datetime


class ConnectionManager:
    """
    Generic WebSocket connection manager that handles multiple channels.
    Each channel can have multiple connected clients.
    """

    def __init__(self):
        # Structure: {channel_name: {client_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str, client_id: str) -> None:
        """
        Connect a client to a specific channel.

        Args:
            websocket: The WebSocket connection
            channel: Channel name (e.g., "users", "posts", "notifications")
            client_id: Unique identifier for this client
        """
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = {}

        self.active_connections[channel][client_id] = websocket

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "message": f"Connected to channel: {channel}",
                "channel": channel,
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )

        print(f"Client {client_id} connected to channel '{channel}'. Total clients: {len(self.active_connections[channel])}")

    def disconnect(self, channel: str, client_id: str) -> None:
        """
        Disconnect a client from a channel.

        Args:
            channel: Channel name
            client_id: Client identifier
        """
        if channel in self.active_connections:
            if client_id in self.active_connections[channel]:
                del self.active_connections[channel][client_id]
                print(f"Client {client_id} disconnected from channel '{channel}'. Remaining: {len(self.active_connections[channel])}")

                # Clean up empty channels
                if not self.active_connections[channel]:
                    del self.active_connections[channel]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")

    async def broadcast_to_channel(self, channel: str, message: dict, exclude_client: str = None) -> None:
        """
        Broadcast a message to all clients in a specific channel.

        Args:
            channel: Channel name to broadcast to
            message: Message dictionary to send
            exclude_client: Optional client_id to exclude from broadcast
        """
        if channel not in self.active_connections:
            return

        # Add metadata to message
        message["timestamp"] = datetime.utcnow().isoformat()
        message["channel"] = channel

        disconnected_clients = []

        for client_id, websocket in self.active_connections[channel].items():
            # Skip excluded client
            if exclude_client and client_id == exclude_client:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(channel, client_id)

    async def broadcast_to_all_channels(self, message: dict) -> None:
        """
        Broadcast a message to all channels.

        Args:
            message: Message dictionary to send
        """
        for channel in list(self.active_connections.keys()):
            await self.broadcast_to_channel(channel, message.copy())

    def get_channel_clients_count(self, channel: str) -> int:
        """
        Get the number of connected clients in a channel.

        Args:
            channel: Channel name

        Returns:
            Number of connected clients
        """
        if channel in self.active_connections:
            return len(self.active_connections[channel])
        return 0

    def get_all_channels(self) -> List[str]:
        """
        Get list of all active channels.

        Returns:
            List of channel names
        """
        return list(self.active_connections.keys())

    def get_stats(self) -> dict:
        """
        Get statistics about all connections.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_channels": len(self.active_connections),
            "channels": {
                channel: len(clients)
                for channel, clients in self.active_connections.items()
            },
            "total_connections": sum(len(clients) for clients in self.active_connections.values())
        }
