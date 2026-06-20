import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "./WebSocketContext";
import { AuthContext } from "./AuthContext";
import { fetchWorkflows, fetchPreviousNotifcations, fetchLogs, fetchRcaEvents } from "../utils/utils";

const GlobalStateContext = createContext();
export function useGlobalState() {
  return useContext(GlobalStateContext);
}

// Helper function to check if item exists by _id (outside component to avoid recreation)
const itemExistsById = (array, item) => {
  if (!item || !item._id) return false;
  return array.some(existing => existing._id && String(existing._id) === String(item._id));
};

export const GlobalStateProvider = ({ children }) => {
  // Initialize state
  const [workflows, setWorkflows] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [rcaEvents, setRcaEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  
  // Use ref for message queue to avoid dependency issues
  const messageQueueRef = useRef([]);
  const isProcessingQueueRef = useRef(false);
  
  const { isAuthenticated, user } = useContext(AuthContext);
  const { ws, isConnected } = useWebSocket();

  // Fetch initial data from APIs
  useEffect(() => {
    if (!isAuthenticated || !user || initialized) {
      return;
    }

    const loadInitialData = async () => {
      try {
        setLoading(true);
        
        // Fetch fresh data from APIs
        const workflowsResponse = await fetchWorkflows(0, 100);
        if (workflowsResponse.status === "success" && workflowsResponse.data) {
          setWorkflows(workflowsResponse.data);
        }

        // Fetch notifications
        const notificationsData = await fetchPreviousNotifcations();
        if (Array.isArray(notificationsData)) {
          setNotifications(notificationsData);
          
          // Filter alerts from notifications (notifications with type=="alert")
          const allAlerts = notificationsData.filter(notif => notif.type === "alert");
          setAlerts(allAlerts);
        }

        // Fetch logs
        const logsData = await fetchLogs();
        if (Array.isArray(logsData)) {
          setLogs(logsData);
        }

        // Fetch RCA events
        const rcaData = await fetchRcaEvents();
        if (Array.isArray(rcaData)) {
          setRcaEvents(rcaData);
        }

        setInitialized(true);
      } catch (error) {
        console.error("Error loading initial data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, [isAuthenticated, user, initialized]);

  // Process a single WebSocket message - stable function with no external dependencies
  const processMessage = useCallback((data) => {
    const messageType = data.message_type || data.type;

    // Handle workflow updates
    if (messageType === "workflow" && data._id) {
      setWorkflows(prev => {
        const existingIndex = prev.findIndex(w => w._id && String(w._id) === String(data._id));
        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = { ...updated[existingIndex], ...data };
          return updated;
        } else if (!itemExistsById(prev, data)) {
          return [data, ...prev];
        }
        return prev;
      });
    }

    // Handle notifications (including alerts)
    if (messageType === "notification" || (data.type && data.type !== "workflow" && data.type !== "log")) {
      setNotifications(prev => {
        if (!itemExistsById(prev, data)) {
          return [data, ...prev];
        }
        return prev;
      });

      if (data.type === "alert") {
        setAlerts(prev => {
          if (!itemExistsById(prev, data)) {
            return [data, ...prev];
          }
          return prev;
        });
      }
    }

    // Handle logs - deduplicate by _id
    if (messageType === "log") {
      setLogs(prev => {
        if (!itemExistsById(prev, data)) {
          return [data, ...prev];
        }
        return prev;
      });
    }

    // Handle RCA events
    if (messageType === "rca") {
      setRcaEvents(prev => {
        const existingIndex = prev.findIndex(r => r._id && String(r._id) === String(data._id));
        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = { ...updated[existingIndex], ...data };
          return updated;
        } else if (!itemExistsById(prev, data)) {
          return [data, ...prev];
        }
        return prev;
      });
    }
  }, []); // No dependencies - uses only setState functions which are stable

  // Handle WebSocket messages
  useEffect(() => {
    if (!ws) {
      return;
    }

    const handleMessage = (event) => {
      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        // Ignore ping/pong messages
        if (data.type === "ping" || data.type === "pong" || data.message_type === "ping" || data.message_type === "pong") {
          return;
        }

        // Process message directly
        processMessage(data);
      } catch (error) {
        console.error("Error handling WebSocket message:", error);
      }
    };

    ws.addEventListener('message', handleMessage);
    return () => ws.removeEventListener('message', handleMessage);
  }, [ws, processMessage]);

  const value = {
    workflows,
    setWorkflows,
    notifications,
    setNotifications,
    logs,
    setLogs,
    alerts,
    setAlerts,
    rcaEvents,
    setRcaEvents,
    loading,
  };

  return (
    <GlobalStateContext.Provider value={value}>
      {children}
    </GlobalStateContext.Provider>
  );
};

