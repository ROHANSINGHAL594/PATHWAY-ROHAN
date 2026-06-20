import { useEffect, useRef, useState, createContext, useContext } from 'react';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Box, IconButton, Badge, Menu, Typography, Divider, List, ListItem, ListItemText, ListItemIcon, MenuItem, useTheme } from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import { useGlobalContext } from '../../context/GlobalContext';

// Notification Context
const NotificationContext = createContext();

// Notification Provider Component
export const NotificationProvider = ({ children }) => {
  const { currentPipelineId, currentPipelineStatus, isAuthenticated } = useGlobalContext();
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const lastPipelineIdRef = useRef(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const handleNotification = (data) => {
    
    const notification = {
      id: data.id || data._id || Date.now() + Math.random(),
      title: data.title || 'Notification',
      message: data.desc || data.description || data.message || data.body || '',
      type: data.type || 'info',
      timestamp: data.timestamp || new Date(),
      read: false,
      ...data,
    };


    // Add to notifications list
    setNotifications((prev) => {
      const updated = [notification, ...prev];
      return updated;
    });
    setUnreadCount((prev) => {
      const newCount = prev + 1;
      return newCount;
    });

    // Show toast notification
    const toastOptions = {
      position: 'top-right',
      autoClose: data.autoClose || 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    };

    switch (notification.type) {
      case 'success':
        toast.success(
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {notification.title}
            </Typography>
            <Typography variant="body2">{notification.message}</Typography>
          </Box>,
          toastOptions
        );
        break;
      case 'error':
        toast.error(
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {notification.title}
            </Typography>
            <Typography variant="body2">{notification.message}</Typography>
          </Box>,
          toastOptions
        );
        break;
      case 'warning':
        toast.warning(
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {notification.title}
            </Typography>
            <Typography variant="body2">{notification.message}</Typography>
          </Box>,
          toastOptions
        );
        break;
      case 'rca':
        toast.info(
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {notification.title}
            </Typography>
            <Typography variant="body2">{notification.message}</Typography>
            {notification.metadata?.severity && (
              <Typography variant="caption" sx={{ color: notification.metadata.severity === 'critical' ? '#ef4444' : notification.metadata.severity === 'high' ? '#f59e0b' : '#3b82f6' }}>
                Severity: {notification.metadata.severity}
              </Typography>
            )}
          </Box>,
          { ...toastOptions, autoClose: 8000 }
        );
        break;
      default:
        toast.info(
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {notification.title}
            </Typography>
            <Typography variant="body2">{notification.message}</Typography>
          </Box>,
          toastOptions
        );
    }
  };

  const connectWebSocket = () => {
    // Only connect if user is authenticated
    if (!isAuthenticated) {
      return;
    }

    const fallbackPipelineId = import.meta.env.VITE_NOTIFICATION_FALLBACK_PIPELINE || null;

    // Use the active workflow pipeline when available, otherwise fall back to the configured ID (if any)
    const effectivePipelineId = currentPipelineId || fallbackPipelineId;

    if (!effectivePipelineId) {
      console.warn('⚠️ No pipeline ID available for notifications.');
      return;
    }

    if (socketRef.current) {
      const readyState = socketRef.current.readyState;
      const isSamePipeline = lastPipelineIdRef.current === effectivePipelineId;
      if (
        isSamePipeline &&
        (readyState === WebSocket.OPEN || readyState === WebSocket.CONNECTING)
      ) {
        console.log('ℹ️ Existing WebSocket connection active; skipping reconnect.');
        return;
      }
      try {
        socketRef.current.close();
      } catch (closeError) {
        console.warn('⚠️ Error closing previous WebSocket connection:', closeError);
      }
      socketRef.current = null;
    }
    
    // Don't reconnect if already connected
    // if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
    //   return;
    // }

    // // Close existing connection if any
    // if (socketRef.current) {
    //   socketRef.current.close();
    //   socketRef.current = null;
    // }

    const BASE_URL = import.meta.env.VITE_WS_SERVER || 'ws://localhost:8081';
    const WS_URL = `${BASE_URL}/ws/alerts/${effectivePipelineId}`;
    
    try {
      
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;
      lastPipelineIdRef.current = effectivePipelineId;
      
      console.log('   WebSocket object created, readyState:', ws.readyState);

      ws.onopen = () => {
        console.log('✅ WebSocket CONNECTED!');
        console.log('   URL:', WS_URL);
        console.log('   ReadyState:', ws.readyState);
        setIsConnected(true);
        // toast.success('Notifications connected', {
        //   position: 'top-right',
        //   autoClose: 2000,
        //   hideProgressBar: true,
        // });
      };

      ws.onclose = (event) => {
        console.log('❌ WebSocket DISCONNECTED');
        console.log('   Code:', event.code);
        console.log('   Reason:', event.reason);
        console.log('   Was Clean:', event.wasClean);
        setIsConnected(false);
        socketRef.current = null;
        
        // Attempt to reconnect after 3 seconds if authenticated
        if (isAuthenticated) {
          console.log('   Will attempt reconnect in 3 seconds...');
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('🔄 Attempting to reconnect...');
            connectWebSocket();
          }, 3000);
        }
      };

      ws.onerror = (error) => {
        console.error('⚠️ WebSocket ERROR:', error);
        console.log('   ReadyState:', ws.readyState);
        console.log('   URL:', WS_URL);
        setIsConnected(false);
      };

      ws.onmessage = (event) => {
        console.log('📨 WebSocket MESSAGE received:', event.data);
        try {
          const data = JSON.parse(event.data);
          console.log('   Parsed data:', data);
          
          // Handle different message types
          if (data.type === 'connection') {
            // Connection confirmation message, don't show as notification
            console.log('✅ Connection confirmed:', data.message);
          } else if (data.message_type === 'rca' || data.type === 'rca') {
            // Handle RCA events - show toast notification with RCA type
            console.log('   Handling RCA event');
            handleNotification({
              ...data,
              title: data.title || 'RCA Analysis',
              message: data.description || data.desc || 'Root cause analysis triggered',
              type: 'rca',
            });
          } else {
            // Regular notification (not RCA)
            console.log('   Handling as notification');
            handleNotification(data);
          }
        } catch (error) {
          console.error('   Error parsing WebSocket message:', error);
          // Try to handle as plain text
          handleNotification({
            title: 'Notification',
            message: event.data,
            type: 'info',
          });
        }
      };

    } catch (error) {
      console.error('❌ Error creating WebSocket connection:', error);
      setIsConnected(false);
    }
  };

  useEffect(() => {
    // Only connect if user is authenticated
    if (!isAuthenticated) {
      // Clear notifications when logged out
      setNotifications([]);
      setUnreadCount(0);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    // Connect to WebSocket (will skip if no pipeline ID is available)
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [isAuthenticated, currentPipelineId, currentPipelineStatus]);

  const markAsRead = (notificationId) => {
    setNotifications((prev) =>
      prev.map((notif) =>
        notif.id === notificationId ? { ...notif, read: true } : notif
      )
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const markAllAsRead = () => {
    setNotifications((prev) =>
      prev.map((notif) => ({ ...notif, read: true }))
    );
    setUnreadCount(0);
  };

  const clearAll = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  const value = {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    markAllAsRead,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

// Hook to use notification context
export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

// Notification Icon Button Component
export const NotificationIcon = () => {
  const [anchorEl, setAnchorEl] = useState(null);
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearAll,
  } = useNotifications();

  console.log('🔔 NotificationIcon render - notifications:', notifications.length, 'unread:', unreadCount);

  const handleMenuOpen = (event) => {
    console.log('📂 Opening notification menu');
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNotificationClick = (notificationId) => {
    markAsRead(notificationId);
  };

  const handleMarkAllAsRead = () => {
    markAllAsRead();
  };

  const handleClearAll = () => {
    clearAll();
    handleMenuClose();
  };

  const open = Boolean(anchorEl);

  return (
    <>
      <IconButton
        onClick={handleMenuOpen}
        aria-label="notifications"
        sx={{
          ml: 1,
          color: (theme) => theme.palette.primary.main,
          outline: "none",
          border: "none",
          boxShadow: "none",
          "&:focus": { outline: "none" },
          "&:active": { outline: "none" },
          "&:hover": { backgroundColor: "transparent" },
        }}
      >
        <Badge
          badgeContent={unreadCount}
          color="error"
          sx={{
            "& .MuiBadge-badge": {
              fontSize: "0.75rem",
              height: 18,
              minWidth: 18,
            },
          }}
        >
          <NotificationsIcon color="inherit" />
        </Badge>
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            width: 400,
            maxWidth: '90vw',
            maxHeight: 500,
            mt: 1.5,
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">
            Notifications
          </Typography>
          <Box>
            {unreadCount > 0 && (
              <IconButton
                size="small"
                onClick={handleMarkAllAsRead}
                sx={{ mr: 1 }}
                title="Mark all as read"
              >
                <Typography variant="caption" color="primary">
                  Mark all read
                </Typography>
              </IconButton>
            )}
            {notifications.length > 0 && (
              <IconButton
                size="small"
                onClick={handleClearAll}
                title="Clear all"
              >
                <Typography variant="caption" color="error">
                  Clear
                </Typography>
              </IconButton>
            )}
          </Box>
        </Box>
        <Divider />
        <List sx={{ maxHeight: 400, overflow: 'auto', p: 0 }}>
          {notifications.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No notifications"
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'text.secondary',
                  align: 'center',
                }}
              />
            </ListItem>
          ) : (
            notifications.map((notification) => (
              <MenuItem
                key={notification.id}
                onClick={() => handleNotificationClick(notification.id)}
                sx={{
                  backgroundColor: notification.read ? 'transparent' : 'action.hover',
                  borderLeft: `3px solid ${
                    notification.type === 'success'
                      ? '#10b981'  // green - matches LogsSection
                      : notification.type === 'error' || notification.type === 'critical'
                      ? '#ef4444'  // red - matches LogsSection error
                      : notification.type === 'warning'
                      ? '#f59e0b'  // amber - matches LogsSection warning
                      : notification.type === 'rca'
                      ? '#8b5cf6'  // purple - RCA events
                      : notification.type === 'debug'
                      ? '#6b7280'  // gray - matches LogsSection debug
                      : '#3b82f6'  // blue - matches LogsSection info
                  }`,
                  py: 1.5,
                  px: 2,
                }}
              >
                <ListItemIcon sx={{ minWidth: 24, mr: 1 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor:
                        notification.type === 'success'
                          ? '#10b981'  // green
                          : notification.type === 'error' || notification.type === 'critical'
                          ? '#ef4444'  // red
                          : notification.type === 'warning'
                          ? '#f59e0b'  // amber
                          : notification.type === 'rca'
                          ? '#8b5cf6'  // purple - RCA events
                          : notification.type === 'debug'
                          ? '#6b7280'  // gray
                          : '#3b82f6',  // blue
                      opacity: notification.read ? 0.5 : 1,
                    }}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={notification.title}
                  secondary={
                    <>
                      {notification.message}
                      <br />
                      <span style={{ fontSize: '0.75rem' }}>
                        {notification.timestamp.toLocaleTimeString()}
                      </span>
                    </>
                  }
                  primaryTypographyProps={{
                    variant: 'subtitle2',
                    fontWeight: notification.read ? 'normal' : 'bold',
                  }}
                  secondaryTypographyProps={{
                    variant: 'body2',
                    color: 'text.secondary',
                    component: 'span',
                  }}
                />
              </MenuItem>
            ))
          )}
        </List>
      </Menu>
    </>
  );
};

// Toast Container Component (should be added to ProtectedRoute)
export const NotificationToastContainer = () => {
  const theme = useTheme();
  
  return (
    <>
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={true}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
        style={{ 
          marginTop: '64px',
          fontFamily: theme.typography.fontFamily,
        }}
        toastClassName="custom-toast"
        bodyClassName="custom-toast-body"
        progressClassName="custom-toast-progress"
      />
      <style>{`
        .custom-toast {
          border-radius: ${theme.shape.borderRadius}px !important;
          font-family: ${theme.typography.fontFamily} !important;
          background-color: ${theme.palette.background.paper} !important;
          color: ${theme.palette.text.primary} !important;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
          border: 1px solid ${theme.palette.divider} !important;
          min-height: 64px !important;
        }
        .custom-toast-body {
          font-family: ${theme.typography.fontFamily} !important;
          padding: 12px 16px !important;
        }
        .custom-toast-progress {
          background: linear-gradient(to right, ${theme.palette.primary.main}, ${theme.palette.secondary.main}) !important;
        }
        .Toastify__toast--success {
          border-left: 4px solid #10b981 !important; /* green - matches LogsSection */
        }
        .Toastify__toast--error {
          border-left: 4px solid #ef4444 !important; /* red - matches LogsSection error */
        }
        .Toastify__toast--warning {
          border-left: 4px solid #f59e0b !important; /* amber - matches LogsSection warning */
        }
        .Toastify__toast--info {
          border-left: 4px solid #3b82f6 !important; /* blue - matches LogsSection info */
        }
        .Toastify__close-button {
          color: ${theme.palette.text.secondary} !important;
          opacity: 0.7 !important;
        }
        .Toastify__close-button:hover {
          opacity: 1 !important;
        }
      `}</style>
    </>
  );
};

// Default export for backward compatibility
const NotificationComponent = () => {
  return (
    <>
      <NotificationIcon />
      <NotificationToastContainer />
    </>
  );
};

export default NotificationComponent;