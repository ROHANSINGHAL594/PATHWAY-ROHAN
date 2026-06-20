import {
  Box,
  Typography,
  AvatarGroup,
  Avatar,
  IconButton,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  Chip,
  alpha,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FileCopyIcon from "@mui/icons-material/FileCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import DescriptionIcon from "@mui/icons-material/Description";
import CloseIcon from "@mui/icons-material/Close";
import Markdown from "react-markdown";
import PipelinePreview from "./PipelinePreview";
import MetricCard from "./MetricCard";
import ActionRequired from "./ActionRequired";
import LogsSection from "./LogsSection";
import { useWebSocket } from "../../context/WebSocketContext";
import { useGlobalState } from "../../context/GlobalStateContext";
import { useEffect, useState, useMemo } from "react";
import { fetchPipelineDetails } from "../../utils/pipelineUtils";
import Loading from "../common/Loading";
import planeLight from "../../assets/plane_light.svg";
import planeDark from "../../assets/plane_dark.svg";

const WorkflowDetails = ({
  workflow,
  actionFilter,
  onActionFilterChange,
  logs,
}) => {
  const theme = useTheme();
  const { getAlertsForPipeline, alerts: allAlerts } = useWebSocket();
  const { notifications } = useGlobalState();
  const [workflowAlerts, setWorkflowAlerts] = useState([]);
  const [pipelineDetails, setPipelineDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState(null);
  
  // Report menu state
  const [reportMenuAnchor, setReportMenuAnchor] = useState(null);
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [viewingReport, setViewingReport] = useState(null);
  
  // Report dialog state
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportContent, setReportContent] = useState("");
  const [reportMetadata, setReportMetadata] = useState(null);

  // Handle report menu open
  const handleReportMenuOpen = async (event) => {
    setReportMenuAnchor(event.currentTarget);
    if (!workflow?.id) return;
    
    setLoadingReports(true);
    try {
      const workflowId = String(workflow.id || workflow._id);
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${workflowId}/reports/list`,
        { credentials: "include" }
      );
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
      } else {
        console.error("Failed to fetch reports:", response.statusText);
        setReports([]);
      }
    } catch (error) {
      console.error("Error fetching reports:", error);
      setReports([]);
    } finally {
      setLoadingReports(false);
    }
  };

  // Handle report menu close
  const handleReportMenuClose = () => {
    setReportMenuAnchor(null);
  };

  // Handle report view - opens markdown in dialog
  const handleViewReport = async (reportId) => {
    if (!workflow?.id) return;
    
    setViewingReport(reportId);
    try {
      const workflowId = String(workflow.id || workflow._id);
      const response = await fetch(
        `${import.meta.env.VITE_API_SERVER}/agentic/${workflowId}/reports/${reportId}`,
        { credentials: "include" }
      );
      
      if (response.ok) {
        const data = await response.json();
        setReportContent(data.content || "");
        setReportMetadata({ ...data.metadata, report_id: reportId });
        setReportDialogOpen(true);
      } else {
        console.error("Failed to fetch report:", response.statusText);
      }
    } catch (error) {
      console.error("Error viewing report:", error);
    } finally {
      setViewingReport(null);
      handleReportMenuClose();
    }
  };

  // Handle report dialog close
  const handleReportDialogClose = () => {
    setReportDialogOpen(false);
    setReportContent("");
    setReportMetadata(null);
  };

  // Get severity color for chip
  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case "critical":
        return "error";
      case "high":
        return "warning";
      case "medium":
        return "info";
      case "low":
        return "success";
      default:
        return "default";
    }
  };

  // Filter notifications for this pipeline based on the selected filter
  const filteredNotifications = useMemo(() => {
    if (!workflow?.id || !notifications || notifications.length === 0) {
      return [];
    }

    const workflowId = String(workflow.id || workflow._id);
    
    // Filter notifications for this pipeline
    const pipelineNotifications = notifications.filter((notification) => {
      return String(notification?.pipeline_id || "") === workflowId;
    });

    // Apply filter based on actionFilter
    switch (actionFilter) {
      case "notifications":
        return pipelineNotifications.filter((n) => n?.type !== "alert");
      
      case "pending_actions":
        return pipelineNotifications.filter((n) => {
          if (n.type !== "alert") return false;
          const actionTaken = n.alert?.action_taken;
          return (
            !actionTaken ||
            actionTaken === "" ||
            actionTaken === null ||
            actionTaken === undefined
          );
        });
      
      case "actions_taken":
        return pipelineNotifications.filter((n) => {
          if (n.type !== "alert") return false;
          const actionTaken = n.alert?.action_taken;
          return (
            actionTaken &&
            actionTaken !== "" &&
            actionTaken !== null &&
            actionTaken !== undefined
          );
        });
      
      default:
        return pipelineNotifications;
    }
  }, [workflow?.id, notifications, actionFilter]);

  // Fetch pipeline details when workflow is selected
  useEffect(() => {
    const loadPipelineDetails = async () => {
      if (!workflow?.id) {
        setPipelineDetails(null);
        return;
      }
      try {
        setLoadingDetails(true);
        setDetailsError(null);
        // Ensure workflow.id is converted to string
        const workflowId = typeof workflow.id === 'string' ? workflow.id : String(workflow.id || workflow._id || '');
        if (!workflowId || workflowId === '[object Object]') {
          throw new Error('Invalid workflow ID');
        }
        const details = await fetchPipelineDetails(workflowId);
        if (details.status === "success") {
          setPipelineDetails(details);
        }
      } catch (err) {
        setDetailsError(err.message || "Failed to load pipeline details");
      } finally {
        setLoadingDetails(false);
      }
    };

    loadPipelineDetails();
  }, [workflow?.id]);

  // Update alerts when workflow changes or WebSocket receives new data
  useEffect(() => {
    if (workflow?.id) {
      const alerts = getAlertsForPipeline(workflow.id);
      setWorkflowAlerts(alerts);
    } else {
      setWorkflowAlerts([]);
    }
  }, [allAlerts, workflow?.id, getAlertsForPipeline]);

  // Update pipeline details when alerts change via WebSocket
  useEffect(() => {
    if (pipelineDetails && workflow?.id) {
      const currentAlerts = getAlertsForPipeline(workflow.id);
      // Update alerts count if it changed
      if (currentAlerts.length !== (pipelineDetails.alerts_count || 0)) {
        setPipelineDetails((prev) => ({
          ...prev,
          alerts_count: currentAlerts.length,
          alerts: currentAlerts,
        }));
      }
    }
  }, [allAlerts.length, pipelineDetails, workflow?.id, getAlertsForPipeline]);
  // Format total running time from seconds to human readable format
  const formatRunningTime = (seconds) => {
    if (!seconds || seconds === 0) return "0 min";
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  // Calculate %time run = (total_runtime / (date.now - create_time)) * 100
  const calculateTimeRunPercentage = () => {
    if (!workflow) return "0%";
    
    const totalRuntime = workflow.runtime || 0; // in seconds
    // Use created_at from pipeline details API (first version_created_at) if available
    const createTime =
      pipelineDetails?.created_at ||
                      workflow.created_at || 
                      workflow.user_pipeline_version?.version_created_at || 
                      workflow.last_updated;
    
    if (!createTime) return "0%";
    
    const now = new Date();
    const created = new Date(createTime);
    const timeSinceCreation = (now - created) / 1000; // Convert to seconds
    
    if (timeSinceCreation <= 0) return "0%";
    
    const percentage = (totalRuntime / timeSinceCreation) * 100;
    return `${percentage.toFixed(2)}%`;
  };

  // Get alerts count from pipeline details or WebSocket
  const getAlertsCount = () => {
    if (workflowAlerts.length > 0) {
      return workflowAlerts.length;
    }
    if (pipelineDetails?.alerts_count !== undefined) {
      return pipelineDetails.alerts_count;
    }
    return workflow?.alerts ? parseInt(workflow.alerts) || 0 : 0;
  };

  const timeRunPercentage = calculateTimeRunPercentage();
  const formattedRunningTime = formatRunningTime(
    workflow?.runtime || workflow?.avgRunningTime || 0
  );
  const alertsCount = getAlertsCount();

  // Show loading state if no workflow selected
  if (!workflow) {
    return (
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          bgcolor: "background.paper",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          px: 3,
          pb: 3,
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            margin: "auto",
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
            No Workflow Selected!
        </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        bgcolor: "background.paper",
        display: "flex",
        flexDirection: "column",
        px: 3,
        overflowY: "scroll"
      }}
    >
      {/* Header Box */}
      <Box
        sx={{
          bgcolor: "background.paper",
        border: "1px solid", 
          borderColor: "divider",
        borderRadius: 0, 
        p: 2,
        mb: 0,
        mx: -3,
        mt: 0,
        borderTop: "none",
        }}
      >
        {loadingDetails && <Loading />}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <Typography
            variant="h5"
            sx={{
              fontWeight: 600,
              color: "text.primary",
            }}
          >
            {workflow?.name || "Unnamed Workflow"}
          </Typography>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
            <Button
              variant="text"
              size="small"
              onClick={handleReportMenuOpen}
              startIcon={<FileCopyIcon sx={{ fontSize: 16 }} />}
              sx={{
                color: "primary.main",
                bgcolor: "rgba(25, 118, 210, 0.08)",
                px: 1.5,
                py: 0.5,
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 500,
                textTransform: "none",
                "&:hover": {
                  bgcolor: "rgba(25, 118, 210, 0.16)",
                },
              }}
            >
              Get Report
            </Button>
            <Menu
              anchorEl={reportMenuAnchor}
              open={Boolean(reportMenuAnchor)}
              onClose={handleReportMenuClose}
              PaperProps={{
                sx: {
                  maxHeight: 300,
                  minWidth: 250,
                },
              }}
            >
              {loadingReports ? (
                <MenuItem disabled>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Loading reports...
                </MenuItem>
              ) : reports.length === 0 ? (
                <MenuItem disabled>
                  <ListItemText primary="No reports available" />
                </MenuItem>
              ) : (
                reports.map((report) => (
                  <MenuItem
                    key={report.report_id}
                    onClick={() => handleViewReport(report.report_id)}
                    disabled={viewingReport === report.report_id}
                  >
                    <ListItemIcon>
                      {viewingReport === report.report_id ? (
                        <CircularProgress size={20} />
                      ) : (
                        <DescriptionIcon fontSize="small" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={report.report_id}
                      secondary={`${report.severity?.toUpperCase() || "Unknown"} - ${
                        report.timestamp
                          ? new Date(report.timestamp).toLocaleDateString()
                          : "N/A"
                      }`}
                    />
                    <OpenInNewIcon fontSize="small" sx={{ ml: 1, color: "text.secondary" }} />
                  </MenuItem>
                ))
              )}
            </Menu>
            <AvatarGroup
              max={3}
              sx={{
                "& .MuiAvatar-root": {
                  width: 32,
                  height: 32,
                  fontSize: "0.75rem",
                },
              }}
            >
              {(workflow?.team || []).map((member, index) => {
                const avatarUrl = `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
                  member.name || member.id || `user${index}`
                )}&size=32`;
                return (
                  <Avatar 
                    key={index}
                    src={avatarUrl}
                    alt={member.name}
                    sx={{ 
                      width: 32, 
                      height: 32,
                    }}
                    title={member.name}
                  />
                );
              })}
            </AvatarGroup>
          </Box>
        </Box>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            fontSize: "0.875rem",
            lineHeight: 1.6,
          }}
        >
          {workflow?.description || "No description available"}
        </Typography>
        {pipelineDetails?.created_at && (
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
              fontSize: "0.75rem",
              mt: 1,
              display: "block",
            }}
          >
            Created {new Date(pipelineDetails.created_at).toLocaleString()}
          </Typography>
        )}
      </Box>

      {/* 1x3 Grid: Pipeline, Average Running Time, Alerts Pending */}
      <Box 
        sx={{ 
          display: "grid", 
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 0,
          mb: 0,
          mx: -3,
        }}
      >
        <PipelinePreview workflowId={workflow?.id || workflow?._id} />
        <MetricCard
          title="Total Running Time"
          subtitle="Pipeline Running"
          value={formattedRunningTime}
          change={timeRunPercentage}
        />
        <MetricCard
          title="Alerts Pending"
          subtitle="Real-time alerts from pipeline"
          value={String(alertsCount).padStart(2, "0")}
          change={workflow?.alertsChange || "0%"}
        />
      </Box>

      {/* Two Columns: Action Required and Logs */}
      <Box 
        sx={{ 
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 0,
          flex: 1,
          mx: -3,
        }}
      >
        <ActionRequired
          actionFilter={actionFilter}
          onFilterChange={onActionFilterChange}
          notifications={filteredNotifications}
        />
        <LogsSection workflow={workflow} />
      </Box>

      {/* Report Dialog */}
      <Dialog
        open={reportDialogOpen}
        onClose={handleReportDialogClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            maxHeight: "85vh",
          },
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid",
            borderColor: "divider",
            pb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <DescriptionIcon color="primary" />
            <Box>
              <Typography variant="h6" fontWeight={600}>
                Incident Report
              </Typography>
              {reportMetadata?.report_id && (
                <Typography variant="caption" color="text.secondary">
                  {reportMetadata.report_id}
                </Typography>
              )}
            </Box>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {reportMetadata?.severity && (
              <Chip
                label={reportMetadata.severity.toUpperCase()}
                color={getSeverityColor(reportMetadata.severity)}
                size="small"
                sx={{ fontWeight: 600 }}
              />
            )}
            {reportMetadata?.primary_service && (
              <Chip
                label={reportMetadata.primary_service}
                variant="outlined"
                size="small"
              />
            )}
            <IconButton onClick={handleReportDialogClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          {/* Report Metadata */}
          {reportMetadata?.timestamp && (
            <Box
              sx={{
                px: 3,
                py: 1.5,
                bgcolor: alpha(theme.palette.primary.main, 0.04),
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                Generated: {new Date(reportMetadata.timestamp).toLocaleString()}
              </Typography>
            </Box>
          )}
          
          {/* Markdown Content */}
          <Box
            sx={{
              p: 3,
              overflow: "auto",
              maxHeight: "calc(85vh - 180px)",
              "& h1": {
                fontSize: "1.75rem",
                fontWeight: 700,
                mb: 2,
                mt: 0,
                pb: 1,
                borderBottom: "1px solid",
                borderColor: "divider",
              },
              "& h2": {
                fontSize: "1.375rem",
                fontWeight: 600,
                mb: 1.5,
                mt: 3,
              },
              "& h3": {
                fontSize: "1.125rem",
                fontWeight: 600,
                mb: 1,
                mt: 2,
              },
              "& p": {
                m: 0,
                mb: 1.5,
                lineHeight: 1.7,
                color: "text.secondary",
              },
              "& ul, & ol": {
                pl: 3,
                mb: 1.5,
              },
              "& li": {
                mb: 0.5,
                color: "text.secondary",
              },
              "& code": {
                px: 0.75,
                py: 0.25,
                borderRadius: 0.5,
                bgcolor: alpha(theme.palette.action.hover, 0.8),
                fontFamily: "monospace",
                fontSize: "0.8125rem",
              },
              "& pre": {
                p: 2,
                borderRadius: 1,
                bgcolor: alpha(theme.palette.action.hover, 0.5),
                overflow: "auto",
                "& code": {
                  p: 0,
                  bgcolor: "transparent",
                },
              },
              "& blockquote": {
                borderLeft: "4px solid",
                borderColor: "primary.main",
                pl: 2,
                ml: 0,
                my: 2,
                color: "text.secondary",
                fontStyle: "italic",
              },
              "& table": {
                width: "100%",
                borderCollapse: "collapse",
                mb: 2,
              },
              "& th, & td": {
                border: "1px solid",
                borderColor: "divider",
                px: 2,
                py: 1,
                textAlign: "left",
              },
              "& th": {
                bgcolor: alpha(theme.palette.primary.main, 0.04),
                fontWeight: 600,
              },
              "& hr": {
                border: "none",
                borderTop: "1px solid",
                borderColor: "divider",
                my: 3,
              },
              "& a": {
                color: "primary.main",
                textDecoration: "none",
                "&:hover": {
                  textDecoration: "underline",
                },
              },
              "& strong": {
                fontWeight: 600,
                color: "text.primary",
              },
            }}
          >
            <Markdown>{reportContent}</Markdown>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default WorkflowDetails;
