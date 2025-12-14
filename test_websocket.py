"""
Script simple para probar WebSocket en tiempo real.
Conecta al canal de usuarios y escucha eventos.
"""
import asyncio
import websockets
import json


async def test_websocket():
    """Conectar al WebSocket y escuchar eventos"""
    uri = "ws://localhost:8000/ws/users"

    print(f"Conectando a {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Conectado exitosamente al canal 'users'")
            print("[INFO] Escuchando eventos... (Ctrl+C para salir)")
            print("-" * 60)

            # Enviar ping para probar
            await websocket.send(json.dumps({"type": "ping"}))

            # Escuchar eventos
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Formatear según el tipo de evento
                    if data.get("type") == "pong":
                        print(f"\n[PONG] Servidor respondio: {data.get('message')}")

                    elif data.get("type") == "created":
                        user = data.get("data", {})
                        print(f"\n[CREATED] Nuevo usuario creado:")
                        print(f"  ID: {user.get('id')}")
                        print(f"  Email: {user.get('email')}")
                        print(f"  Nombre: {user.get('name')}")

                    elif data.get("type") == "updated":
                        user = data.get("data", {})
                        print(f"\n[UPDATED] Usuario actualizado:")
                        print(f"  ID: {user.get('id')}")
                        print(f"  Email: {user.get('email')}")
                        print(f"  Nombre: {user.get('name')}")

                    elif data.get("type") == "deleted":
                        user_id = data.get("data", {}).get("id")
                        print(f"\n[DELETED] Usuario eliminado:")
                        print(f"  ID: {user_id}")

                    else:
                        print(f"\n[EVENT] {data}")

                    print("-" * 60)

                except websockets.exceptions.ConnectionClosed:
                    print("\n[ERROR] Conexion cerrada por el servidor")
                    break

    except ConnectionRefusedError:
        print("[ERROR] No se pudo conectar. Asegurate de que el servidor este corriendo.")
    except KeyboardInterrupt:
        print("\n[INFO] Desconectado por el usuario")
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")


async def test_websocket_with_stats():
    """Conectar y pedir estadisticas"""
    uri = "ws://localhost:8000/ws/users"

    print(f"Conectando a {uri} para obtener estadisticas...")

    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Conectado")

            # Pedir estadísticas
            await websocket.send(json.dumps({"type": "get_stats"}))

            # Esperar respuesta
            message = await websocket.recv()
            data = json.loads(message)

            if data.get("type") == "stats":
                stats = data.get("data", {})
                print("\n[STATS] Estadisticas del servidor:")
                print(f"  Canales activos: {stats.get('channels', {})}")
                print(f"  Total conexiones: {stats.get('total_connections', 0)}")
            else:
                print(f"Respuesta: {data}")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("WEBSOCKET TESTER")
    print("=" * 60)
    print("\nOpciones:")
    print("1. Escuchar eventos en tiempo real")
    print("2. Obtener estadisticas del servidor")
    print()

    choice = input("Selecciona opcion (1 o 2): ").strip()

    if choice == "1":
        print("\nIniciando listener...")
        print("Abre otra terminal y ejecuta:")
        print('  curl -X POST "http://localhost:8000/users/" -H "Content-Type: application/json" -d "{\\"provider\\":\\"google\\",\\"provider_user_id\\":\\"test123\\",\\"email\\":\\"test@example.com\\",\\"name\\":\\"Test User\\"}"')
        print("\nPara ver eventos en tiempo real!\n")
        asyncio.run(test_websocket())

    elif choice == "2":
        asyncio.run(test_websocket_with_stats())

    else:
        print("Opcion invalida")
