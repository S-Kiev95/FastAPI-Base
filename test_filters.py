"""
Quick test script to verify the filtering system works correctly.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def create_test_users():
    """Create some test users"""
    users = [
        {
            "provider": "google",
            "provider_user_id": "filter_test_1",
            "email": "alice@gmail.com",
            "name": "Alice Gmail",
            "is_active": True
        },
        {
            "provider": "google",
            "provider_user_id": "filter_test_2",
            "email": "bob@yahoo.com",
            "name": "Bob Yahoo",
            "is_active": True
        },
        {
            "provider": "github",
            "provider_user_id": "filter_test_3",
            "email": "charlie@gmail.com",
            "name": "Charlie Gmail",
            "is_active": False
        },
        {
            "provider": "google",
            "provider_user_id": "filter_test_4",
            "email": "david@hotmail.com",
            "name": "David Hotmail",
            "is_active": True
        }
    ]

    print("\n=== Creating test users ===")
    created = []
    for user_data in users:
        try:
            response = requests.post(f"{BASE_URL}/users/", json=user_data)
            if response.status_code == 201:
                user = response.json()
                created.append(user)
                print(f"[OK] Created: {user['name']} ({user['email']})")
            else:
                print(f"[FAIL] Failed to create {user_data['name']}: {response.text}")
        except Exception as e:
            print(f"[ERROR] Error creating {user_data['name']}: {e}")

    # If no users were created (they might already exist), fetch existing ones
    if not created:
        print("\n  All test users already exist. Fetching existing users...")
        try:
            response = requests.get(f"{BASE_URL}/users/")
            if response.status_code == 200:
                return response.json()
        except:
            pass

    return created

def test_basic_filter():
    """Test basic filtering"""
    print("\n=== Test 1: Filter Gmail users ===")
    filter_data = {
        "conditions": [
            {"field": "email", "operator": "icontains", "value": "gmail"}
        ]
    }

    response = requests.post(f"{BASE_URL}/users/filter", json=filter_data)
    if response.status_code == 200:
        users = response.json()
        print(f"[OK] Found {len(users)} Gmail users:")
        for user in users:
            print(f"  - {user['name']} ({user['email']})")
    else:
        print(f"[FAIL] Failed: {response.text}")

def test_multiple_conditions():
    """Test multiple conditions with AND"""
    print("\n=== Test 2: Filter active Gmail users ===")
    filter_data = {
        "conditions": [
            {"field": "email", "operator": "icontains", "value": "gmail"},
            {"field": "is_active", "operator": "eq", "value": True}
        ],
        "operator": "and"
    }

    response = requests.post(f"{BASE_URL}/users/filter", json=filter_data)
    if response.status_code == 200:
        users = response.json()
        print(f"[OK] Found {len(users)} active Gmail users:")
        for user in users:
            print(f"  - {user['name']} ({user['email']}) - Active: {user['is_active']}")
    else:
        print(f"[FAIL] Failed: {response.text}")

def test_or_operator():
    """Test OR operator"""
    print("\n=== Test 3: Filter Gmail OR Yahoo users ===")
    filter_data = {
        "conditions": [
            {"field": "email", "operator": "icontains", "value": "gmail"},
            {"field": "email", "operator": "icontains", "value": "yahoo"}
        ],
        "operator": "or"
    }

    response = requests.post(f"{BASE_URL}/users/filter", json=filter_data)
    if response.status_code == 200:
        users = response.json()
        print(f"[OK] Found {len(users)} Gmail or Yahoo users:")
        for user in users:
            print(f"  - {user['name']} ({user['email']})")
    else:
        print(f"[FAIL] Failed: {response.text}")

def test_pagination():
    """Test pagination"""
    print("\n=== Test 4: Paginated results ===")
    filter_data = {
        "conditions": [
            {"field": "is_active", "operator": "eq", "value": True}
        ],
        "order_by": "created_at",
        "order_direction": "desc",
        "limit": 2,
        "offset": 0
    }

    response = requests.post(f"{BASE_URL}/users/filter/paginated", json=filter_data)
    if response.status_code == 200:
        result = response.json()
        print(f"[OK] Total active users: {result['total']}")
        print(f"  Showing: {len(result['data'])} users")
        print(f"  Limit: {result['limit']}, Offset: {result['offset']}")
        print(f"  Has more: {result['has_more']}")
        for user in result['data']:
            print(f"  - {user['name']} ({user['email']})")
    else:
        print(f"[FAIL] Failed: {response.text}")

def test_ordering():
    """Test ordering"""
    print("\n=== Test 5: Ordered by name (ascending) ===")
    filter_data = {
        "order_by": "name",
        "order_direction": "asc",
        "limit": 10
    }

    response = requests.post(f"{BASE_URL}/users/filter", json=filter_data)
    if response.status_code == 200:
        users = response.json()
        print(f"[OK] Found {len(users)} users (ordered by name):")
        for user in users:
            print(f"  - {user['name']}")
    else:
        print(f"[FAIL] Failed: {response.text}")

def test_provider_filter():
    """Test filtering by provider"""
    print("\n=== Test 6: Filter Google provider users ===")
    filter_data = {
        "conditions": [
            {"field": "provider", "operator": "eq", "value": "google"}
        ]
    }

    response = requests.post(f"{BASE_URL}/users/filter", json=filter_data)
    if response.status_code == 200:
        users = response.json()
        print(f"[OK] Found {len(users)} Google users:")
        for user in users:
            print(f"  - {user['name']} (Provider: {user['provider']})")
    else:
        print(f"[FAIL] Failed: {response.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("FILTER SYSTEM TEST")
    print("=" * 60)

    # Create test users
    created_users = create_test_users()

    if not created_users:
        print("\n[FAIL] No test users created. Exiting.")
        exit(1)

    # Run tests
    test_basic_filter()
    test_multiple_conditions()
    test_or_operator()
    test_pagination()
    test_ordering()
    test_provider_filter()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
