#!/usr/bin/env python3
"""
Backend API Testing Suite for Bot Hosting Admin Panel
Tests all core functionality including CRUD operations, bot control, monitoring, and WebSocket
"""

import requests
import json
import time
import asyncio
import websockets
import os
from datetime import datetime
from typing import Dict, List, Any

# Get backend URL from frontend .env file
def get_backend_url():
    env_path = "/app/frontend/.env"
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.split('=')[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

class BotHostingAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.created_bots = []  # Track created bots for cleanup
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {test_name}: {status}")
        if details:
            print(f"  Details: {details}")
        print("-" * 80)
    
    def test_api_root(self):
        """Test the root API endpoint"""
        try:
            response = self.session.get(f"{API_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "version" in data:
                    self.log_test("API Root Endpoint", "✅ PASS", f"Response: {data}")
                    return True
                else:
                    self.log_test("API Root Endpoint", "❌ FAIL", "Missing expected fields in response")
                    return False
            else:
                self.log_test("API Root Endpoint", "❌ FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Root Endpoint", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_create_bot(self, bot_data: Dict[str, Any]) -> str:
        """Test bot creation and return bot ID if successful"""
        try:
            response = self.session.post(f"{API_URL}/bots", json=bot_data)
            if response.status_code == 200:
                bot = response.json()
                if "id" in bot and "name" in bot:
                    self.created_bots.append(bot["id"])
                    self.log_test(f"Create Bot ({bot_data['name']})", "✅ PASS", 
                                f"Bot ID: {bot['id']}, Type: {bot['bot_type']}")
                    return bot["id"]
                else:
                    self.log_test(f"Create Bot ({bot_data['name']})", "❌ FAIL", 
                                "Missing required fields in response")
                    return None
            else:
                self.log_test(f"Create Bot ({bot_data['name']})", "❌ FAIL", 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            self.log_test(f"Create Bot ({bot_data['name']})", "❌ FAIL", f"Exception: {str(e)}")
            return None
    
    def test_get_bots(self):
        """Test getting all bots"""
        try:
            response = self.session.get(f"{API_URL}/bots")
            if response.status_code == 200:
                bots = response.json()
                if isinstance(bots, list):
                    self.log_test("Get All Bots", "✅ PASS", f"Found {len(bots)} bots")
                    return True
                else:
                    self.log_test("Get All Bots", "❌ FAIL", "Response is not a list")
                    return False
            else:
                self.log_test("Get All Bots", "❌ FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get All Bots", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_get_bot_by_id(self, bot_id: str):
        """Test getting a specific bot by ID"""
        try:
            response = self.session.get(f"{API_URL}/bots/{bot_id}")
            if response.status_code == 200:
                bot = response.json()
                if "id" in bot and bot["id"] == bot_id:
                    self.log_test(f"Get Bot by ID ({bot_id[:8]}...)", "✅ PASS", 
                                f"Name: {bot.get('name', 'N/A')}, Status: {bot.get('status', 'N/A')}")
                    return True
                else:
                    self.log_test(f"Get Bot by ID ({bot_id[:8]}...)", "❌ FAIL", 
                                "Bot ID mismatch or missing")
                    return False
            else:
                self.log_test(f"Get Bot by ID ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Get Bot by ID ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_update_bot(self, bot_id: str, update_data: Dict[str, Any]):
        """Test updating a bot"""
        try:
            response = self.session.put(f"{API_URL}/bots/{bot_id}", json=update_data)
            if response.status_code == 200:
                bot = response.json()
                # Verify the update was applied
                updated = False
                for key, value in update_data.items():
                    if bot.get(key) == value:
                        updated = True
                        break
                
                if updated:
                    self.log_test(f"Update Bot ({bot_id[:8]}...)", "✅ PASS", 
                                f"Updated fields: {list(update_data.keys())}")
                    return True
                else:
                    self.log_test(f"Update Bot ({bot_id[:8]}...)", "❌ FAIL", 
                                "Update not reflected in response")
                    return False
            else:
                self.log_test(f"Update Bot ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Update Bot ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_start_bot(self, bot_id: str):
        """Test starting a bot"""
        try:
            response = self.session.post(f"{API_URL}/bots/{bot_id}/start")
            if response.status_code == 200:
                result = response.json()
                if "message" in result and "pid" in result:
                    self.log_test(f"Start Bot ({bot_id[:8]}...)", "✅ PASS", 
                                f"PID: {result['pid']}")
                    return True
                else:
                    self.log_test(f"Start Bot ({bot_id[:8]}...)", "❌ FAIL", 
                                "Missing expected fields in response")
                    return False
            else:
                self.log_test(f"Start Bot ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test(f"Start Bot ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_stop_bot(self, bot_id: str):
        """Test stopping a bot"""
        try:
            response = self.session.post(f"{API_URL}/bots/{bot_id}/stop")
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log_test(f"Stop Bot ({bot_id[:8]}...)", "✅ PASS", result["message"])
                    return True
                else:
                    self.log_test(f"Stop Bot ({bot_id[:8]}...)", "❌ FAIL", 
                                "Missing message in response")
                    return False
            else:
                self.log_test(f"Stop Bot ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test(f"Stop Bot ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_restart_bot(self, bot_id: str):
        """Test restarting a bot"""
        try:
            response = self.session.post(f"{API_URL}/bots/{bot_id}/restart")
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log_test(f"Restart Bot ({bot_id[:8]}...)", "✅ PASS", result["message"])
                    return True
                else:
                    self.log_test(f"Restart Bot ({bot_id[:8]}...)", "❌ FAIL", 
                                "Missing message in response")
                    return False
            else:
                self.log_test(f"Restart Bot ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test(f"Restart Bot ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_get_bot_logs(self, bot_id: str):
        """Test getting bot logs"""
        try:
            response = self.session.get(f"{API_URL}/bots/{bot_id}/logs")
            if response.status_code == 200:
                logs = response.json()
                if isinstance(logs, list):
                    self.log_test(f"Get Bot Logs ({bot_id[:8]}...)", "✅ PASS", 
                                f"Found {len(logs)} log entries")
                    return True
                else:
                    self.log_test(f"Get Bot Logs ({bot_id[:8]}...)", "❌ FAIL", 
                                "Response is not a list")
                    return False
            else:
                self.log_test(f"Get Bot Logs ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Get Bot Logs ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_add_bot_log(self, bot_id: str):
        """Test adding a log entry"""
        try:
            log_data = {
                "bot_id": bot_id,
                "level": "INFO",
                "message": "Test log entry from API test",
                "source": "test"
            }
            response = self.session.post(f"{API_URL}/bots/{bot_id}/logs", json=log_data)
            if response.status_code == 200:
                log_entry = response.json()
                if "id" in log_entry and log_entry["message"] == log_data["message"]:
                    self.log_test(f"Add Bot Log ({bot_id[:8]}...)", "✅ PASS", 
                                f"Log ID: {log_entry['id']}")
                    return True
                else:
                    self.log_test(f"Add Bot Log ({bot_id[:8]}...)", "❌ FAIL", 
                                "Log entry not created properly")
                    return False
            else:
                self.log_test(f"Add Bot Log ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Add Bot Log ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_system_metrics(self):
        """Test getting system metrics"""
        try:
            response = self.session.get(f"{API_URL}/system/metrics")
            if response.status_code == 200:
                metrics = response.json()
                required_fields = ["cpu_usage", "memory_usage", "disk_usage", "active_bots", "total_bots"]
                missing_fields = [field for field in required_fields if field not in metrics]
                
                if not missing_fields:
                    self.log_test("System Metrics", "✅ PASS", 
                                f"CPU: {metrics['cpu_usage']}%, Memory: {metrics['memory_usage']}%, "
                                f"Active Bots: {metrics['active_bots']}/{metrics['total_bots']}")
                    return True
                else:
                    self.log_test("System Metrics", "❌ FAIL", 
                                f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("System Metrics", "❌ FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("System Metrics", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
            
            async def test_ws():
                try:
                    async with websockets.connect(ws_url) as websocket:
                        # Wait for a message (system update should come within 10 seconds)
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(message)
                        
                        if "type" in data and "data" in data:
                            return True, f"Received message type: {data['type']}"
                        else:
                            return False, "Invalid message format"
                except asyncio.TimeoutError:
                    return False, "Timeout waiting for WebSocket message"
                except Exception as e:
                    return False, f"WebSocket error: {str(e)}"
            
            # Run the async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, details = loop.run_until_complete(test_ws())
            loop.close()
            
            if success:
                self.log_test("WebSocket Connection", "✅ PASS", details)
                return True
            else:
                self.log_test("WebSocket Connection", "❌ FAIL", details)
                return False
                
        except Exception as e:
            self.log_test("WebSocket Connection", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def test_delete_bot(self, bot_id: str):
        """Test deleting a bot"""
        try:
            response = self.session.delete(f"{API_URL}/bots/{bot_id}")
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log_test(f"Delete Bot ({bot_id[:8]}...)", "✅ PASS", result["message"])
                    if bot_id in self.created_bots:
                        self.created_bots.remove(bot_id)
                    return True
                else:
                    self.log_test(f"Delete Bot ({bot_id[:8]}...)", "❌ FAIL", 
                                "Missing message in response")
                    return False
            else:
                self.log_test(f"Delete Bot ({bot_id[:8]}...)", "❌ FAIL", 
                            f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Delete Bot ({bot_id[:8]}...)", "❌ FAIL", f"Exception: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up created bots"""
        print("\n" + "="*80)
        print("CLEANUP: Removing test bots...")
        print("="*80)
        
        for bot_id in self.created_bots.copy():
            self.test_delete_bot(bot_id)
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("="*80)
        print("BOT HOSTING ADMIN PANEL - BACKEND API TEST SUITE")
        print("="*80)
        print(f"Testing against: {BASE_URL}")
        print("="*80)
        
        results = {}
        
        # Test 1: API Root
        results["api_root"] = self.test_api_root()
        
        # Test 2: System Metrics
        results["system_metrics"] = self.test_system_metrics()
        
        # Test 3: Create demo bots
        bot_configs = [
            {
                "name": "Discord Music Bot",
                "description": "A Discord bot for playing music",
                "bot_type": "discord",
                "command": "python discord_bot.py",
                "environment_vars": {"DISCORD_TOKEN": "test_token_123"}
            },
            {
                "name": "Telegram Notification Bot",
                "description": "Sends notifications via Telegram",
                "bot_type": "telegram",
                "command": "python telegram_bot.py",
                "environment_vars": {"TELEGRAM_TOKEN": "test_telegram_token"}
            },
            {
                "name": "Webhook Handler",
                "description": "Handles incoming webhooks",
                "bot_type": "webhook",
                "command": "python webhook_handler.py",
                "port": 8080,
                "environment_vars": {"WEBHOOK_SECRET": "secret123"}
            }
        ]
        
        created_bot_ids = []
        for i, bot_config in enumerate(bot_configs):
            bot_id = self.test_create_bot(bot_config)
            if bot_id:
                created_bot_ids.append(bot_id)
                results[f"create_bot_{i+1}"] = True
            else:
                results[f"create_bot_{i+1}"] = False
        
        # Test 4: Get all bots
        results["get_all_bots"] = self.test_get_bots()
        
        # Test 5-8: Individual bot operations (using first created bot)
        if created_bot_ids:
            test_bot_id = created_bot_ids[0]
            
            # Get individual bot
            results["get_bot_by_id"] = self.test_get_bot_by_id(test_bot_id)
            
            # Update bot
            update_data = {"description": "Updated description for testing"}
            results["update_bot"] = self.test_update_bot(test_bot_id, update_data)
            
            # Bot control operations
            results["start_bot"] = self.test_start_bot(test_bot_id)
            time.sleep(1)  # Brief pause
            
            results["stop_bot"] = self.test_stop_bot(test_bot_id)
            time.sleep(1)  # Brief pause
            
            results["restart_bot"] = self.test_restart_bot(test_bot_id)
            time.sleep(1)  # Brief pause
            
            # Log operations
            results["add_bot_log"] = self.test_add_bot_log(test_bot_id)
            results["get_bot_logs"] = self.test_get_bot_logs(test_bot_id)
        
        # Test 9: WebSocket connection
        results["websocket"] = self.test_websocket_connection()
        
        # Summary
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print("-" * 80)
        print(f"OVERALL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Backend is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
        
        # Cleanup
        self.cleanup()
        
        return results

def main():
    """Main test execution"""
    tester = BotHostingAPITester()
    try:
        results = tester.run_all_tests()
        return results
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        tester.cleanup()
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {str(e)}")
        tester.cleanup()

if __name__ == "__main__":
    main()