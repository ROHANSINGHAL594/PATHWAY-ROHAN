import { Box, Typography, Button, IconButton, useTheme } from "@mui/material";
import { useState } from "react";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import planeLight from "../../assets/plane_light.svg";
import planeDark from "../../assets/plane_dark.svg";
import ApprovalDialog from "../ApprovalDialog";
import { useGlobalWorkflow } from "../../context/GlobalWorkflowContext";
dayjs.extend(relativeTime);

const ActionRequired = ({
  actionFilter,
  onFilterChange,
  notifications = [],
}) => {
  const theme = useTheme();
  const { id: currentPipelineId } = useGlobalWorkflow();
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);

  // Format notification for display
  const formatNotification = (n) => {
    return {
      id: n._id || n.id,
      title: n.title || n.desc || "Notification",
      description: n.desc || n.title || "",
      type: n.type,
      timestamp: n.timestamp,
      timeAgo: n.timestamp ? dayjs(n.timestamp).fromNow() : "Unknown",
      action_taken: n.alert?.action_taken,
      action_executed_by: n.alert?.action_executed_by,
      action_executed_by_user: n.action_executed_by_user,
      email: n.action_executed_by_user?.email,
      assignee: n.action_executed_by_user
        ? `Action taken by ${
            n.action_executed_by_user.full_name ||
            n.action_executed_by_user.email
          }`
        : undefined,
      // Include original notification for approval dialog
      originalNotification: n,
      // Check if this is an approval request
      isApprovalRequest: n.data?.type === "approval_request" || n.type === "approval_request",
    };
  };

  const filteredNotifications = notifications.map(formatNotification);

  const handleApproveClick = (notification) => {
    setSelectedNotification(notification.originalNotification);
    setApprovalDialogOpen(true);
  };

  const handleRejectClick = (notification) => {
    setSelectedNotification(notification.originalNotification);
    setApprovalDialogOpen(true);
  };

  const handleApprovalDialogClose = () => {
    setApprovalDialogOpen(false);
    setSelectedNotification(null);
  };

  const handleApprovalSuccess = (requestId, actionId, approvedBy) => {
    console.log(`Approval successful for request ${requestId}`, { actionId, approvedBy });
    // Optionally refresh notifications or update UI
  };

  const handleRejectionSuccess = (requestId, actionId, rejectedBy, reason) => {
    console.log(`Rejection successful for request ${requestId}`, { actionId, rejectedBy, reason });
    // Optionally refresh notifications or update UI
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 0,
        borderTop: "none",
        overflow: "hidden",
      }}
    >
      <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        <Typography
          variant="h6"
          sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "text.primary" }}
        >
          Action Required
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Button
            size="small"
            variant={actionFilter === "notifications" ? "soft" : "text"}
            color="neutral"
            onClick={() => onFilterChange("notifications")}
            sx={{
              minWidth: "auto",
              border: "none",
              "&:hover": {
                border: "none",
              },
            }}
          >
            Notifications
          </Button>
          <Button
            size="small"
            variant={actionFilter === "pending_actions" ? "soft" : "text"}
            color="neutral"
            onClick={() => onFilterChange("pending_actions")}
            sx={{
              minWidth: "auto",
              border: "none",
              "&:hover": {
                border: "none",
              },
            }}
          >
            Pending Actions
          </Button>
          <Button
            size="small"
            variant={actionFilter === "actions_taken" ? "soft" : "text"}
            color="neutral"
            onClick={() => onFilterChange("actions_taken")}
            sx={{
              minWidth: "auto",
              border: "none",
              "&:hover": {
                border: "none",
              },
            }}
          >
            Actions Taken
          </Button>
        </Box>
      </Box>
      <Box
        sx={{
          flex: 1,
          px: 2,
          pt: 1,
          pb: 3,
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {filteredNotifications.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                py: 4,
              }}
            >
              <Box
                component="img"
                src={theme.palette.mode === "dark" ? planeDark : planeLight}
                alt="No data"
                sx={{ width: "8rem", height: "auto", opacity: 0.6 }}
              />
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontSize: "0.875rem", mt: 2 }}
              >
                No{" "}
                {actionFilter === "notifications"
                  ? "notifications found"
                  : actionFilter === "pending_actions"
                  ? "actions pending"
                  : "actions taken yet"}
              </Typography>
            </Box>
          ) : (
            filteredNotifications.map((item) => (
              <Box
                key={item.id}
                sx={{
                  p: "1rem",
                  borderRadius: 2,
                  bgcolor: "background.elevation1",
                  transition: "all 0.2s",
                  "&:hover": {
                    bgcolor: "action.hover",
                  },
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    mb: 0.75,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: "0.8125rem",
                      color: "text.primary",
                      flex: 1,
                    }}
                  >
                    {item.title}
                  </Typography>
                  <IconButton
                    size="small"
                    sx={{
                      ml: 1,
                      p: 0.5,
                      color: "primary.main",
                      bgcolor: "rgba(25, 118, 210, 0.08)",
                      width: 28,
                      height: 28,
                      "&:hover": {
                        bgcolor: "rgba(25, 118, 210, 0.16)",
                      },
                    }}
                  >
                    <AutoAwesomeOutlinedIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </Box>
                {item.email && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: "0.75rem",
                      display: "block",
                      mb: 0.5,
                    }}
                  >
                    {item.email}
                  </Typography>
                )}
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.secondary",
                    fontSize: "0.6875rem",
                    display: "block",
                    mb: 1,
                  }}
                >
                  {item.assignee || item.timeAgo}
                </Typography>
                {item.type === "alert" &&
                  actionFilter === "pending_actions" && (
                    <Box sx={{ display: "flex", gap: 1.5 }}>
                      <Button
                        size="small"
                        variant="text"
                        onClick={() => handleApproveClick(item)}
                        sx={{
                          minWidth: "auto",
                          px: 1.5,
                          py: 0.5,
                          color: "primary.main",
                          fontSize: "0.75rem",
                          fontWeight: 500,
                          textTransform: "none",
                          "&:hover": {
                            bgcolor: "action.hover",
                          },
                        }}
                      >
                        Approve
                      </Button>
                      <Button
                        size="small"
                        variant="text"
                        onClick={() => handleRejectClick(item)}
                        sx={{
                          minWidth: "auto",
                          px: 1.5,
                          py: 0.5,
                          color: "error.main",
                          fontSize: "0.75rem",
                          fontWeight: 500,
                          textTransform: "none",
                          "&:hover": {
                            bgcolor:
                              theme.palette.mode === "dark"
                                ? "rgba(211, 47, 47, 0.16)"
                                : "rgba(211, 47, 47, 0.08)",
                          },
                        }}
                      >
                        Reject
                      </Button>
                    </Box>
                  )}
              </Box>
            ))
          )}
        </Box>
      </Box>

      {/* Approval Dialog */}
      <ApprovalDialog
        open={approvalDialogOpen}
        onClose={handleApprovalDialogClose}
        notification={selectedNotification}
        pipelineId={currentPipelineId}
        onApprove={handleApprovalSuccess}
        onReject={handleRejectionSuccess}
      />
    </Box>
  );
};

export default ActionRequired;
