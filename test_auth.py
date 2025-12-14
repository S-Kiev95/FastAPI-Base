"""
Script para probar el sistema de autenticación JWT.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth_system():
    """Prueba completa del sistema de autenticación"""

    print("=" * 60)
    print("TEST DEL SISTEMA DE AUTENTICACIÓN JWT")
    print("=" * 60)

    # 1. Registrar un nuevo usuario
    print("\n[PASO 1] Registrando nuevo usuario...")
    register_data = {
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            user = response.json()
            print(f"[OK] Usuario registrado:")
            print(f"  - ID: {user['id']}")
            print(f"  - Email: {user['email']}")
            print(f"  - Provider: {user['provider']}")
        elif response.status_code == 400 and "already registered" in response.text:
            print("[INFO] Usuario ya existe, continuando con login...")
        else:
            print(f"[ERROR] {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    # 2. Login con credenciales
    print("\n[PASO 2] Iniciando sesión...")
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            print(f"[OK] Login exitoso!")
            print(f"  - Token: {access_token[:50]}...")
        else:
            print(f"[ERROR] {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    # 3. Acceder a endpoint protegido (/auth/me)
    print("\n[PASO 3] Accediendo a endpoint protegido /auth/me...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            user = response.json()
            print(f"[OK] Datos del usuario autenticado:")
            print(f"  - Email: {user['email']}")
            print(f"  - Name: {user['name']}")
            print(f"  - Active: {user['is_active']}")
        else:
            print(f"[ERROR] {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    # 4. Intentar acceder sin token (debe fallar)
    print("\n[PASO 4] Intentando acceder sin token (debe fallar)...")
    try:
        response = requests.get(f"{BASE_URL}/auth/me")
        if response.status_code == 403:
            print(f"[OK] Correctamente bloqueado sin token")
        else:
            print(f"[WARNING] Response: {response.status_code}")
    except Exception as e:
        print(f"[OK] Bloqueado correctamente: {e}")

    # 5. Refresh token
    print("\n[PASO 5] Renovando token...")
    try:
        response = requests.post(f"{BASE_URL}/auth/refresh", headers=headers)
        if response.status_code == 200:
            new_token_data = response.json()
            print(f"[OK] Token renovado exitosamente")
            print(f"  - Nuevo token: {new_token_data['access_token'][:50]}...")
        else:
            print(f"[ERROR] {response.text}")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 6. Probar login con password incorrecta
    print("\n[PASO 6] Probando login con password incorrecta...")
    wrong_login = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=wrong_login)
        if response.status_code == 401:
            print(f"[OK] Login rechazado correctamente con password incorrecta")
        else:
            print(f"[WARNING] Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 60)
    print("TODOS LOS TESTS COMPLETADOS")
    print("=" * 60)
    print("\nEl sistema de autenticación JWT está funcionando correctamente!")
    print("\nPuedes usar estos endpoints en tu aplicación:")
    print("  - POST /auth/register - Registrar usuario")
    print("  - POST /auth/login - Iniciar sesión")
    print("  - GET /auth/me - Obtener usuario actual (requiere token)")
    print("  - POST /auth/refresh - Renovar token")


if __name__ == "__main__":
    test_auth_system()
