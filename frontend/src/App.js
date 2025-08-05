import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:');

// Dashboard Component
const Dashboard = () => {
  const [bots, setBots] = useState([]);
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [logs, setLogs] = useState([]);
  const [selectedBot, setSelectedBot] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws`);
    
    ws.onopen = () => {
      setWsConnected(true);
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'system_update') {
        setSystemMetrics(data.data.metrics);
        // Update running bots with real-time stats
        setBots(prevBots => 
          prevBots.map(bot => {
            const updatedBot = data.data.running_bots.find(rb => rb.id === bot.id);
            return updatedBot ? { ...bot, ...updatedBot } : bot;
          })
        );
      } else if (data.type === 'log') {
        setLogs(prevLogs => [data.data, ...prevLogs.slice(0, 499)]); // Keep last 500 logs
      }
    };
    
    ws.onclose = () => {
      setWsConnected(false);
      console.log('WebSocket disconnected');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, []);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [botsRes, metricsRes] = await Promise.all([
          axios.get(`${API}/bots`),
          axios.get(`${API}/system/metrics`)
        ]);
        
        setBots(botsRes.data);
        setSystemMetrics(metricsRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Fetch logs for selected bot
  useEffect(() => {
    if (selectedBot) {
      const fetchLogs = async () => {
        try {
          const response = await axios.get(`${API}/bots/${selectedBot}/logs?limit=100`);
          setLogs(response.data);
        } catch (error) {
          console.error('Error fetching logs:', error);
        }
      };
      fetchLogs();
    }
  }, [selectedBot]);

  const handleBotAction = async (botId, action) => {
    try {
      await axios.post(`${API}/bots/${botId}/${action}`);
      // Refresh bots data
      const response = await axios.get(`${API}/bots`);
      setBots(response.data);
    } catch (error) {
      console.error(`Error ${action} bot:`, error);
      alert(`Failed to ${action} bot: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'bg-green-500';
      case 'stopped': return 'bg-gray-500';
      case 'error': return 'bg-red-500';
      case 'starting': return 'bg-yellow-500';
      case 'stopping': return 'bg-orange-500';
      default: return 'bg-gray-500';
    }
  };

  const getLogLevelColor = (level) => {
    switch (level) {
      case 'ERROR': return 'text-red-500';
      case 'WARNING': return 'text-yellow-500';
      case 'INFO': return 'text-blue-500';
      case 'DEBUG': return 'text-gray-500';
      default: return 'text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading Bot Hosting Admin Panel...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">Bot Hosting Admin Panel</h1>
              <div className={`ml-4 px-2 py-1 rounded-full text-xs font-medium ${wsConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
              </div>
            </div>
            <div className="text-sm text-gray-500">
              Real-time Monitoring & Logs
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* System Metrics */}
        {systemMetrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">CPU</span>
                  </div>
                </div>
                <div className="ml-4">
                  <h3 className="text-sm font-medium text-gray-500">CPU Usage</h3>
                  <p className="text-2xl font-semibold text-gray-900">{systemMetrics.cpu_usage.toFixed(1)}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">RAM</span>
                  </div>
                </div>
                <div className="ml-4">
                  <h3 className="text-sm font-medium text-gray-500">Memory Usage</h3>
                  <p className="text-2xl font-semibold text-gray-900">{systemMetrics.memory_usage.toFixed(1)}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">💾</span>
                  </div>
                </div>
                <div className="ml-4">
                  <h3 className="text-sm font-medium text-gray-500">Disk Usage</h3>
                  <p className="text-2xl font-semibold text-gray-900">{systemMetrics.disk_usage.toFixed(1)}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">🤖</span>
                  </div>
                </div>
                <div className="ml-4">
                  <h3 className="text-sm font-medium text-gray-500">Active Bots</h3>
                  <p className="text-2xl font-semibold text-gray-900">{systemMetrics.active_bots}/{systemMetrics.total_bots}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Bots Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Bot Management</h2>
            </div>
            
            <div className="p-6">
              {bots.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-gray-400 mb-4">
                    <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 mb-1">No bots configured</h3>
                  <p className="text-sm text-gray-500">Create your first bot to start monitoring</p>
                  <button className="mt-4 bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 transition-colors">
                    Add Bot
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {bots.map((bot) => (
                    <div key={bot.id} className={`border rounded-lg p-4 ${selectedBot === bot.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center">
                          <div className={`w-3 h-3 rounded-full ${getStatusColor(bot.status)} mr-3`}></div>
                          <div>
                            <h3 className="font-medium text-gray-900">{bot.name}</h3>
                            <p className="text-sm text-gray-500">{bot.bot_type} bot</p>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          {bot.status === 'running' ? (
                            <>
                              <button
                                onClick={() => handleBotAction(bot.id, 'stop')}
                                className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
                              >
                                Stop
                              </button>
                              <button
                                onClick={() => handleBotAction(bot.id, 'restart')}
                                className="px-3 py-1 bg-yellow-500 text-white text-sm rounded hover:bg-yellow-600 transition-colors"
                              >
                                Restart
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => handleBotAction(bot.id, 'start')}
                              className="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600 transition-colors"
                            >
                              Start
                            </button>
                          )}
                          <button
                            onClick={() => setSelectedBot(selectedBot === bot.id ? null : bot.id)}
                            className={`px-3 py-1 text-sm rounded transition-colors ${selectedBot === bot.id ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                          >
                            Logs
                          </button>
                        </div>
                      </div>
                      
                      {bot.status === 'running' && (
                        <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-gray-200">
                          <div className="text-center">
                            <p className="text-xs text-gray-500">CPU</p>
                            <p className="text-sm font-medium">{bot.cpu_usage.toFixed(1)}%</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-gray-500">Memory</p>
                            <p className="text-sm font-medium">{bot.memory_usage.toFixed(1)}%</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-gray-500">Uptime</p>
                            <p className="text-sm font-medium">{bot.uptime || '0:00:00'}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Logs Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">
                Real-time Logs {selectedBot && `- ${bots.find(b => b.id === selectedBot)?.name}`}
              </h2>
            </div>
            
            <div className="h-96 overflow-y-auto p-4 bg-gray-900 text-green-400 font-mono text-sm">
              {logs.length === 0 ? (
                <div className="text-gray-500 text-center py-8">
                  {selectedBot ? 'No logs available for this bot' : 'Select a bot to view logs'}
                </div>
              ) : (
                <div className="space-y-1">
                  {logs.slice(0, 100).map((log, index) => (
                    <div key={`${log.id}-${index}`} className="flex text-xs">
                      <span className="text-gray-400 mr-2">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={`mr-2 font-bold ${getLogLevelColor(log.level)}`}>
                        [{log.level}]
                      </span>
                      <span className="text-gray-300 mr-2">
                        [{log.source}]
                      </span>
                      <span>{log.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Demo Data Setup Component
const DemoSetup = ({ onSetupComplete }) => {
  const [setting, setSetting] = useState(false);

  const setupDemoData = async () => {
    setSetting(true);
    try {
      // Create demo bots
      const demoBots = [
        {
          name: "Discord Music Bot",
          description: "A Discord bot for playing music in voice channels",
          bot_type: "discord",
          command: "python discord_bot.py",
          port: 8080,
          environment_vars: {
            "DISCORD_TOKEN": "your_discord_token_here",
            "COMMAND_PREFIX": "!"
          }
        },
        {
          name: "Telegram Weather Bot",
          description: "A Telegram bot providing weather updates",
          bot_type: "telegram",
          command: "node telegram_bot.js",
          environment_vars: {
            "TELEGRAM_TOKEN": "your_telegram_token_here",
            "WEATHER_API_KEY": "your_weather_api_key"
          }
        },
        {
          name: "Webhook Handler",
          description: "Generic webhook handler for various integrations",
          bot_type: "webhook",
          command: "python webhook_handler.py",
          port: 3001,
          environment_vars: {
            "SECRET_KEY": "webhook_secret_123"
          }
        }
      ];

      for (const bot of demoBots) {
        await axios.post(`${API}/bots`, bot);
      }

      // Start the first bot as demo
      const botsResponse = await axios.get(`${API}/bots`);
      if (botsResponse.data.length > 0) {
        await axios.post(`${API}/bots/${botsResponse.data[0].id}/start`);
      }

      onSetupComplete();
    } catch (error) {
      console.error('Error setting up demo data:', error);
      alert('Failed to setup demo data');
    } finally {
      setSetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 mb-4">
            <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome to Bot Hosting Admin Panel</h3>
          <p className="text-sm text-gray-500 mb-6">
            Get started by setting up some demo bots to see the real-time monitoring in action.
          </p>
          <button
            onClick={setupDemoData}
            disabled={setting}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {setting ? 'Setting up...' : 'Setup Demo Bots'}
          </button>
          <button
            onClick={onSetupComplete}
            className="w-full mt-2 bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Skip & Continue
          </button>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [showDemo, setShowDemo] = useState(true);
  const [bots, setBots] = useState([]);

  useEffect(() => {
    // Check if there are existing bots
    const checkExistingBots = async () => {
      try {
        const response = await axios.get(`${API}/bots`);
        if (response.data.length > 0) {
          setShowDemo(false);
        }
      } catch (error) {
        console.error('Error checking existing bots:', error);
      }
    };
    
    checkExistingBots();
  }, []);

  return (
    <div className="App">
      {showDemo ? (
        <DemoSetup onSetupComplete={() => setShowDemo(false)} />
      ) : (
        <Dashboard />
      )}
    </div>
  );
}

export default App;