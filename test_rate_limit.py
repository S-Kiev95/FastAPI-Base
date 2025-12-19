"""
Script to test rate limiting

This script makes multiple requests to test rate limit behavior.
"""
import asyncio
import httpx
import time


async def test_rate_limit():
    """Test rate limiting by making rapid requests"""

    base_url = "http://localhost:8001"

    async with httpx.AsyncClient() as client:
        print("Testing rate limiting...")
        print("=" * 60)

        # Test 1: Make requests within limit
        print("\n1. Testing requests within limit (50 in 60s)...")
        success_count = 0
        for i in range(10):
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    success_count += 1
                    headers = response.headers
                    print(f"  Request {i+1}: ✓ OK")
                    print(f"    X-RateLimit-Limit: {headers.get('X-RateLimit-Limit')}")
                    print(f"    X-RateLimit-Remaining: {headers.get('X-RateLimit-Remaining')}")
            except Exception as e:
                print(f"  Request {i+1}: ✗ Error: {e}")

        print(f"\n  Result: {success_count}/10 requests succeeded")

        # Test 2: Rapidly exceed limit
        print("\n2. Testing rate limit exceeded (100+ requests)...")
        success_count = 0
        rate_limited_count = 0

        for i in range(110):
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited_count += 1
                    if rate_limited_count == 1:
                        # Print first rate limit response
                        data = response.json()
                        print(f"\n  First rate limit at request {i+1}:")
                        print(f"    Status: 429 Too Many Requests")
                        print(f"    Message: {data.get('message')}")
                        print(f"    Retry-After: {data.get('retry_after')}s")
                        print(f"    Current Usage: {data.get('current_usage')}/{data.get('limit')}")
            except Exception as e:
                print(f"  Request {i+1}: ✗ Error: {e}")

        print(f"\n  Result:")
        print(f"    Succeeded: {success_count}")
        print(f"    Rate Limited: {rate_limited_count}")
        print(f"    Total: {success_count + rate_limited_count}")

        # Test 3: Endpoint-specific limits
        print("\n3. Testing endpoint-specific limits (/tasks/media/process)...")
        print("  Limit: 50 requests per minute")

        for i in range(55):
            try:
                response = await client.post(
                    f"{base_url}/tasks/media/process",
                    json={
                        "media_id": 1,
                        "file_path": "/test/image.jpg"
                    }
                )
                if response.status_code == 429:
                    data = response.json()
                    print(f"\n  Rate limited at request {i+1}:")
                    print(f"    Limit: {data.get('limit')} requests")
                    print(f"    Current usage: {data.get('current_usage')}")
                    break
            except Exception as e:
                if i < 3:  # Only print first few errors
                    print(f"  Request {i+1}: {e}")

        print("\n" + "=" * 60)
        print("Rate limiting test completed!")


async def test_rate_limit_headers():
    """Test rate limit headers"""
    base_url = "http://localhost:8001"

    async with httpx.AsyncClient() as client:
        print("\nTesting Rate Limit Headers...")
        print("=" * 60)

        response = await client.get(f"{base_url}/health")

        print("Response Headers:")
        print(f"  X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit', 'N/A')}")
        print(f"  X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining', 'N/A')}")
        print(f"  X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset', 'N/A')}")

        if response.status_code == 429:
            print(f"  Retry-After: {response.headers.get('Retry-After', 'N/A')}")

        print("=" * 60)


if __name__ == "__main__":
    print("\n🚀 Rate Limiting Test Script")
    print("Make sure the FastAPI server is running on http://localhost:8001\n")

    try:
        asyncio.run(test_rate_limit())
        asyncio.run(test_rate_limit_headers())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Make sure the server is running: uvicorn main:app --port 8001")
