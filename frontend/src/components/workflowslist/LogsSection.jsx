import { useState } from "react";
import { Box, Typography, Avatar, IconButton, Chip } from "@mui/material";
import { Key as KeyIcon, History as HistoryIcon, BugReport as DebugIcon, Info as InfoIcon, Warning as WarningIcon, Error as ErrorIcon, Report as CriticalIcon } from "@mui/icons-material";
import { useEffect } from "react";
import { useGlobalState } from "../../context/GlobalStateContext";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

// Import local SVG assets
import bubbleGreen from "../../assets/bubble-green.svg";
import bubbleBlue from "../../assets/bubble-blue.svg";

dayjs.extend(relativeTime);

// Empty state component for no logs
const NoLogsState = () => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      py: 4,
      px: 2,
      minHeight: 200,
    }}
  >
    {/* Illustration */}
    <Box
      sx={{
        position: "relative",
        width: 200,
        height: 140,
        mb: 2,
      }}
    >
      {/* Blue bubble (top right) */}
      <Box
        component="img"
        src={bubbleBlue}
        alt=""
        sx={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 100,
          height: "auto",
          transform: "rotate(180deg) scaleY(-1)",
        }}
      />
      {/* Green bubble (bottom left) */}
      <Box
        component="img"
        src={bubbleGreen}
        alt=""
        sx={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: 120,
          height: "auto",
        }}
      />
    </Box>
    <Typography
      variant="body2"
      sx={{
        fontSize: "0.875rem",
        color: "text.secondary",
        textAlign: "center",
      }}
    >
      No logs available
    </Typography>
  </Box>
);

// Helper to format log timestamp (handles both BSON $date and regular formats)
const formatLogTimestamp = (timestamp) => {
  if (!timestamp) return { date: "Unknown", time: "", relative: "" };
  
  try {
    let dateStr;
    // Handle MongoDB BSON format { $date: "..." }
    if (timestamp && typeof timestamp === 'object' && timestamp['$date']) {
      dateStr = timestamp['$date'];
    } else if (typeof timestamp === 'string') {
      dateStr = timestamp;
    } else if (timestamp instanceof Date) {
      dateStr = timestamp.toISOString();
    } else {
      return { date: "Unknown", time: "", relative: "" };
    }
    
    const date = dayjs(dateStr);
    return {
      date: date.format("YYYY-MM-DD"),
      time: date.format("HH:mm:ss"),
      relative: date.fromNow()
    };
  } catch (error) {
    console.error("Error formatting log timestamp:", error);
    return { date: "Unknown", time: "", relative: "" };
  }
};

// Get log level styling
const getLogLevelStyle = (level) => {
  const styles = {
    debug: { color: "#6b7280", bgcolor: "#f3f4f6", icon: DebugIcon, label: "DEBUG" },
    info: { color: "#3b82f6", bgcolor: "#dbeafe", icon: InfoIcon, label: "INFO" },
    warning: { color: "#f59e0b", bgcolor: "#fef3c7", icon: WarningIcon, label: "WARN" },
    error: { color: "#ef4444", bgcolor: "#fee2e2", icon: ErrorIcon, label: "ERROR" },
    critical: { color: "#dc2626", bgcolor: "#fecaca", icon: CriticalIcon, label: "CRIT" }
  };
  return styles[level?.toLowerCase()] || styles.info;
};

