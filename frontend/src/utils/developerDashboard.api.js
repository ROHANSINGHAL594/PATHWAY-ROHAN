/**
 * Developer Dashboard API utilities
 * Page-specific functions for the developer dashboard
 */

export const fetchTemplates = async () => {
  // Real API call placeholder:
  // const response = await fetch('/api/templates');
  // const data = await response.json();
  // return data;

  return [
    { id: "custom", name: "Custom Workflow" },
    { id: "sales", name: "MDTR & Throughput" },
    { id: "proposal", name: "Latency Check" },
    { id: "invoice", name: "Crash Reports" },
  ];
};

import fetchWithAuth from "./api";

// Fetches a list of existing workflow files.
export const fetchWorkflows = async (skip = 0, limit = 3) => {
  const response = await fetchWithAuth(
    `/overview/workflows/?skip=${skip}&limit=${limit}`
  );
  const data = await response.json();
  return data;
};

// Create web - socket to fetch notifications and actions
export const fetchNotifications = async () => {
  const ws = new WebSocket(`${import.meta.env.VITE_WS_SERVER}/ws/pipeline/All`);

  // To test:
  // ws.onopen = () => {
  // console.log("Notifications WS connected");
  // };
  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
  return ws;
};

// Fetches overview statistics data.
export const fetchOverviewData = async () => {
  const response = await fetchWithAuth("/overview/kpi");
  const data = await response.json();
  return data;
};

// Fetches chart data for Admin dashboard
export const fetchChartsData = async () => {
  const response = await fetchWithAuth("/overview/charts");
  const data = await response.json();
  return data;
};

// Update notification with action taken
export const updateNotificationAction = async (notificationId, action) => {
  const response = await fetch(
    `${
      import.meta.env.VITE_API_SERVER
    }/overview/notifications/${notificationId}/action`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        action_taken: action,
        taken_at: new Date().toISOString(),
      }),
    }
  );

  const data = await response.json();
  return { ok: response.ok, data };
};

// Fetches all workflows from /version/retrieve_all
export const fetchAllWorkflows = async () => {
  const response = await fetch(
    `${import.meta.env.VITE_API_SERVER}/version/retrieve_all`,
    { credentials: "include" }
  );
  const data = await response.json();
  return data;
};

// Fetches previous notifications (placeholder - adjust based on actual endpoint)
export const fetchPreviousNotifications = async () => {
  // TODO: Replace with actual API endpoint when available
  // For now, return empty array
  return [];
};

// Fetch user details by user ID
export const fetchUserById = async (userId) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/auth/users/${userId}`,
      { credentials: "include" }
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch user: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Error fetching user ${userId}:`, error);
    // Return fallback data
    return {
      id: String(userId),
      email: `user${userId}@example.com`,
      full_name: `User ${userId}`,
      role: "user",
      is_active: true,
    };
  }
};

// Remove viewer from pipeline
export const removeViewerFromPipeline = async (pipelineId, userId) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/version/remove_viewer`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pipeline_id: pipelineId,
          user_id: userId,
        }),
      }
    );
    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "Failed to remove viewer" }));
      throw new Error(
        errorData.detail || `Failed to remove viewer: ${response.status}`
      );
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error removing viewer:", error);
    throw error;
  }
};

// Fetch all users
export const fetchAllUsers = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/auth/users`,
      { credentials: "include" }
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch users: ${response.status}`);
    }
    const data = await response.json();
    // The API returns an array directly, ensure we return it as-is
    if (Array.isArray(data)) {
      return data;
    }
    // If wrapped in an object, extract the array
    if (data.data && Array.isArray(data.data)) {
      return data.data;
    }
    console.warn("Unexpected API response format:", data);
    return [];
  } catch (error) {
    console.error("Error fetching users:", error);
    throw error;
  }
};

// Add viewer to pipeline
export const addViewerToPipeline = async (pipelineId, userId) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/version/add_viewer`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pipeline_id: pipelineId,
          user_id: userId,
        }),
      }
    );
    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "Failed to add viewer" }));
      throw new Error(
        errorData.detail || `Failed to add viewer: ${response.status}`
      );
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error adding viewer:", error);
    throw error;
  }
};


// Get current user details
export const getCurrentUser = async () => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_SERVER}/auth/me`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch user: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching current user:", error);
    throw error;
  }
};

// Retrieve pipeline to get workflow name
export const retrievePipeline = async (workflowId, versionId) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/version/retrieve_pipeline`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow_id: workflowId,
          version_id: versionId,
        }),
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to retrieve pipeline: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error retrieving pipeline:", error);
    throw error;
  }
};
