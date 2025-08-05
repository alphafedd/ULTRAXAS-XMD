#!/usr/bin/env python3
"""
Debug WebSocket connection to see what messages are being received
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

async def debug_websocket():
    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Wait for messages
            for i in range(3):  # Listen for 3 messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    print(f"\n📨 Message {i+1} received:")
                    print(f"Raw message: {message}")
                    
                    try:
                        data = json.loads(message)
                        print(f"Parsed JSON: {json.dumps(data, indent=2)}")
                        
                        if "type" in data and "data" in data:
                            print("✅ Message has correct format (type and data fields)")
                        else:
                            print("❌ Message missing 'type' or 'data' fields")
                            print(f"Available keys: {list(data.keys())}")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse JSON: {e}")
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout waiting for message {i+1}")
                    break
                    
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_websocket())