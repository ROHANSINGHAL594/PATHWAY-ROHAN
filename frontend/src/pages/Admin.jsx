import { useState, useEffect } from "react";
import { Typography, Box, Divider } from "@mui/material";
import TopBar from "../components/common/TopBar";
import { useGlobalContext } from "../context/GlobalContext";
import { AuthContext } from "../context/AuthContext";
import { useContext } from "react";
import {
  fetchAllWorkflows,
  retrievePipeline,
  fetchOverviewData,
  fetchChartsData,
} from "../utils/developerDashboard.api";

// Import components from admin folder
import { KpiCard } from "../components/admin/KpiCardAdmin";
import { PipelineStatsChart } from "../components/admin/PipelineStatsChart";
import { RuntimeChart } from "../components/admin/RuntimeChart";
import { RCAChart } from "../components/admin/RCAChart";
import { AlertsChart } from "../components/admin/AlertsChart";
import { WorkflowsTable } from "../components/admin/WorkflowsTable";
import { MembersTable } from "../components/admin/MembersTable";
import PieChartOutlineIcon from "@mui/icons-material/PieChartOutline";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import EqualizerIcon from "@mui/icons-material/Equalizer";
import TimelineIcon from "@mui/icons-material/Timeline";
import "../css/overview.css";
import "../css/admin.css";

