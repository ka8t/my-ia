#!/usr/bin/env python3
import httpx
import asyncio

async def test():
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Sending request to Ollama...")
            response = await client.post(
                "http://ollama:11434/api/generate",
                json={
                    "model": "llama3.2:1b",
                    "prompt": "Bonjour",
                    "stream": False
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.json()["response"]
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