const LogsSection = ({ workflow }) => {
  console.log("workflow in logsection:", workflow.id);
  const [logsView, setLogsView] = useState("logs");
  const colorPalette = ["#f97316", "#10b981", "#3b82f6", "#8b5cf6", "#14b8a6"];
  const { logs } = useGlobalState();
  // consolœ.log("logs in logsection:", logs);
  const [versionHistory, setVersionHistory] = useState(null);
  const [lenVersions, setLenVersions] = useState(0);
  const workflow_id = workflow.id || workflow._id; // Support both formats
  useEffect(() => {
    const fetch_version_history = async () => {
      try {
        const res = await fetch(
          `${
            import.meta.env.VITE_API_SERVER
          }/version/retrieve_versions?workflow_id=${workflow_id}`,
          { credentials: "include" }
        );

        const historyData = await res.json();

        setVersionHistory(historyData[0]);
        setLenVersions(historyData[1]);
      } catch (err) {
        console.error("Error fetching versions", err);
      }
    };

    fetch_version_history();
  }, [workflow_id]);

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
        borderLeft: "none",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          p: 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "text.primary" }}
        >
          {logsView === "logs" ? "Logs" : "Version History"}
        </Typography>
        <Box
          sx={{
            display: "flex",
            gap: 0,
            bgcolor: "background.elevation1",
            borderRadius: "8px",
            p: 0.5,
          }}
        >
          <IconButton
            size="small"
            onClick={() => setLogsView("logs")}
            sx={{
              bgcolor: logsView === "logs" ? "background.paper" : "transparent",
              color: logsView === "logs" ? "text.primary" : "text.secondary",
              borderRadius: "6px",
              px: 1,
              py: 0.5,
              boxShadow:
                logsView === "logs" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              "&:hover": {
                bgcolor:
                  logsView === "logs" ? "background.paper" : "action.hover",
              },
            }}
          >
            <KeyIcon sx={{ fontSize: 16 }} />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => setLogsView("history")}
            sx={{
              bgcolor:
                logsView === "history" ? "background.paper" : "transparent",
              color: logsView === "history" ? "text.primary" : "text.secondary",
              borderRadius: "6px",
              px: 1,
              py: 0.5,
              boxShadow:
                logsView === "history" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              "&:hover": {
                bgcolor:
                  logsView === "history" ? "background.paper" : "action.hover",
              },
            }}
          >
            <HistoryIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Box>
      </Box>
      <Box
        sx={{
          flex: 1,
          p: 2,
          pb: 3,
        }}
      >
        {logsView === "logs" ? (
          (() => {
            const filteredLogs = logs.filter((log) => {
              const logWorkflowId = log.workflow_id || log.pipeline_id;
              const workflowId = workflow?._id || workflow?.id;
              return (
                logWorkflowId &&
                workflowId &&
                String(logWorkflowId) === String(workflowId)
              );
            });
            
            if (filteredLogs.length === 0) {
              return <NoLogsState />;
            }
            
            return (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                {filteredLogs.map((log, index) => {
                  const levelStyle = getLogLevelStyle(log.level);
                  const LogIcon = levelStyle.icon;
                  const timeInfo = formatLogTimestamp(log.timestamp);
                  
                  return (
                    <Box key={log._id || index} sx={{ display: "flex", gap: 1.5 }}>
                      <Box
                        sx={{
                          width: 24,
                          height: 24,
                          borderRadius: "4px",
                          bgcolor: levelStyle.bgcolor,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                          mt: 0.25,
                        }}
                      >
                        <LogIcon
                          sx={{ fontSize: "0.875rem", color: levelStyle.color }}
                        />
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.25 }}>
                          <Chip
                            label={levelStyle.label}
                            size="small"
                            sx={{
                              height: 16,
                              fontSize: "0.625rem",
                              fontWeight: 600,
                              bgcolor: levelStyle.bgcolor,
                              color: levelStyle.color,
                              "& .MuiChip-label": { px: 0.75 }
                            }}
                          />
                          {log.source && (
                            <Typography
                              variant="caption"
                              sx={{ fontSize: "0.625rem", color: "text.disabled" }}
                            >
                              {log.source}
                            </Typography>
                          )}
                        </Box>
                        <Typography
                          variant="body2"
                          sx={{
                            fontSize: "0.8125rem",
                            color: "text.primary",
                            fontWeight: 600,
                          }}
                        >
                          {log.message}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{ fontSize: "0.6875rem", color: "text.secondary" }}
                        >
                          {timeInfo.relative} • {timeInfo.date} {timeInfo.time}
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            );
          })()
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {lenVersions === 0 ? (
              <Typography
                variant="body2"
                sx={{
                  fontSize: "0.75rem",
                  color: "text.secondary",
                  textAlign: "center",
                  py: 2,
                }}
              >
                No versions available
              </Typography>
            ) : (
              <>
                {versionHistory &&
                  versionHistory.map((item, index) => (
                    <Box
                      key={index}
                      sx={{ display: "flex", gap: 1.5, position: "relative" }}
                    >
                      {index < versionHistory.length - 1 && (
                        <Box
                          sx={{
                            position: "absolute",
                            left: "6px",
                            top: "24px",
                            bottom: "-16px",
                            width: "2px",
                            bgcolor: "divider",
                          }}
                        />
                      )}
                      <Box
                        sx={{
                          width: 14,
                          height: 14,
                          borderRadius: "50%",
                          bgcolor: `${colorPalette[index]}`,
                          flexShrink: 0,
                          mt: 0.25,
                          zIndex: 1,
                        }}
                      />
                      <Box sx={{ flex: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontSize: "0.8125rem",
                            color: "text.primary",
                            mb: 0.5,
                            fontWeight: 600,
                          }}
                        >
                          {item.date.split("T")[0]} at{" "}
                          {item.date.split("T")[1].split(".")[0]}
                        </Typography>
                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <Avatar
                            src={`https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
                              item.user
                            )}&size=32`}
                            alt={item.user}
                            sx={{ width: 20, height: 20 }}
                          />
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: "0.75rem",
                              color: "text.secondary",
                            }}
                          >
                            User ID: {item.user}, Version ID: {item.version_id}
                          </Typography>
                        </Box>
                      </Box>
                    </Box>
                  ))}
                {lenVersions > 5 && (
                  <Typography
                    variant="body2"
                    sx={{ fontSize: "0.75rem", color: "text.secondary" }}
                  >
                    And {lenVersions - 5} more version(s)
                  </Typography>
                )}
              </>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default LogsSection;
