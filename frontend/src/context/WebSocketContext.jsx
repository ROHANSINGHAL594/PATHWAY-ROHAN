import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from "react";
import { AuthContext } from "./AuthContext";

const WebSocketContext = createContext();

export const useWebSocket = () => {
  return useContext(WebSocketContext);
};

export const WebSocketProvider = ({ children }) => {
  const { isAuthenticated, user } = useContext(AuthContext);
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [logs, setLogs] = useState([]);
  const [workflows, setWorkflows] = useState([]); // Store workflow updates
  const [rcaEvents, setRcaEvents] = useState([]); // Store RCA events
  const reconnectTimeoutRef = useRef(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const maxReconnectAttempts = 5;
  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const pongReceivedRef = useRef(true); // Track if pong was received (ref needed for synchronous interval check)
  const pongTimeoutRef = useRef(null);
  const [isManualDisconnect, setIsManualDisconnect] = useState(false); // Track if disconnect was manual

  // Message handlers
  const handleMessage = useCallback((event) => {
    try {
      let data;
      if (typeof event.data === 'string') {
        // Backend sends BSON dumps which are JSON strings
        data = JSON.parse(event.data);
      } else {
        data = event.data;
      }
      
      // Handle pong response for connection health check
      if (data.type === "pong" || data.message_type === "pong") {
        pongReceivedRef.current = true;
        if (pongTimeoutRef.current) {
          clearTimeout(pongTimeoutRef.current);
          pongTimeoutRef.current = null;
        }
        return; // Don't process pong as regular message
      }
      
      // Determine message type from backend message_type or infer from data
      const messageType = data.message_type || data.type || (data.alert ? "alert" : "notification");
      
      // Alerts are notifications with type "alert" or have an alert field
      if (messageType === "alert" || (data.type === "alert") || (data.alert && data.type === "notification")) {
        setAlerts(prev => {
          // Avoid duplicates by _id
          const exists = prev.find(a => {
            if (a._id && data._id) return String(a._id) === String(data._id);
            return false;
          });
          if (exists) return prev;
          return [data, ...prev].slice(0, 100); // Keep last 100 alerts
        });
      }
      
      // All notifications (including alerts) go to notifications list
      if (messageType === "notification" || messageType === "alert" || data.type) {
        setNotifications(prev => {
          const exists = prev.find(n => {
            if (n._id && data._id) return String(n._id) === String(data._id);
            return false;
          });
          if (exists) return prev;
          return [data, ...prev].slice(0, 100);
        });
      }
      
      // Workflow updates
      if (messageType === "workflow") {
        setWorkflows(prev => {
          // Update or add workflow
          const existingIndex = prev.findIndex(w => {
            if (w._id && data._id) return String(w._id) === String(data._id);
            return false;
          });
          if (existingIndex >= 0) {
            // Update existing workflow
            const updated = [...prev];
            updated[existingIndex] = data;
            return updated;
          } else {
            // Add new workflow
            return [data, ...prev].slice(0, 100);
          }
        });
      }
      
      // Logs
      if (messageType === "log") {
        console.log("Received log message:", data);
        setLogs(prev => [data, ...prev]);
        console.log("Updated logs state:", logs);
      }
      
      // RCA Events
      if (messageType === "rca") {
        console.log("Received RCA event:", data);
        setRcaEvents(prev => {
          // Update or add RCA event
          const existingIndex = prev.findIndex(r => {
            if (r._id && data._id) return String(r._id) === String(data._id);
            return false;
          });
          if (existingIndex >= 0) {
            // Update existing RCA event
            const updated = [...prev];
            updated[existingIndex] = data;
            return updated;
          } else {
            // Add new RCA event
            return [data, ...prev].slice(0, 100); // Keep last 100 RCA events
          }
        });
      }
    } catch (error) {
      console.error("Error parsing WebSocket message:", error, event.data);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated || !user) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    // Derive WebSocket URL from API server URL if VITE_WS_SERVER is not set
    let wsBaseUrl = import.meta.env.VITE_WS_SERVER;
    if (!wsBaseUrl) {
      // Use API server URL and convert to WebSocket protocol
      const apiServer = import.meta.env.VITE_API_SERVER || 'http://localhost:8081';
      wsBaseUrl = apiServer.replace('http://', 'ws://').replace('https://', 'wss://');
    }

    // Ensure WebSocket URL uses ws:// or wss:// protocol
    if (!wsBaseUrl.startsWith('ws://') && !wsBaseUrl.startsWith('wss://')) {
      // If it's http/https, convert to ws/wss
      wsBaseUrl = wsBaseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    }
    
    const wsUrl = `${wsBaseUrl}/ws/`;  // Backend endpoint is /ws/ (prefix /ws + endpoint /)
    console.log("Connecting to global WebSocket:", wsUrl);
    console.log("User authenticated:", isAuthenticated, "User:", user?.email);
    console.log("API Server:", import.meta.env.VITE_API_SERVER);
    console.log("WS Server:", import.meta.env.VITE_WS_SERVER);
    
    const websocket = new WebSocket(wsUrl);
    wsRef.current = websocket;
    
    // Log connection state changes
    websocket.addEventListener('open', () => {
      console.log("WebSocket OPEN event fired");
    });
    
    websocket.addEventListener('error', (error) => {
      console.error("WebSocket ERROR event fired:", error);
      console.error("WebSocket readyState:", websocket.readyState);
    });

    websocket.onopen = () => {
      console.log("Global WebSocket connected");
      setIsConnected(true);
      setReconnectAttempts(0);
      pongReceivedRef.current = true;
      setWs(websocket);
      
      // Send periodic ping to keep connection alive and detect broken connections
      const pingInterval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          // Check if previous pong was received
          if (!pongReceivedRef.current) {
            console.warn("Pong not received, connection may be broken");
            websocket.close(); // Force close to trigger reconnection
            return;
          }
          
          // Reset pong flag and send ping
          pongReceivedRef.current = false;
          websocket.send(JSON.stringify({ type: "ping" }));
          
          // Set timeout to check for pong response (10 seconds)
          if (pongTimeoutRef.current) {
            clearTimeout(pongTimeoutRef.current);
          }
          pongTimeoutRef.current = setTimeout(() => {
            if (!pongReceivedRef.current) {
              console.warn("Pong timeout, connection may be broken");
              websocket.close(); // Force close to trigger reconnection
            }
          }, 10000);
        } else {
          clearInterval(pingInterval);
          pingIntervalRef.current = null;
        }
      }, 30000);
      
      // Store interval ID for cleanup
      pingIntervalRef.current = pingInterval;
    };

    websocket.onmessage = handleMessage;

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
      console.error("WebSocket URL attempted:", wsUrl);
      setIsConnected(false);
      // Error will trigger onclose, which will handle reconnection
    };

    websocket.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      console.log("Close event details:", {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        url: wsUrl
      });
      
      setIsConnected(false);
      setWs(null);
      
      // Clear ping interval and pong timeout if exists
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (pongTimeoutRef.current) {
        clearTimeout(pongTimeoutRef.current);
        pongTimeoutRef.current = null;
      }
      
      wsRef.current = null;

      // Don't reconnect on authentication failure (code 1008 = WS_1008_POLICY_VIOLATION)
      if (event.code === 1008) {
        console.error("WebSocket authentication failed. Please log in again.");
        return;
      }

      // Attempt to reconnect if not a manual disconnect and user is still authenticated
      if (!isManualDisconnect && isAuthenticated && user) {
        setReconnectAttempts(prev => {
          const newAttempts = prev + 1;
        
        // Use exponential backoff with max delay of 30 seconds
        // After max attempts, continue trying but with longer delays (up to 60 seconds)
          const baseDelay = newAttempts <= maxReconnectAttempts 
            ? Math.min(1000 * Math.pow(2, newAttempts - 1), 30000)
            : Math.min(30000 + (newAttempts - maxReconnectAttempts) * 10000, 60000);
          
          console.log(`Reconnecting in ${baseDelay}ms (attempt ${newAttempts})`);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          // Reset manual disconnect flag before reconnecting
            setIsManualDisconnect(false);
          connect();
        }, baseDelay);
          
          return newAttempts;
        });
      } else if (isManualDisconnect) {
        // Reset flag after handling manual disconnect
        setIsManualDisconnect(false);
        setReconnectAttempts(0);
      }
    };
  }, [isAuthenticated, user, handleMessage]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    // Mark as manual disconnect to prevent reconnection
    setIsManualDisconnect(true);
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Clear ping interval and pong timeout
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnect");
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setWs(null);
    setReconnectAttempts(0);
  }, []);

  // Initialize WebSocket when authenticated
  useEffect(() => {
    console.log("WebSocket effect triggered:", { isAuthenticated, user: user?.email });
    
    if (!isAuthenticated || !user) {
      console.log("Not authenticated, disconnecting WebSocket");
      disconnect();
      return;
    }

    // Small delay to ensure cookies are set after login
    const timeoutId = setTimeout(() => {
      console.log("Attempting WebSocket connection...");
      connect();
    }, 500); // Increased delay to ensure cookies are set

    return () => {
      clearTimeout(timeoutId);
      disconnect();
    };
  }, [isAuthenticated, user, connect, disconnect]);

  // Get alerts for a specific pipeline
  const getAlertsForPipeline = useCallback((pipelineId) => {
    if (!pipelineId) return [];
    const pipelineIdStr = String(pipelineId);
    return alerts.filter(alert => {
      const alertPipelineId = alert.pipeline_id ? String(alert.pipeline_id) : null;
      return alertPipelineId === pipelineIdStr;
    });
  }, [alerts]);

  // Get all alerts
  const getAllAlerts = useCallback(() => {
    return alerts;
  }, [alerts]);

  // Clear alerts for a pipeline
  const clearAlertsForPipeline = useCallback((pipelineId) => {
    setAlerts(prev => prev.filter(alert => alert.pipeline_id !== pipelineId));
  }, []);

  // Get workflow by ID
  const getWorkflowById = useCallback((workflowId) => {
    if (!workflowId) return null;
    const workflowIdStr = String(workflowId);
    return workflows.find(w => {
      if (w._id) return String(w._id) === workflowIdStr;
      return false;
    });
  }, [workflows]);

  // Get all workflows
  const getAllWorkflows = useCallback(() => {
    return workflows;
  }, [workflows]);

  // Get notifications for a specific pipeline
  const getNotificationsForPipeline = useCallback((pipelineId) => {
    if (!pipelineId) return [];
    const pipelineIdStr = String(pipelineId);
    return notifications.filter(notif => {
      const notifPipelineId = notif.pipeline_id ? String(notif.pipeline_id) : null;
      return notifPipelineId === pipelineIdStr;
    });
  }, [notifications]);

  // Get logs for a specific pipeline
  const getLogsForPipeline = useCallback((pipelineId) => {
    if (!pipelineId) return [];
    const pipelineIdStr = String(pipelineId);
    return logs.filter(log => {
      const logPipelineId = log.pipeline_id ? String(log.pipeline_id) : null;
      return logPipelineId === pipelineIdStr;
    });
  }, [logs]);

  // Get RCA events for a specific pipeline
  const getRcaEventsForPipeline = useCallback((pipelineId) => {
    if (!pipelineId) return [];
    const pipelineIdStr = String(pipelineId);
    return rcaEvents.filter(rca => {
      const rcaPipelineId = rca.pipeline_id ? String(rca.pipeline_id) : null;
      return rcaPipelineId === pipelineIdStr;
    });
  }, [rcaEvents]);

  // Get all RCA events
  const getAllRcaEvents = useCallback(() => {
    return rcaEvents;
  }, [rcaEvents]);

  // Get RCA event by ID
  const getRcaEventById = useCallback((rcaId) => {
    if (!rcaId) return null;
    const rcaIdStr = String(rcaId);
    return rcaEvents.find(r => {
      if (r._id) return String(r._id) === rcaIdStr;
      return false;
    });
  }, [rcaEvents]);

  const value = {
    // Connection state
    ws,
    isConnected,
    connect,
    disconnect,
    // Data
    alerts,
    notifications,
    logs,
    workflows,
    rcaEvents,
    // Helper functions
    getAlertsForPipeline,
    getAllAlerts,
    clearAlertsForPipeline,
    getNotificationsForPipeline,
    getLogsForPipeline,
    getWorkflowById,
    getAllWorkflows,
    getRcaEventsForPipeline,
    getAllRcaEvents,
    getRcaEventById,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

