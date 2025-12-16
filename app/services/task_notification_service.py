"""
Task Notification Service

Listens to Redis Pub/Sub for task notifications from workers
and relays them to connected WebSocket clients.

This bridges the gap between:
- Workers (publish to Redis Pub/Sub)
- WebSocket clients (receive real-time updates)
"""
import asyncio
import json
from typing import Dict, Any
import redis.asyncio as aioredis

from app.config import settings
from app.services.websocket import connection_manager


class TaskNotificationService:
    """
    Service that listens to Redis Pub/Sub channels for task notifications
    and forwards them to WebSocket clients.

    Usage:
        service = TaskNotificationService()
        asyncio.create_task(service.start())
    """

    def __init__(self):
        """Initialize the service"""
        self.redis: aioredis.Redis = None
        self.pubsub = None
        self.running = False
        self.subscribed_channels: set = set()

    async def initialize(self):
        """Initialize Redis connection"""
        if not settings.REDIS_ENABLED:
            print("[TaskNotification] Redis not enabled, service disabled")
            return

        try:
            self.redis = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis.pubsub()
            print("[TaskNotification] Initialized Redis Pub/Sub listener")
        except Exception as e:
            print(f"[TaskNotification] Failed to initialize: {e}")
            raise

    async def subscribe_to_user_tasks(self, user_id: int):
        """
        Subscribe to task notifications for a specific user

        Args:
            user_id: User ID to subscribe to
        """
        if not self.pubsub:
            await self.initialize()

        channel = f"task_notifications:{user_id}"

        if channel not in self.subscribed_channels:
            await self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            print(f"[TaskNotification] Subscribed to {channel}")

    async def subscribe_to_media_tasks(self, media_id: int):
        """
        Subscribe to task notifications for a specific media item

        Args:
            media_id: Media ID to subscribe to
        """
        if not self.pubsub:
            await self.initialize()

        channel = f"task_notifications:{media_id}"

        if channel not in self.subscribed_channels:
            await self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            print(f"[TaskNotification] Subscribed to {channel}")

    async def start(self):
        """
        Start listening to Redis Pub/Sub and relay messages to WebSocket

        This should be run as a background task:
            asyncio.create_task(task_notification_service.start())
        """
        if not settings.REDIS_ENABLED:
            print("[TaskNotification] Service not started (Redis disabled)")
            return

        if not self.pubsub:
            await self.initialize()

        self.running = True
        print("[TaskNotification] Service started, listening for task notifications...")

        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                # Skip subscribe/unsubscribe messages
                if message['type'] not in ['message', 'pmessage']:
                    continue

                await self._handle_notification(message)

        except Exception as e:
            print(f"[TaskNotification] Error in listener loop: {e}")
        finally:
            self.running = False

    async def stop(self):
        """Stop the listener"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        print("[TaskNotification] Service stopped")

    async def _handle_notification(self, message: Dict[str, Any]):
        """
        Handle incoming notification from Redis Pub/Sub

        Args:
            message: Redis Pub/Sub message
        """
        try:
            # Parse channel name
            channel = message['channel']
            data_str = message['data']

            # Parse notification data
            notification = eval(data_str)  # Convert string back to dict

            print(f"[TaskNotification] Received: {notification['event_type']} from {channel}")

            # Determine which WebSocket channel to send to
            event_type = notification.get('event_type')
            user_id = notification.get('user_id')
            media_id = notification.get('media_id')

            # Prepare WebSocket message
            ws_message = {
                "type": "task_notification",
                "event": event_type,
                "job_id": notification.get('job_id'),
                "data": notification.get('data'),
                "timestamp": notification.get('timestamp'),
            }

            # Send to appropriate WebSocket channel
            if media_id:
                # Send to media channel
                await connection_manager.broadcast(
                    {"type": "task_update", **ws_message},
                    channel="media"
                )

            # If user_id is present, we could send to user-specific channel
            # For now, broadcast to media channel since most tasks are media-related

            print(f"[TaskNotification] Forwarded to WebSocket: {event_type}")

        except Exception as e:
            print(f"[TaskNotification] Error handling notification: {e}")


# Global instance
task_notification_service = TaskNotificationService()


# Background task starter
async def start_task_notification_listener():
    """
    Start the task notification listener as a background task

    Call this from main.py on startup:
        asyncio.create_task(start_task_notification_listener())
    """
    try:
        await task_notification_service.start()
    except Exception as e:
        print(f"[TaskNotification] Listener crashed: {e}")
