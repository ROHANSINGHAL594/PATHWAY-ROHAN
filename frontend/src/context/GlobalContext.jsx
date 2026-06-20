import { createContext, useContext, useState, useEffect } from "react";
import { AuthContext } from "./AuthContext";
import { fetchAllWorkflows, fetchPreviousNotifications } from "../utils/developerDashboard.api";

const GlobalContext = createContext();

export function useGlobalContext() {
  return useContext(GlobalContext);
}

export const GlobalContextProvider = ({ children }) => {
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [containerId, setContainerId] = useState();
  const { login, user, logout, isAuthenticated } = useContext(AuthContext);
  const [sidebarOpen, setSideBarOpen] = useState(false);
  const [workflows, setWorkflows] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [agentContainerId, setAgentContainerId]=useState(null);

  const globalContextValue = {
    user,
    role,
    setRole,
    loading,
    setLoading,
    error,
    setError,
    containerId,
    setContainerId,
    agentContainerId,
    setAgentContainerId,
    login,
    isAuthenticated,
    sidebarOpen,
    setSideBarOpen,
    logout,
    workflows,
    setWorkflows,
    notifications,
    setNotifications,
  };

  // Fetch workflows and notifications on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const workflowResponse = await fetchAllWorkflows();
        if (workflowResponse.status === "success" && workflowResponse.data) {
          setWorkflows(workflowResponse.data);
        }

        const previousNotifications = await fetchPreviousNotifications();
        setNotifications(previousNotifications);
      } catch (err) {
        console.error("Error loading workflows and notifications:", err);
        setError(err.message || "Failed to load data");
      }
    };

    loadData();
  }, []);

  return (
    <GlobalContext.Provider value={globalContextValue}>
      {children}
    </GlobalContext.Provider>
  );
};
