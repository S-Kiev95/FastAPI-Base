from typing import Optional
from .manager import ConnectionManager


class ChannelManager:
    """
    Manager for model-specific WebSocket channels.
    Each model gets its own channel for real-time updates.
    """

    def __init__(self, connection_manager: ConnectionManager, channel_name: str):
        """
        Initialize a channel manager for a specific model.

        Args:
            connection_manager: The global ConnectionManager instance
            channel_name: Name of the channel (e.g., "users", "posts")
        """
        self.manager = connection_manager
        self.channel_name = channel_name

    async def broadcast_created(self, data: dict, exclude_client: Optional[str] = None) -> None:
        """
        Broadcast a 'created' event to all clients in this channel.

        Args:
            data: The created object data
            exclude_client: Optional client_id to exclude
        """
        await self.manager.broadcast_to_channel(
            self.channel_name,
            {
                "type": "created",
                "model": self.channel_name,
                "data": data
            },
            exclude_client=exclude_client
        )

    async def broadcast_updated(self, data: dict, exclude_client: Optional[str] = None) -> None:
        """
        Broadcast an 'updated' event to all clients in this channel.

        Args:
            data: The updated object data
            exclude_client: Optional client_id to exclude
        """
        await self.manager.broadcast_to_channel(
            self.channel_name,
            {
                "type": "updated",
                "model": self.channel_name,
                "data": data
            },
            exclude_client=exclude_client
        )

    async def broadcast_deleted(self, object_id: int, exclude_client: Optional[str] = None) -> None:
        """
        Broadcast a 'deleted' event to all clients in this channel.

        Args:
            object_id: ID of the deleted object
            exclude_client: Optional client_id to exclude
        """
        await self.manager.broadcast_to_channel(
            self.channel_name,
            {
                "type": "deleted",
                "model": self.channel_name,
                "data": {"id": object_id}
            },
            exclude_client=exclude_client
        )

    async def broadcast_custom(self, event_type: str, data: dict, exclude_client: Optional[str] = None) -> None:
        """
        Broadcast a custom event to all clients in this channel.

        Args:
            event_type: Custom event type name
            data: Event data
            exclude_client: Optional client_id to exclude
        """
        await self.manager.broadcast_to_channel(
            self.channel_name,
            {
                "type": event_type,
                "model": self.channel_name,
                "data": data
            },
            exclude_client=exclude_client
        )


# Global connection manager instance
connection_manager = ConnectionManager()

# Channel managers for each model
users_channel = ChannelManager(connection_manager, "users")
media_channel = ChannelManager(connection_manager, "media")

# Add more channels for other models as needed:
# posts_channel = ChannelManager(connection_manager, "posts")
# comments_channel = ChannelManager(connection_manager, "comments")
# notifications_channel = ChannelManager(connection_manager, "notifications")
