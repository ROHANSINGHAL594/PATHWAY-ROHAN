import { useState, useEffect, useMemo } from "react";
import {
  Typography,
  IconButton,
  Drawer,
  Fab,
  Grid,
  Box,
  Divider,
  useTheme,
} from "@mui/material";
import OverviewSection from "../components/overview/OverviewSection";
import KPICard from "../components/overview/KPICardDashboard";
import RecentWorkflowCard from "../components/overview/RecentWorkflowCard";
import HighlightsPanel from "../components/overview/HighlightsPanel";
import TopBar from "../components/common/TopBar";
import { useGlobalState } from "../context/GlobalStateContext";
import { fetchPreviousNotifcations, fetchWorkflows } from "../utils/utils";
import { fetchOverviewData } from "../utils/developerDashboard.api";
import { useNavigate } from "react-router-dom";
import "../css/overview.css";
import TimelineIcon from "@mui/icons-material/Timeline";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import SpeedIcon from "@mui/icons-material/Speed";
import HighlightIcon from "@mui/icons-material/Highlight";
import CloseIcon from "@mui/icons-material/Close";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";
import planeLight from "../assets/plane_light.svg";
import planeDark from "../assets/plane_dark.svg";
// Icon mapping utility
const getIconComponent = (iconType) => {
  const iconMap = {
    timeline: TimelineIcon,
    "access-time": AccessTimeIcon,
    "error-outline": ErrorOutlineIcon,
    speed: SpeedIcon,
    notifications: NotificationsActiveOutlinedIcon,
  };
  return iconMap[iconType] || TimelineIcon;
};

