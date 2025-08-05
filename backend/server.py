from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
import psutil
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Bot Hosting Admin Panel")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Enums
class BotStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

class BotType(str, Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    GENERAL = "general"

# Models
class Bot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    bot_type: BotType
    status: BotStatus = BotStatus.STOPPED
    port: Optional[int] = None
    command: str
    working_directory: str = "/app"
    environment_vars: Dict[str, str] = {}
    pid: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_started: Optional[datetime] = None
    last_stopped: Optional[datetime] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime: Optional[str] = None

class BotCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    bot_type: BotType
    command: str
    working_directory: str = "/app"
    environment_vars: Dict[str, str] = {}
    port: Optional[int] = None

class BotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    working_directory: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None
    port: Optional[int] = None

class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bot_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str  # INFO, ERROR, WARNING, DEBUG
    message: str
    source: str = "bot"  # bot, system, api

class LogEntryCreate(BaseModel):
    bot_id: str
    level: str
    message: str
    source: str = "bot"

class SystemMetrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_bots: int
    total_bots: int

# Utility functions
async def get_bot_by_id(bot_id: str) -> Optional[Bot]:
    bot_data = await db.bots.find_one({"id": bot_id})
    if bot_data:
        return Bot(**bot_data)
    return None

async def update_bot_status(bot_id: str, status: BotStatus, pid: Optional[int] = None):
    update_data = {"status": status}
    if pid is not None:
        update_data["pid"] = pid
    if status == BotStatus.RUNNING:
        update_data["last_started"] = datetime.utcnow()
    elif status == BotStatus.STOPPED:
        update_data["last_stopped"] = datetime.utcnow()
        update_data["pid"] = None
    
    await db.bots.update_one({"id": bot_id}, {"$set": update_data})

async def log_message(bot_id: str, level: str, message: str, source: str = "system"):
    log_entry = LogEntry(bot_id=bot_id, level=level, message=message, source=source)
    await db.logs.insert_one(log_entry.dict())
    
    # Broadcast log to WebSocket clients
    log_data = log_entry.dict()
    # Convert datetime to ISO string for JSON serialization
    if 'timestamp' in log_data:
        log_data['timestamp'] = log_data['timestamp'].isoformat()
    
    await manager.broadcast(json.dumps({
        "type": "log",
        "data": log_data
    }))

def get_process_stats(pid: int) -> Dict[str, Any]:
    try:
        process = psutil.Process(pid)
        return {
            "cpu_usage": process.cpu_percent(),
            "memory_usage": process.memory_percent(),
            "status": process.status(),
            "create_time": process.create_time()
        }
    except psutil.NoSuchProcess:
        return None

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Bot Hosting Admin Panel API", "version": "1.0.0"}

@api_router.post("/bots", response_model=Bot)
async def create_bot(bot_data: BotCreate):
    bot = Bot(**bot_data.dict())
    await db.bots.insert_one(bot.dict())
    await log_message(bot.id, "INFO", f"Bot '{bot.name}' created", "api")
    return bot

@api_router.get("/bots", response_model=List[Bot])
async def get_bots():
    bots_data = await db.bots.find().to_list(1000)
    bots = [Bot(**bot_data) for bot_data in bots_data]
    
    # Update real-time stats for running bots
    for bot in bots:
        if bot.status == BotStatus.RUNNING and bot.pid:
            stats = get_process_stats(bot.pid)
            if stats:
                bot.cpu_usage = stats["cpu_usage"]
                bot.memory_usage = stats["memory_usage"]
                # Calculate uptime
                uptime_seconds = datetime.utcnow().timestamp() - stats["create_time"]
                uptime_delta = timedelta(seconds=int(uptime_seconds))
                bot.uptime = str(uptime_delta)
            else:
                # Process not found, update status
                await update_bot_status(bot.id, BotStatus.STOPPED)
                bot.status = BotStatus.STOPPED
    
    return bots

@api_router.get("/bots/{bot_id}", response_model=Bot)
async def get_bot(bot_id: str):
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Update real-time stats if running
    if bot.status == BotStatus.RUNNING and bot.pid:
        stats = get_process_stats(bot.pid)
        if stats:
            bot.cpu_usage = stats["cpu_usage"]
            bot.memory_usage = stats["memory_usage"]
            uptime_seconds = datetime.utcnow().timestamp() - stats["create_time"]
            uptime_delta = timedelta(seconds=int(uptime_seconds))
            bot.uptime = str(uptime_delta)
        else:
            await update_bot_status(bot.id, BotStatus.STOPPED)
            bot.status = BotStatus.STOPPED
    
    return bot

@api_router.put("/bots/{bot_id}", response_model=Bot)
async def update_bot(bot_id: str, bot_update: BotUpdate):
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    update_data = {k: v for k, v in bot_update.dict().items() if v is not None}
    if update_data:
        await db.bots.update_one({"id": bot_id}, {"$set": update_data})
        await log_message(bot_id, "INFO", f"Bot '{bot.name}' updated", "api")
    
    return await get_bot_by_id(bot_id)

@api_router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str):
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Stop bot if running
    if bot.status == BotStatus.RUNNING:
        await stop_bot(bot_id)
    
    await db.bots.delete_one({"id": bot_id})
    await db.logs.delete_many({"bot_id": bot_id})
    await log_message(bot_id, "INFO", f"Bot '{bot.name}' deleted", "api")
    return {"message": "Bot deleted successfully"}