// Main Admin Page Component
export function AdminPage() {
  const [selectedChart, setSelectedChart] = useState("alerts");
  const { workflows, setWorkflows } = useGlobalContext();
  const { user } = useContext(AuthContext);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [workflowNames, setWorkflowNames] = useState({}); // Map of workflow_id to name

  // KPI data from API
  const [kpiData, setKpiData] = useState([
    {
      id: 1,
      title: "Pipeline Running",
      value: "0",
      description: "Total number of pipeline running",
      icon: PieChartOutlineIcon,
      iconClass: "blue",
    },
    {
      id: 2,
      title: "Total Runtime",
      value: "0s",
      description: "Across all pipelines",
      icon: AutoGraphIcon,
      iconClass: "blue",
    },
    {
      id: 3,
      title: "Alerts",
      value: "00",
      description: "No. of alerts today",
      icon: EqualizerIcon,
      iconClass: "blue",
      cardClass: "alerts",
    },
    {
      id: 4,
      title: "RCA Triggers",
      value: "0",
      description: "Root cause analysis",
      icon: TimelineIcon,
      iconClass: "blue",
    },
  ]);

  // Pipeline stats from API (maps to PipelineStatsChart: successful=running, errors=stopped, broken=broken)
  const [pipelineStatsData, setPipelineStatsData] = useState({
    successful: 0,
    errors: 0,
    broken: 0,
  });

  // Charts data from API
  const [alertsChartData, setAlertsChartData] = useState([]);
  const [runtimeChartData, setRuntimeChartData] = useState([]);
  const [rcaChartData, setRcaChartData] = useState({
    total: 0,
    time_series: {
      labels: [
        "10:00 AM",
        "11:00 AM",
        "12:00 PM",
        "1:00 PM",
        "2:00 PM",
        "3:00 PM",
      ],
      datasets: [{ color: "#A2B8F4", values: [0, 0, 0, 0, 0, 0] }],
    },
    stats: [],
  });

  // Fetch KPI data from API
  useEffect(() => {
    const fetchKpiData = async () => {
      try {
        const data = await fetchOverviewData();

        // Update pipeline stats (mapping: running->successful, stopped->errors, broken->broken)
        if (data.pie_chart) {
          setPipelineStatsData({
            successful: data.pie_chart.running || 0,
            errors: data.pie_chart.stopped || 0,
            broken: data.pie_chart.broken || 0,
          });
        }

        // Update KPI cards with real data
        if (data.kpi && Array.isArray(data.kpi)) {
          const runtimeKpi = data.kpi.find((k) => k.id === "total_runtime");
          const alertsKpi = data.kpi.find((k) => k.id === "total_alerts");
          const pendingKpi = data.kpi.find((k) => k.id === "pending_alerts");
          const rcaKpi = data.kpi.find((k) => k.id === "rca_triggers");

          // Fetch charts data
          try {
            const chartsData = await fetchChartsData();
            // Update charts data
            if (chartsData.alerts_chart) {
              setAlertsChartData(chartsData.alerts_chart);
            }
            if (chartsData.runtime_chart) {
              setRuntimeChartData(chartsData.runtime_chart);
            }
            if (chartsData.rca_chart) {
              setRcaChartData(chartsData.rca_chart);
            }
          } catch (chartError) {
            console.error("Error fetching charts data:", chartError);
          }

          setKpiData([
            {
              id: 1,
              title: "Pipeline Running",
              value: String(data.pie_chart?.running || 0),
              description: `${data.pie_chart?.total || 0} total pipelines`,
              icon: PieChartOutlineIcon,
              iconClass: "blue",
            },
            {
              id: 2,
              title: "Total Runtime",
              value: runtimeKpi?.value || "0s",
              description: runtimeKpi?.subtitle || "Across all pipelines",
              icon: AutoGraphIcon,
              iconClass: "blue",
            },
            {
              id: 3,
              title: "Alerts",
              value: String(alertsKpi?.value || 0).padStart(2, "0"),
              description: `${pendingKpi?.value || 0} pending alerts`,
              icon: EqualizerIcon,
              iconClass: "blue",
              cardClass: "alerts",
            },
            {
              id: 4,
              title: "RCA Triggers",
              value: String(rcaKpi?.value || 0),
              description: rcaKpi?.subtitle || "Root cause analysis",
              icon: TimelineIcon,
              iconClass: "blue",
            },
          ]);
        }
      } catch (error) {
        console.error("Error fetching KPI data:", error);
      }
    };

    fetchKpiData();
  }, []);

  // Fetch workflow names when workflows are loaded
  useEffect(() => {
    const fetchWorkflowNames = async () => {
      if (!workflows || workflows.length === 0) return;

      const namesMap = {};
      const fetchPromises = workflows.map(async (workflow) => {
        if (!workflow._id || !workflow.current_version_id) return;

        try {
          const result = await retrievePipeline(
            workflow._id,
            workflow.current_version_id
          );
          // Check workflow name first
          if (result.workflow?.name) {
            namesMap[workflow._id] = result.workflow.name;
          }
          // Check version pipeline metadata for name
          else if (result.version?.pipeline?.metadata?.pipelineName) {
            namesMap[workflow._id] =
              result.version.pipeline.metadata.pipelineName;
          }
        } catch (error) {
          console.error(
            `Error fetching name for workflow ${workflow._id}:`,
            error
          );
          // If error, name will remain undefined and default format will be used
        }
      });

      await Promise.all(fetchPromises);
      setWorkflowNames(namesMap);
    };

    fetchWorkflowNames();
  }, [workflows]);

  // Select first workflow by default when workflows are loaded
  useEffect(() => {
    if (workflows && workflows.length > 0 && !selectedWorkflow) {
      setSelectedWorkflow(workflows[0]);
    }
  }, [workflows, selectedWorkflow]);

  // Handle workflow update (e.g., after removing a viewer)
  const handleWorkflowUpdate = async (updatedWorkflow) => {
    // Update the selected workflow
    setSelectedWorkflow(updatedWorkflow);

    // Refresh workflows list from backend
    try {
      const workflowResponse = await fetchAllWorkflows();
      if (workflowResponse.status === "success" && workflowResponse.data) {
        setWorkflows(workflowResponse.data);
        // Update selected workflow if it still exists
        const updated = workflowResponse.data.find(
          (w) => w._id === updatedWorkflow._id
        );
        if (updated) {
          setSelectedWorkflow(updated);
        }
      }
    } catch (error) {
      console.error("Error refreshing workflows:", error);
    }
  };

  const handleKpiClick = (kpiId) => {
    if (kpiId === 1) {
      setSelectedChart("pipeline");
    } else if (kpiId === 2) {
      setSelectedChart("runtime");
    } else if (kpiId === 3) {
      setSelectedChart("alerts");
    } else if (kpiId === 4) {
      setSelectedChart("rca");
    }
  };

  return (
    <Box
      className="below-sidebar-container"
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        className="admin-container"
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Top Bar */}
        <TopBar />

        {/* Main Content */}
        <Box
          className="admin-content"
          sx={{
            flex: 1,
            p: { xs: 2, md: 3 },
            overflowY: "auto",
          }}
        >
          {/* Main Grid - KPIs and Alerts */}
          <Box
            className="admin-grid"
            sx={{
              display: "flex",
              overflow: "hidden",
              flexDirection: { xs: "column", lg: "row" },
            }}
          >
            {/* Left Column - Header + KPI Cards */}
            <Box
              className="admin-left-column"
              sx={{
                width: { xs: "100%", lg: "50%" },
                p: 2.5,
                display: "flex",
                flexDirection: "column",
                gap: 2,
              }}
            >
              {/* Header */}
              <Box className="admin-header" sx={{ mb: 0.5 }}>
                <Typography
                  variant="h5"
                  sx={{
                    fontSize: "1.5rem",
                    fontWeight: 600,
                    color: "text.primary",
                    mb: 0.25,
                  }}
                >
                  Admin Overview
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    color: "text.secondary",
                    fontSize: "0.875rem",
                  }}
                >
                  Select the metric to visualize it on right !
                </Typography>
              </Box>
              {/* KPI Cards */}
              <Box
                className="admin-kpi-section"
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
                  gap: 2,
                  flex: 1,
                }}
              >
                {kpiData.map((kpi) => (
                  <KpiCard
                    key={kpi.id}
                    title={kpi.title}
                    value={kpi.value}
                    description={kpi.description}
                    icon={kpi.icon}
                    iconClass={kpi.iconClass}
                    cardClass={kpi.cardClass}
                    onClick={() => handleKpiClick(kpi.id)}
                    isSelected={
                      (kpi.id === 1 && selectedChart === "pipeline") ||
                      (kpi.id === 2 && selectedChart === "runtime") ||
                      (kpi.id === 3 && selectedChart === "alerts") ||
                      (kpi.id === 4 && selectedChart === "rca")
                    }
                  />
                ))}
              </Box>
            </Box>

            {/* Chart Section */}
            <Box
              className="admin-alerts-wrapper"
              sx={{
                width: { xs: "100%", lg: "50%" },
                p: 2.5,
              }}
            >
              {selectedChart === "pipeline" ? (
                <PipelineStatsChart data={pipelineStatsData} />
              ) : selectedChart === "runtime" ? (
                <RuntimeChart data={runtimeChartData} />
              ) : selectedChart === "rca" ? (
                <RCAChart data={rcaChartData} />
              ) : (
                <AlertsChart data={alertsChartData} />
              )}
            </Box>
          </Box>

          {/* Divider between top and bottom sections */}
          <Divider sx={{ my: 3 }} />

          {/* Bottom Section - Workflows and Members */}
          <Box
            className="admin-bottom-section"
            sx={{
              display: "flex",
              overflow: "hidden",
              flexDirection: { xs: "column", lg: "row" },
            }}
          >
            <WorkflowsTable
              data={workflows}
              onWorkflowSelect={setSelectedWorkflow}
              selectedWorkflowId={selectedWorkflow?._id}
              workflowNames={workflowNames}
            />
            <Divider
              orientation="vertical"
              flexItem
              sx={{
                display: { xs: "none", lg: "block" },
                mx: 0,
              }}
            />
            <Box
              sx={{
                display: { xs: "block", lg: "none" },
                width: "100%",
              }}
            >
              <Divider sx={{ my: 0 }} />
            </Box>
            <MembersTable
              workflow={selectedWorkflow}
              onWorkflowUpdate={handleWorkflowUpdate}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
