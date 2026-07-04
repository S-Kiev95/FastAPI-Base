"""
Test de integración del portal de seguros (end-to-end contra el server vivo).

Ejercita el flujo real del portal tal como lo hace el frontend:
register -> login (con org_slug) -> dashboard -> crear/listar/editar/completar
en cada recurso. Cubre los mismatches arreglados (métodos PUT->POST/PATCH,
query params) y el contrato de creación (organization_id inyectado por el
backend, no enviado por el cliente).

Requiere el backend corriendo en BASE_URL (default http://localhost:8000).

Uso:
    uv run python test_seguros_portal.py
    BASE_URL=http://localhost:8000 uv run python test_seguros_portal.py

Sale con código 0 si todo pasa, 1 si hay algún fallo.
"""
import os
import sys
import time
from datetime import date, timedelta

import requests

BASE = os.getenv("BASE_URL", "http://localhost:8000")
TIMEOUT = 10

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name}  {detail}")


def main():
    s = requests.Session()
    suffix = str(int(time.time()))
    email = f"test_portal_{suffix}@seguros.test"
    password = "TestPortal123!"

    print(f"== Portal de seguros — test de integración ({BASE}) ==")

    # --- Register ---
    r = s.post(f"{BASE}/auth/register", json={
        "email": email, "password": password,
        "name": "Test Portal", "organization_name": f"Test Org {suffix}",
    }, timeout=TIMEOUT)
    check("register -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # --- Login (debe devolver org_slug) ---
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    check("login -> 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json() if r.ok else {}
    token = data.get("access_token")
    org_slug = data.get("org_slug")
    check("login devuelve access_token", bool(token))
    check("login devuelve org_slug", bool(org_slug), f"org_slug={org_slug!r}")
    if not token or not org_slug:
        return _finish()

    s.headers.update({"Authorization": f"Bearer {token}"})
    api = f"{BASE}/api/orgs/{org_slug}/seguros"

    # user id (para mensajes)
    me = s.get(f"{BASE}/auth/me", timeout=TIMEOUT)
    user_id = me.json().get("id") if me.ok else None

    # --- Dashboard ---
    r = s.get(f"{api}/dashboard", timeout=TIMEOUT)  # sigue redirect trailing slash
    check("GET dashboard -> 200", r.status_code == 200, f"got {r.status_code}")
    if r.ok:
        check("dashboard tiene KPIs", "total_clientes" in r.json())

    # --- Crear aseguradora (sin organization_id, como el frontend) ---
    r = s.post(f"{api}/aseguradoras", json={"nombre": f"Aseg Test {suffix}"}, timeout=TIMEOUT)
    check("POST aseguradora sin org_id -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    insurer_id = r.json().get("id") if r.ok else None

    # --- Crear cliente ---
    r = s.post(f"{api}/clientes", json={"nombre": "Juan", "apellido": "Test"}, timeout=TIMEOUT)
    check("POST cliente sin org_id -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    client_id = r.json().get("id") if r.ok else None

    # --- Editar cliente (updateClient: PATCH) ---
    if client_id:
        r = s.patch(f"{api}/clientes/{client_id}", json={"telefono": "099 123 456"}, timeout=TIMEOUT)
        check("PATCH cliente -> 200", r.status_code == 200, f"got {r.status_code}")

    # --- Buscar cliente (searchClients: ?q=) ---
    r = s.get(f"{api}/clientes", params={"q": "Juan"}, timeout=TIMEOUT)
    check("GET clientes?q= -> 200", r.status_code == 200, f"got {r.status_code}")
    check("búsqueda encuentra al cliente", any(c.get("nombre") == "Juan" for c in (r.json() if r.ok else [])))

    # --- Crear vehículo ---
    if client_id:
        r = s.post(f"{api}/vehiculos", json={
            "cliente_id": client_id, "marca": "Toyota", "matricula": f"TST{suffix[-4:]}",
        }, timeout=TIMEOUT)
        check("POST vehiculo -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # --- Crear póliza (vence dentro de 30 días -> por-vencer) ---
    policy_id = None
    if client_id and insurer_id:
        today = date.today()
        r = s.post(f"{api}/polizas", json={
            "cliente_id": client_id, "aseguradora_id": insurer_id,
            "numero_poliza": f"TST-POL-{suffix}",
            "vigente_desde": (today - timedelta(days=355)).isoformat(),
            "vigente_hasta": (today + timedelta(days=10)).isoformat(),
            "prima_total": 12000, "total_cuotas": 3, "estado": "activa",
        }, timeout=TIMEOUT)
        check("POST poliza -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
        policy_id = r.json().get("id") if r.ok else None

    # --- Próximos vencimientos (getExpiringPolicies: ?days=) ---
    r = s.get(f"{api}/dashboard/proximos-vencimientos", params={"days": 30}, timeout=TIMEOUT)
    check("GET proximos-vencimientos?days= -> 200", r.status_code == 200, f"got {r.status_code}")
    if r.ok and policy_id:
        check("la póliza creada aparece en por-vencer",
              any(p.get("id") == policy_id for p in r.json()))

    # --- Cuotas de la póliza (generadas automáticamente) ---
    if policy_id:
        r = s.get(f"{api}/polizas/{policy_id}/cuotas", timeout=TIMEOUT)
        check("GET poliza/cuotas -> 200", r.status_code == 200, f"got {r.status_code}")

    # --- Crear siniestro ---
    if policy_id and insurer_id:
        r = s.post(f"{api}/siniestros", json={
            "poliza_id": policy_id, "aseguradora_id": insurer_id,
            "numero_siniestro": f"TST-SIN-{suffix}", "descripcion": "Test",
        }, timeout=TIMEOUT)
        check("POST siniestro -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # --- Crear tarea (creado_por inyectado por el backend) ---
    r = s.post(f"{api}/tareas", json={"titulo": "Tarea de prueba"}, timeout=TIMEOUT)
    check("POST tarea sin creado_por -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    task_id = r.json().get("id") if r.ok else None

    # --- Completar tarea (completeTask: POST) ---
    if task_id:
        r = s.post(f"{api}/tareas/{task_id}/completar", timeout=TIMEOUT)
        check("POST tarea/completar -> 200", r.status_code == 200, f"got {r.status_code}")

    # --- Crear taller ---
    r = s.post(f"{api}/talleres", json={"nombre": f"Taller {suffix}", "departamento": "Montevideo"}, timeout=TIMEOUT)
    check("POST taller -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # --- Mensaje (a sí mismo) + marcar leído (markRead: POST) ---
    if user_id:
        r = s.post(f"{api}/mensajes", json={
            "destinatario_id": user_id, "asunto": "Hola", "contenido": "Mensaje de prueba",
        }, timeout=TIMEOUT)
        check("POST mensaje -> 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
        msg_id = r.json().get("id") if r.ok else None
        if msg_id:
            r = s.post(f"{api}/mensajes/{msg_id}/leer", timeout=TIMEOUT)
            check("POST mensaje/leer -> 200", r.status_code == 200, f"got {r.status_code}")

    # --- Listados de cada recurso ---
    for path in ["clientes", "vehiculos", "aseguradoras", "polizas", "cuotas",
                 "siniestros", "talleres", "tareas"]:
        r = s.get(f"{api}/{path}", timeout=TIMEOUT)
        check(f"GET {path} -> 200", r.status_code == 200, f"got {r.status_code}")

    return _finish()


def _finish():
    print(f"\n== Resultado: {_passed} PASS, {_failed} FAIL ==")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.ConnectionError:
        print(f"[ERROR] No se pudo conectar a {BASE}. ¿Está el backend corriendo?")
        sys.exit(2)
