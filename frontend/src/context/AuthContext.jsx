import React, { createContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Loading from "../components/common/Loading";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        let res = await fetch(`${import.meta.env.VITE_API_SERVER}/auth/me`, {
          method: "GET",
          credentials: "include",
        });

        // If 401, try to refresh token
        if (res.status === 401) {
          const refreshRes = await fetch(`${import.meta.env.VITE_API_SERVER}/auth/refresh`, {
            method: "POST",
            credentials: "include",
          });

          if (refreshRes.ok) {
            // Retry /me after refresh
            res = await fetch(`${import.meta.env.VITE_API_SERVER}/auth/me`, {
              method: "GET",
              credentials: "include",
            });
          }
        }

        if (res.ok) {
          const data = await res.json();
          setUser(data);
        } else {
          setUser(null);
        }
      } catch (err) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);


  // Login: just update state and redirect; backend sets HttpOnly cookies
  const login = async (data) => {
    setUser(data);
    navigate("/overview");
  };

  // Logout: call backend to delete cookies
  const logout = async () => {
    try {
      await fetch(`${import.meta.env.VITE_API_SERVER}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      console.error(err);
    } finally {
      setUser(null);
      navigate("/login");
    }
  };

  const isAuthenticated = !!user;

  if (loading) {
    return <Loading />;
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
