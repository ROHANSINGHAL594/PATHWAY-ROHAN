/**
 * General system state utilities
 * Functions for fetching workflows, notifications, and logs
 */

// Fetches a list of existing workflow files.
export const fetchWorkflows = async (skip = 0, limit = 4) => {
  const response = await fetch(
    `${import.meta.env.VITE_API_SERVER}/version/retrieve_all?skip=${skip}&limit=${limit}`,
    { credentials: "include" }
  );

  if (!response.ok) {
    throw new Error("Failed to fetch workflows");
  }

  return await response.json();
};

// Fetches previous notifications from the API
export const fetchPreviousNotifcations = async () => {
  try {
    const apiUrl = `${import.meta.env.VITE_API_SERVER}/overview/notifications`;    
    const response = await fetch(apiUrl, { credentials: "include" });
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ Failed to fetch notifications: ${response.status} ${response.statusText}`, errorText);
      return [];
    }
    
      const data = await response.json();
    if (data && typeof data === 'object') {
      if (data.data !== undefined) {
        if (Array.isArray(data.data)) {
          console.log(`✅ API returned ${data.data.length} notifications in data.data`);
          return data.data;
        } else {
          console.warn("⚠️ data.data exists but is not an array:", data.data);
          return [];
        }
      } else if (Array.isArray(data)) {
        console.log(`✅ API returned ${data.length} notifications as direct array`);
        return data;
      } else {
        console.warn("⚠️ Unexpected notification response format - no data.data or array:", data);
        return [];
      }
    } else {
      console.warn("⚠️ Unexpected notification response - not an object:", typeof data, data);
      return [];
    }
  } catch (error) {
    console.error("❌ Error fetching previous notifications:", error);
    console.error("Error details:", error.message, error.stack);
    return [];
  }
};

// Fetches logs from the API
export const fetchLogs = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/overview/logs`,
      { credentials: "include" }
    );
    const data = await response.json();
    if (data && data.status === "success" && data.data) {
      console.log(`✅ API returned ${data.data.length} logs`);
      return data.data;
    } else if (Array.isArray(data)) {
      return data;
    } else {
      console.warn("⚠️ Unexpected logs response format:", data);
      return [];
    }
  } catch (error) {
    console.error("❌ Error fetching logs:", error);
    return [];
  }
};

// Fetches RCA events from the API
export const fetchRcaEvents = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_SERVER}/rca/rca_events`,
      { credentials: "include" }
    );
    const data = await response.json();
    if (data && data.status === "success" && data.data) {
      console.log(`✅ API returned ${data.data.length} RCA events`);
      return data.data;
    } else if (Array.isArray(data)) {
      return data;
    } else {
      console.warn("⚠️ Unexpected RCA events response format:", data);
      return [];
    }
  } catch (error) {
    console.error("❌ Error fetching RCA events:", error);
    return [];
  }
};

