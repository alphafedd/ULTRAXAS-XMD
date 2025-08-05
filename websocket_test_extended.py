#!/usr/bin/env python3
"""
Extended WebSocket test to wait for backend system updates
"""

import asyncio
import websockets
import json

def get_backend_url():
    env_path = "/app/frontend/.env"
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.split('=')[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()

async def test_backend_websocket():
    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            print("🔍 Waiting for backend system updates (should come every 5 seconds)...")
            
            backend_messages = 0
            start_time = asyncio.get_event_loop().time()
            
            while backend_messages < 2 and (asyncio.get_event_loop().time() - start_time) < 15:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=6.0)
                    
                    try:
                        data = json.loads(message)
                        
                        # Check if this is a backend system update
                        if data.get("type") == "system_update" and "data" in data:
                            backend_messages += 1
                            print(f"\n✅ Backend system update #{backend_messages} received!")
                            print(f"Metrics: CPU={data['data']['metrics'].get('cpu_usage', 'N/A')}%, "
                                  f"Memory={data['data']['metrics'].get('memory_usage', 'N/A')}%")
                            print(f"Running bots: {len(data['data'].get('running_bots', []))}")
                            
                        elif data.get("type") in ["hot", "liveReload", "reconnect"]:
                            # Skip development server messages
                            continue
                        else:
                            print(f"📨 Other message type: {data.get('type', 'unknown')}")
                            
                    except json.JSONDecodeError:
                        print(f"❌ Non-JSON message: {message}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    continue
            
            if backend_messages >= 1:
                print(f"\n🎉 SUCCESS: Received {backend_messages} backend system updates!")
                return True
            else:
                print(f"\n❌ FAIL: No backend system updates received in 15 seconds")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_backend_websocket())
    exit(0 if result else 1)