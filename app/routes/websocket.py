from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import uuid

from app.services.websocket import connection_manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.

    Available channels:
    - users: Real-time user updates (create, update, delete)
    - media: Real-time media file updates (upload, update, delete)
    - Add more channels as you add more models

    Query parameters:
    - client_id: Optional unique identifier for the client.
                 If not provided, a UUID will be generated.

    Usage:
        ws://localhost:8000/ws/users
        ws://localhost:8000/ws/users?client_id=my-unique-id
    """
    # Generate client_id if not provided
    if not client_id:
        client_id = str(uuid.uuid4())

    # Validate channel
    valid_channels = ["users", "media", "tasks"]  # Add more as you create them
    if channel not in valid_channels:
        await websocket.close(code=1008, reason=f"Invalid channel: {channel}")
        return

    # Connect client to channel
    await connection_manager.connect(websocket, channel, client_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            # Handle different message types
            message_type = data.get("type", "message")

            if message_type == "ping":
                # Respond to ping
                await connection_manager.send_personal_message(
                    {"type": "pong", "message": "pong"},
                    websocket
                )
            elif message_type == "get_stats":
                # Send channel statistics
                stats = connection_manager.get_stats()
                await connection_manager.send_personal_message(
                    {"type": "stats", "data": stats},
                    websocket
                )
            else:
                # Echo back any other message (can be customized)
                await connection_manager.send_personal_message(
                    {
                        "type": "echo",
                        "message": "Message received",
                        "original": data
                    },
                    websocket
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(channel, client_id)
        print(f"Client {client_id} disconnected from {channel}")
    except Exception as e:
        print(f"Error in WebSocket connection for {client_id}: {e}")
        connection_manager.disconnect(channel, client_id)


@router.get("/stats")
async def get_websocket_stats():
    """
    Get current WebSocket connection statistics.

    Returns information about:
    - Number of active channels
    - Number of clients per channel
    - Total connections
    """
    return connection_manager.get_stats()