@api_router.post("/bots/{bot_id}/start")
async def start_bot(bot_id: str):
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        await update_bot_status(bot_id, BotStatus.STARTING)
        await log_message(bot_id, "INFO", f"Starting bot '{bot.name}'", "api")
        
        # Simulate bot start (in real implementation, this would start actual processes)
        env = os.environ.copy()
        env.update(bot.environment_vars)
        
        # For demo purposes, we'll simulate a running process
        # In production, you'd use subprocess.Popen or similar
        import random
        fake_pid = random.randint(1000, 9999)
        
        await update_bot_status(bot_id, BotStatus.RUNNING, fake_pid)
        await log_message(bot_id, "INFO", f"Bot '{bot.name}' started successfully with PID {fake_pid}", "system")
        
        return {"message": "Bot started successfully", "pid": fake_pid}
    
    except Exception as e:
        await update_bot_status(bot_id, BotStatus.ERROR)
        await log_message(bot_id, "ERROR", f"Failed to start bot: {str(e)}", "system")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

@api_router.post("/bots/{bot_id}/stop")
async def stop_bot(bot_id: str):
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot.status != BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    try:
        await update_bot_status(bot_id, BotStatus.STOPPING)
        await log_message(bot_id, "INFO", f"Stopping bot '{bot.name}'", "api")
        
        # Simulate stopping the process
        if bot.pid:
            # In production, you'd use os.kill or psutil to terminate the process
            pass
        
        await update_bot_status(bot_id, BotStatus.STOPPED)
        await log_message(bot_id, "INFO", f"Bot '{bot.name}' stopped successfully", "system")
        
        return {"message": "Bot stopped successfully"}
    
    except Exception as e:
        await update_bot_status(bot_id, BotStatus.ERROR)
        await log_message(bot_id, "ERROR", f"Failed to stop bot: {str(e)}", "system")
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")

@api_router.post("/bots/{bot_id}/restart")
async def restart_bot(bot_id: str):
    try:
        await stop_bot(bot_id)
        await asyncio.sleep(1)  # Brief pause between stop and start
        return await start_bot(bot_id)
    except HTTPException as e:
        if "not running" in str(e.detail):
            return await start_bot(bot_id)
        raise e

@api_router.get("/bots/{bot_id}/logs")
async def get_bot_logs(bot_id: str, limit: int = 100, level: Optional[str] = None):
    query = {"bot_id": bot_id}
    if level:
        query["level"] = level
    
    logs_data = await db.logs.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    return [LogEntry(**log_data) for log_data in logs_data]

@api_router.post("/bots/{bot_id}/logs")
async def add_bot_log(bot_id: str, log_data: LogEntryCreate):
    log_entry = LogEntry(**log_data.dict())
    await db.logs.insert_one(log_entry.dict())
    
    # Broadcast log to WebSocket clients
    log_dict = log_entry.dict()
    # Convert datetime to ISO string for JSON serialization
    if 'timestamp' in log_dict:
        log_dict['timestamp'] = log_dict['timestamp'].isoformat()
    
    await manager.broadcast(json.dumps({
        "type": "log",
        "data": log_dict
    }))
    
    return log_entry

@api_router.get("/system/metrics")
async def get_system_metrics():
    # Get system metrics
    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get bot counts
    total_bots = await db.bots.count_documents({})
    active_bots = await db.bots.count_documents({"status": "running"})
    
    metrics = SystemMetrics(
        cpu_usage=cpu_usage,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        active_bots=active_bots,
        total_bots=total_bots
    )
    
    return metrics

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic system updates
            await asyncio.sleep(5)
            
            # Get current system metrics
            metrics = await get_system_metrics()
            
            # Get running bots with updated stats
            bots_data = await db.bots.find({"status": "running"}).to_list(100)
            bots_with_stats = []
            
            for bot_data in bots_data:
                bot = Bot(**bot_data)
                if bot.pid:
                    stats = get_process_stats(bot.pid)
                    if stats:
                        bot.cpu_usage = stats["cpu_usage"]
                        bot.memory_usage = stats["memory_usage"]
                        uptime_seconds = datetime.utcnow().timestamp() - stats["create_time"]
                        uptime_delta = timedelta(seconds=int(uptime_seconds))
                        bot.uptime = str(uptime_delta)
                    else:
                        await update_bot_status(bot.id, BotStatus.STOPPED)
                        continue
                bots_with_stats.append(bot.dict())
            
            # Broadcast system update
            metrics_data = metrics.dict()
            # Convert datetime to ISO string for JSON serialization
            if 'timestamp' in metrics_data:
                metrics_data['timestamp'] = metrics_data['timestamp'].isoformat()
            
            # Convert datetime fields in bot data
            bots_serializable = []
            for bot_dict in bots_with_stats:
                bot_copy = bot_dict.copy()
                for key, value in bot_copy.items():
                    if isinstance(value, datetime):
                        bot_copy[key] = value.isoformat()
                bots_serializable.append(bot_copy)
            
            await manager.broadcast(json.dumps({
                "type": "system_update",
                "data": {
                    "metrics": metrics_data,
                    "running_bots": bots_serializable
                }
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Bot Hosting Admin Panel API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Bot Hosting Admin Panel API shutdown")