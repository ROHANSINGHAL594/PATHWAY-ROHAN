import React, { useState, useMemo, useEffect} from "react";
import {
  Box,
  Typography,
  Button,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Snackbar,
  Alert,
  useTheme,
} from "@mui/material";
import { useColorScheme } from "@mui/material/styles";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import IconifyIcon from "components/base/IconifyIcon";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import planeLight from "../../assets/plane_light.svg";
import planeDark from "../../assets/plane_dark.svg";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import PeopleIcon from "@mui/icons-material/People";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import EditIcon from "@mui/icons-material/Edit";
import { updateNotificationAction } from "../../utils/developerDashboard.api";
import { fetchPreviousNotifcations } from "../../utils/utils";
import { useGlobalState } from "../../context/GlobalStateContext";
import notif_dark from "../../assets/notif_dark.svg";
import notif_light from "../../assets/notif_light.svg";

dayjs.extend(relativeTime);

const HighlightsPanel = () => {
  const theme = useTheme();
  const { mode, systemMode } = useColorScheme();
  const resolvedMode = (mode === 'system' ? systemMode : mode) || theme.palette.mode;
  const isDark = resolvedMode === 'dark';
  const [anchorEl, setAnchorEl] = useState(null);
  const [sortBy, setSortBy] = useState("all");
  const [confirmDialog, setConfirmDialog] = useState({ open: false, notification: null, action: null });
  const [loadingAction, setLoadingAction] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: "", severity: "success" });
  // Use GlobalStateContext which already has real-time WebSocket notifications
  const { notifications, setNotifications, rcaEvents } = useGlobalState();

  const getIconStyle = (type) => {
    switch (type) {
      case "success":
        return {
          color: "success.dark",
          bgColor: "success.lighter",
          icon: "material-symbols:check-circle-outline",
          useIconify: true,
        };
      case "error":
        return {
          color: "error.dark",
          bgColor: "error.lighter",
          icon: ErrorOutlineIcon,
          useIconify: false,
        };
      case "warning":
        return {
          color: "warning.dark",
          bgColor: "warning.lighter",
          icon: WarningAmberIcon,
          useIconify: false,
        };
      case "alert":
        return {
          color: "secondary.dark",  
          bgColor: "secondary.lighter",
          icon: "mdi:bell-alert-outline",
          useIconify: true,
        };
      case "rca":
        return {
          color: "primary.dark",
          bgColor: "primary.lighter",
          icon: "mdi:magnify-scan",
          useIconify: true,
        };
      case "info":
      default:
        return {
          color: "info.dark",
          bgColor: "info.lighter",
          icon: ArrowForwardIcon,
          useIconify: false,
        };
    }
  };
  // Note: Previous notifications are now loaded by GlobalStateContext on mount
  // This effect is kept for backward compatibility but shouldn't be needed
  // The GlobalStateContext handles initial data loading


  // Get appropriate icon based on notification content
  const getNotificationIcon = (notification) => {
    // Check if it's a user access notification
    if (notification.desc?.toLowerCase().includes("got access") || 
        notification.desc?.toLowerCase().includes("access to")) {
      return {
        icon: PeopleIcon,
        useIconify: false,
        color: "info.dark",
        bgColor: "info.lighter",
      };
    }
    // Check if it's an action required notification
    if (notification.title?.toLowerCase().includes("action required") ||
        notification.type === "warning") {
      return {
        icon: EditIcon,
        useIconify: false,
        color: "warning.dark",
        bgColor: "warning.lighter",
      };
    }
    // Default to type-based icon
    return getIconStyle(notification.type);
  };

  // Format timestamp to relative time
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    try {
      // Handle both string and Date objects
      const date = typeof timestamp === "string" ? dayjs(timestamp) : dayjs(timestamp);
      return date.fromNow();
    } catch (error) {
      return timestamp;
    }
  };
  // Get chip color and styling based on notification_status using theme
  const getChipStyles = (status) => {
    switch (status?.toLowerCase()) {
      case "pending":
      case "due":
        return {
          bgcolor: theme.palette.warning.lighter,
          color: theme.palette.warning.darker,
          border: `1px solid ${theme.palette.warning.light}`,
          fontWeight: 600,
          boxShadow: theme.shadows[1],
        };
      case "resolved":
      case "active":
        return {
          bgcolor: theme.palette.success.lighter,
          color: theme.palette.success.darker,
          border: `1px solid ${theme.palette.success.light}`,
          fontWeight: 600,
          boxShadow: theme.shadows[1],
        };
      case "ignored":
        return {
          bgcolor: theme.palette.error.lighter,
          color: theme.palette.error.darker,
          border: `1px solid ${theme.palette.error.light}`,
          fontWeight: 600,
          boxShadow: theme.shadows[1],
        };
      default:
        return {
          bgcolor: theme.palette.grey[100],
          color: theme.palette.grey[700],
          border: `1px solid ${theme.palette.grey[300]}`,
          fontWeight: 500,
        };
    }
  };

  // Handle action button clicks with confirmation
  const handleActionClick = (notification, action) => {
    setConfirmDialog({ open: true, notification, action });
  };

  const handleConfirmAction = async () => {
    const { notification, action } = confirmDialog;
    setLoadingAction(notification._id);
    
try {
  if (!notification._id) {
    setSnackbar({
      open: true,
      message: "Notification ID not found",
      severity: "error",
    });
    return;
  }

  const { ok, data } = await updateNotificationAction(notification._id, action);

  setConfirmDialog({ open: false, notification: null, action: null });

    if (ok) {
      setSnackbar({
        open: true,
        message: `Successfully ${action.toLowerCase()}d the notification`,
        severity: "success",
      });

      const updatedList = await fetchPreviousNotifcations();
      setNotifications(updatedList);
    } else {
      setSnackbar({
        open: true,
        message: data?.detail || `Failed to ${action.toLowerCase()} the notification`,
        severity: "error",
      });
    }
  } catch (error) {
    setSnackbar({
      open: true,
      message: error.message || "Failed to take action. Please try again.",
      severity: "error",
    });
  } finally {
    setLoadingAction(null);
  }

  };

  const handleCloseSnackbar = (event, reason) => {
    if (reason === "clickaway") {
      return;
    }
    setSnackbar({ ...snackbar, open: false });
  };

  const handleCancelAction = () => {
    setConfirmDialog({ open: false, notification: null, action: null });
  };

  // Define sort order priority for notification types
  const typePriority = {
    error: 0,
    warning: 1,
    rca: 2,
    info: 3,
    success: 4,
    alert: 5
  };

  const handleSortClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleSortClose = () => {
    setAnchorEl(null);
  };

  const handleSortSelect = (sortOption) => {
    setSortBy(sortOption);
    handleSortClose();
  };

  // Helper function to get timestamp as Date for sorting
  const getTimestamp = (notification) => {
    if (!notification.timestamp) return new Date(0);
    return typeof notification.timestamp === "string" 
      ? new Date(notification.timestamp) 
      : new Date(notification.timestamp);
  };

  // Sort notifications based on selected option (always by time descending - most recent first)
  const enhancedNotifications = useMemo(() => {
    // Combine notifications with RCA events (add type="rca" to RCA events)
    const rcaWithType = (rcaEvents || []).map(rca => ({
      ...rca,
      type: "rca",
      // Map RCA fields to notification fields for display
      desc: rca.description || rca.desc,
      timestamp: rca.triggered_at || rca.timestamp,
    }));
    
    const allItems = [...(notifications || []), ...rcaWithType];
    
    if (allItems.length === 0) {
      return [];
    }

    let sorted = [...allItems];

    // Always sort by timestamp first (most recent on top)
    sorted.sort((a, b) => {
      const timeA = getTimestamp(a);
      const timeB = getTimestamp(b);
      return timeB - timeA; // Descending order (most recent first)
    });

    if (sortBy === "all") {
      return sorted;
    }

    else if (sortBy === "type") {
      // Group by type priority, but maintain time order within each group
      sorted.sort((a, b) => {
        const priorityA = typePriority[a.type] ?? 999;
        const priorityB = typePriority[b.type] ?? 999;
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }
        // Same type priority, sort by time (most recent first)
        return getTimestamp(b) - getTimestamp(a);
      });
    } else if (typePriority[sortBy] !== undefined) {
      // Sort by specific type - show that type first, then by time
      sorted.sort((a, b) => {
        if (a.type === sortBy && b.type !== sortBy) return -1;
        if (a.type !== sortBy && b.type === sortBy) return 1;
        // Same type category, sort by time (most recent first)
        return getTimestamp(b) - getTimestamp(a);
      });
    }

    else {
      sorted = allItems.filter(
        (notif) => notif.type === sortBy
      );
      // Also sort filtered results by time
      sorted.sort((a, b) => getTimestamp(b) - getTimestamp(a));
    }

    return sorted;
  }, [notifications, rcaEvents, sortBy]);

  return (
    <Box
      sx={{
        height: "100%",
        borderLeft: "1px solid",
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ p: theme.spacing(3) }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: theme.spacing(1),
          }}
        >
          <Typography
            variant="h6"
            fontWeight="700"
            sx={{ fontSize: theme.typography.h6.fontSize }}
          >
            Highlights
          </Typography>
          <Button
            variant="text"
            size="small"
            onClick={handleSortClick}
            sx={{
              textTransform: "none",
              color: "text.secondary",
              fontSize: theme.typography.body2.fontSize,
            }}
            endIcon={<ArrowDropDownIcon />}
          >
            Sort by
          </Button>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleSortClose}
            anchorOrigin={{
              vertical: "bottom",
              horizontal: "right",
            }}
            transformOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
          >
            {["all", "type", "error", "warning", "rca", "info", "success", "alert"].map((item) => (
              <MenuItem
                key={item}
                onClick={() => handleSortSelect(item)}
                selected={sortBy === item}
              >
                {item === "rca" ? "RCA" : item.charAt(0).toUpperCase() + item.slice(1)}
              </MenuItem>
            ))}
          </Menu>
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", p: theme.spacing(2) }}>
        {enhancedNotifications.length === 0 ? (
          <Box sx={{ textAlign: "center", py: "2rem", display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
            <Box
              component="img"
              src={isDark ? notif_dark : notif_light}
              alt="No highlights"
              sx={{
                width: { xs: "10rem", sm: "12rem" },
                height: "auto",
                opacity: 0.8,
              }}
            />
            <Typography color="text.secondary" sx={{ fontSize: "0.875rem" }}>
              No highlights to show
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{ display: "flex", flexDirection: "column", gap: theme.spacing(1.5) }}
          >
            {enhancedNotifications.map((notification, index) => {
              const iconStyle = getNotificationIcon(notification);
              const IconComponent = iconStyle.useIconify
                ? null
                : iconStyle.icon;
              const isAlert = notification.type === "alert";
              const hasActions = isAlert && 
                notification.alert?.actions && 
                notification.alert.actions.length > 0 &&
                !notification.alert?.action_taken;
              // Show status chip from alert.status
              const showStatusChip = notification.alert?.status;

              return (
                <Box
                  key={index}
                  sx={{
                    p: "1rem",
                    borderRadius: 2,
                    bgcolor: "background.elevation1",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                    transition: "all 0.2s",
                    "&:hover": {
                      bgcolor: "action.hover",
                      boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
                    },
                  }}
                >
                  <Box sx={{ display: "flex", gap: "0.75rem" }}>
                    <Box
                      sx={{
                        width: theme.spacing(5),
                        height: theme.spacing(5),
                        borderRadius: theme.shape.borderRadius * 2,
                        bgcolor: iconStyle.bgColor,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      {iconStyle.useIconify ? (
                        <IconifyIcon
                          icon={iconStyle.icon}
                          sx={{ color: iconStyle.color, fontSize: 24 }}
                        />
                      ) : (
                        <IconComponent
                          sx={{ color: iconStyle.color, fontSize: 24 }}
                        />
                      )}
                    </Box>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          mb: "0.25rem",
                        }}
                      >
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: "0.875rem",
                              color: "text.primary",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                            }}
                          >
                            {notification.title && (
                              <Box component="span" fontWeight="700">
                                {notification.title}
                              </Box>
                            )}
                            {notification.title && notification.desc && " "}
                            {notification.desc && (
                              <Box component="span">
                                {notification.desc}
                              </Box>
                            )}
                          </Typography>
                        </Box>
                        <IconButton
                          size="small"
                          sx={{ ml: "0.5rem", mt: "-0.25rem" }}
                        >
                          <MoreHorizIcon sx={{ fontSize: "1rem" }} />
                        </IconButton>
                      </Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block", mb: hasActions || showStatusChip || notification.alert?.action_taken ? 1 : 0 }}
                      >
                        {formatTimestamp(notification.timestamp)}
                      </Typography>
                      {hasActions && (
                        <Box 
                          sx={{ 
                            display: "flex", 
                            gap: "1rem", 
                            alignItems: "center", 
                            flexWrap: "wrap",
                            mb: showStatusChip || notification.alert?.action_taken ? 1 : 0 
                          }}
                        >
                          {notification.alert.actions.map((action, actionIndex) => {
                            const actionLower = action.toLowerCase();
                            const isPositive = actionLower.includes("activate") || 
                                              actionLower.includes("accept") || 
                                              actionLower.includes("approve") ||
                                              actionLower.includes("enable") ||
                                              actionLower.includes("allow");
                            const isNegative = actionLower.includes("deactivate") || 
                                              actionLower.includes("reject") || 
                                              actionLower.includes("deny") ||
                                              actionLower.includes("disable") ||
                                              actionLower.includes("decline");
                            const actionTaken = !!notification.alert?.action_taken;
                            
                            // Determine color based on action type
                            let actionColor = "#9E9E9E"; // Default gray for disabled
                            if (!actionTaken) {
                              if (isPositive) {
                                actionColor = "#1976D2"; // Blue for positive actions
                              } else if (isNegative) {
                                actionColor = "#D32F2F"; // Red for negative actions
                              } else {
                                actionColor = "#FF9800"; // Orange for intermediate actions
                              }
                            }
                            
                            return (
                              <Typography
                                key={actionIndex}
                                component="button"
                                onClick={() => !actionTaken && handleActionClick(notification, action)}
                                disabled={actionTaken}
                                sx={{
                                  fontSize: theme.typography.body2.fontSize,
                                  fontWeight: 700,
                                  textDecoration: "none",
                                  cursor: actionTaken ? "not-allowed" : "pointer",
                                  border: "none",
                                  background: "none",
                                  padding: 0,
                                  fontFamily: theme.typography.fontFamily,
                                  color: actionColor,
                                  opacity: actionTaken ? 0.5 : 1,
                                  transition: theme.transitions.create(["opacity", "transform"], {
                                    duration: theme.transitions.duration.standard,
                                    easing: theme.transitions.easing.easeInOut,
                                  }),
                                  "&:hover": {
                                    opacity: actionTaken ? 0.5 : 0.7,
                                    transform: actionTaken ? "none" : "scale(1.05)",
                                  },
                                  "&:active": {
                                    transform: "scale(0.98)",
                                  },
                                  "&:disabled": {
                                    color: theme.palette.action.disabled,
                                    cursor: "not-allowed",
                                  },
                                }}
                              >
                                {action}
                              </Typography>
                            );
                          })}
                        </Box>
                      )}
                      {notification.alert?.action_taken && (
                        <Typography
                          variant="caption"
                          sx={{ 
                            display: "block", 
                            mb: showStatusChip ? 1 : 0,
                            fontSize: theme.typography.caption.fontSize,
                            color: theme.palette.success.main,
                            fontWeight: 500,
                          }}
                        >
                          ✓ Action "{notification.alert.action_taken}" taken
                          {notification.action_executed_by_user && (
                            <> by {notification.action_executed_by_user.full_name || notification.action_executed_by_user.email}</>
                          )}
                        </Typography>
                      )}
                      {showStatusChip && (
                        <Chip
                          label={notification.alert.status}
                          size="small"
                          sx={{ 
                            height: "1.5rem",
                            fontSize: "0.75rem",
                            fontWeight: 500,
                            ...getChipStyles(notification.alert.status),
                          }}
                        />
                      )}
                    </Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}
      </Box>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={handleCancelAction}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">
          Confirm Action
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            Are you sure you want to <strong>{confirmDialog.action}</strong> for this notification?
            <br />
            <br />
            <Typography variant="body2" sx={{ fontStyle: "italic", color: "text.secondary" }}>
              {confirmDialog.notification?.title && (
                <>
                  <strong>{confirmDialog.notification.title}</strong>
                  {confirmDialog.notification.desc && ` - ${confirmDialog.notification.desc}`}
                </>
              )}
            </Typography>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelAction} color="inherit" disabled={loadingAction === confirmDialog.notification?._id}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirmAction} 
            color="primary" 
            variant="contained"
            disabled={loadingAction === confirmDialog.notification?._id}
            startIcon={loadingAction === confirmDialog.notification?._id ? <CircularProgress size={16} /> : null}
          >
            {loadingAction === confirmDialog.notification?._id ? "Processing..." : "Confirm"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default HighlightsPanel;
