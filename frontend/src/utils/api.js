/**
 * API utility with automatic token refresh
 * Intercepts fetch requests and automatically refreshes access token on 401 errors
 */

const API_SERVER = import.meta.env.VITE_API_SERVER;
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Fetch wrapper with automatic token refresh
 * @param {string} url - API endpoint (without base URL)
 * @param {object} options - Fetch options
 * @returns {Promise<Response>}
 */
const fetchWithAuth = async (url, options = {}) => {
  // First attempt
  let response = await fetch(`${API_SERVER}${url}`, {
    ...options,
    credentials: "include",
    headers: {
      ...options.headers,
      "Content-Type":
        options.headers?.["Content-Type"] ||
        (options.body && typeof options.body === "string"
          ? "application/json"
          : options.headers?.["Content-Type"] || "application/x-www-form-urlencoded"),
    },
  });

  // If 401, try to refresh token (skip auth endpoints to avoid infinite loops)
  if (response.status === 401 && !url.includes("/auth/")) {
    if (isRefreshing) {
      // Wait for ongoing refresh
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then(() => {
          // Retry original request after refresh
          return fetch(`${API_SERVER}${url}`, {
            ...options,
            credentials: "include",
            headers: {
              ...options.headers,
              "Content-Type":
                options.headers?.["Content-Type"] ||
                (options.body && typeof options.body === "string"
                  ? "application/json"
                  : options.headers?.["Content-Type"] || "application/x-www-form-urlencoded"),
            },
          });
        })
        .catch((err) => {
          throw err;
        });
    }

    isRefreshing = true;

    try {
      const refreshResponse = await fetch(`${API_SERVER}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (refreshResponse.ok) {
        processQueue(null, null);
        // Retry original request
        response = await fetch(`${API_SERVER}${url}`, {
          ...options,
          credentials: "include",
          headers: {
            ...options.headers,
            "Content-Type":
              options.headers?.["Content-Type"] ||
              (options.body && typeof options.body === "string"
                ? "application/json"
                : options.headers?.["Content-Type"] || "application/x-www-form-urlencoded"),
          },
        });
      } else {
        // Refresh failed, redirect to login
        processQueue(new Error("Refresh failed"), null);
        // Only redirect if we're not already on login/signup
        if (!window.location.pathname.includes("/login") && !window.location.pathname.includes("/signup")) {
          window.location.href = "/login";
        }
        throw new Error("Session expired");
      }
    } catch (error) {
      processQueue(error, null);
      // Only redirect if we're not already on login/signup
      if (!window.location.pathname.includes("/login") && !window.location.pathname.includes("/signup")) {
        window.location.href = "/login";
      }
      throw error;
    } finally {
      isRefreshing = false;
    }
  }

  return response;
};

export default fetchWithAuth;