export default function OverviewPage() {
  const navigate = useNavigate();
  const theme = useTheme();
  const [overviewData, setOverviewData] = useState(null);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const { workflows, setWorkflows, notifications, setNotifications } =
    useGlobalState();

  // Load initial KPI data
  useEffect(() => {
    const loadInitialData = async () => {
      // Fetch initial KPI data
      const overview = await fetchOverviewData();
      setOverviewData(overview);

      // Fetch initial notifications (workflows are already loaded by GlobalStateContext)
      setNotifications(await fetchPreviousNotifcations());
    };
    loadInitialData();
  }, []);

  // Fallback: Periodically refresh workflows if WebSocket isn't working
  // This ensures workflows are updated even if backend doesn't send WebSocket updates
  useEffect(() => {
    const refreshWorkflows = async () => {
      try {
        const workflowData = await fetchWorkflows(0, 100);
        if (workflowData.status === "success" && workflowData.data) {
          setWorkflows(workflowData.data);
        }
      } catch (error) {
        console.error("Error refreshing workflows:", error);
      }
    };

    // Refresh every 30 seconds as a fallback
    const intervalId = setInterval(refreshWorkflows, 30000);

    return () => clearInterval(intervalId);
  }, [setWorkflows]);

  // Update KPI data when workflows change (for dynamic updates via WebSocket)
  useEffect(() => {
    const updateKPIData = async () => {
      try {
        const overview = await fetchOverviewData();
        setOverviewData(overview);
      } catch (error) {
        console.error("Error updating KPI data:", error);
      }
    };

    // Update KPI data when workflows change (debounced to avoid too many calls)
    // Only update if we already have initial data loaded
    if (overviewData !== null) {
      const timeoutId = setTimeout(() => {
        updateKPIData();
      }, 500); // Debounce by 500ms

      return () => clearTimeout(timeoutId);
    }
  }, [workflows.length, overviewData]);

  const handleSelectTemplate = (templateId) => {
    if (!templateId) return;
    navigate(`/workflows/${templateId}`);
  };

  // Get recent workflows, sorted by last_updated (most recent first), limited to 4
  // Use useMemo to ensure it updates when workflows change
  const recentWorkflows = useMemo(() => {
    if (!workflows || workflows.length === 0) return [];

    return workflows
      .slice()
      .sort((a, b) => {
        const dateA =
          a.last_updated ||
          a.user_pipeline_version?.version_updated_at ||
          new Date(0);
        const dateB =
          b.last_updated ||
          b.user_pipeline_version?.version_updated_at ||
          new Date(0);
        return new Date(dateB) - new Date(dateA);
      })
      .slice(0, 4);
  }, [workflows]);
  return (
    <>
      <div className="below-sidebar-container">
        <div className="overview-main">
          <TopBar userAvatar="https://i.pravatar.cc/40" />

          <div className="overview-content-wrapper">
            <div className="overview-left-content">
              <Box
                sx={{
                  mx: { xs: "-16px", md: "-32px" },
                  mt: { xs: "-16px", md: "-32px" },
                  width: { xs: "calc(100% + 32px)", md: "calc(100% + 64px)" },
                }}
              >
                {overviewData && (
                  <Grid container spacing={0}>
                    <Grid className="First" size={{ xs: 12, md: 6, xl: 7 }}>
                      {overviewData["pie_chart"] && (
                        <OverviewSection
                          data={overviewData["pie_chart"]}
                          kpiData={overviewData["kpi"]}
                        />
                      )}
                    </Grid>

                    <Grid container size={{ xs: 12, md: 6, xl: 5 }} spacing={0}>
                      {overviewData["kpi"] &&
                        overviewData["kpi"].map((kpi, index) => {
                          // Get icon based on the iconType from API
                          const IconComponent = getIconComponent(kpi.iconType);
                          const totalKpis = overviewData["kpi"].length;
                          const isFirstRow = index < Math.ceil(totalKpis / 2);
                          const isLastRow =
                            index >= totalKpis - Math.ceil(totalKpis / 2);
                          return (
                            <Grid
                              size={{ xs: 6, sm: 4, md: 6, xl: 6 }}
                              key={kpi.id}
                            >
                              <KPICard
                                title={kpi.title}
                                value={kpi.value}
                                subtitle={kpi.subtitle}
                                icon={IconComponent}
                                iconColor={kpi.iconColor}
                                isFirstRow={isFirstRow}
                                isLastRow={isLastRow}
                              />
                            </Grid>
                          );
                        })}
                    </Grid>
                  </Grid>
                )}
              </Box>

              <div className="overview-horizontal-divider" />

              <div className="overview-workflows-section">
                <div className="overview-workflows-header">
                  <Typography variant="h6" className="overview-workflows-title">
                    Recent Workflows
                  </Typography>
                </div>
                <div className="overview-workflows-list">
                  {recentWorkflows.length === 0 ? (
                    <Box
                      sx={{
                        textAlign: "center",
                        py: "3rem",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "1rem",
                        width: "100%",
                      }}
                    >
                      <img
                        src={theme.palette.mode === "dark" ? planeDark : planeLight}
                        alt="No data"
                        style={{ width: "10rem", height: "auto", opacity: 0.7 }}
                      />
                      <Typography
                        color="text.secondary"
                        sx={{ fontSize: "0.875rem" }}
                      >
                        No recent workflows
                      </Typography>
                    </Box>
                  ) : (
                    recentWorkflows.map((workflow, index) => {
                      const workflowId =
                        workflow.id || workflow._id || `workflow-${index}`;
                      const lastUpdated =
                        workflow.last_updated ||
                        workflow.user_pipeline_version?.version_updated_at ||
                        "";
                      return (
                        <RecentWorkflowCard
                          key={`${workflowId}-${lastUpdated}`}
                          workflow={workflow}
                          onClick={() => {
                            handleSelectTemplate(workflowId);
                          }}
                        />
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            <div className="overview-highlights-panel">
              <HighlightsPanel />
            </div>
          </div>
        </div>
      </div>

      {/* Floating Action Button for Mobile/Tablet */}
      <Fab
        className="overview-highlights-fab"
        onClick={() => setMobileDrawerOpen(true)}
        aria-label="highlights"
      >
        <HighlightIcon />
      </Fab>

      {/* Mobile/Tablet Drawer for Highlights */}
      <Drawer
        anchor="right"
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        className="overview-drawer"
      >
        <div className="overview-drawer-header">
          <Typography variant="h6" className="overview-drawer-title">
            Highlights
          </Typography>
          <IconButton onClick={() => setMobileDrawerOpen(false)}>
            <CloseIcon />
          </IconButton>
        </div>
        <HighlightsPanel />
      </Drawer>
    </>
  );
}
