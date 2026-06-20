import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import { styles } from "../styles/WorkflowsList.styles";
import { create_pipeline, fetchPipelineDetails } from "../utils/pipelineUtils";
import Loading from "../components/common/Loading";
import WorkflowHeader from "../components/workflowslist/WorkflowHeader";
import WorkflowCard from "../components/workflowslist/WorkflowCard";
import WorkflowDetails from "../components/workflowslist/WorkflowDetails";
import TopBar from "../components/common/TopBar";
import NewProjectModal from "../components/createWorkflow/NewProjectModal";
import CreateWorkflowDrawer from "../components/createWorkflow/CreateWorkflowDrawer";
import { useGlobalState } from "../context/GlobalStateContext";
import { useWebSocket } from "../context/WebSocketContext";
import { formatTimeAgo } from "../helpers/datetime";
import planeLight from "../assets/plane_light.svg";
import planeDark from "../assets/plane_dark.svg";
import { useTheme } from "@mui/material/styles";

// Transform backend workflow data to frontend format
const transformWorkflow = (backendWorkflow, details = null) => {
  const pipeline = backendWorkflow.user_pipeline_version?.pipeline || {};
  const runtime = backendWorkflow.runtime || 0;
  const description =
    backendWorkflow.user_pipeline_version?.version_description ||
    `Pipeline: ${backendWorkflow.name}`;

  // Combine owners and viewers into team
  const owners = (backendWorkflow.owners || []).map((owner) => ({
    ...owner,
    name: owner.name || owner.display_name || `User ${owner.id}`, // Ensure name field exists
  }));
  const viewerIds = backendWorkflow.viewer_ids || [];
  // Create viewer objects from viewer_ids (assuming they're not already fetched)
  // If viewers are fetched separately, they would be in backendWorkflow.viewers
  const viewers =
    backendWorkflow.viewers ||
    viewerIds.map((id) => {
      const idStr = String(id);
      return {
        id: idStr,
        display_name: `User ${idStr}`,
        name: `User ${idStr}`, // Add name for WorkflowCard compatibility
        initials:
          idStr.length >= 2
            ? idStr.slice(0, 2).toUpperCase()
            : idStr.toUpperCase(),
      };
    });

  // Combine owners and viewers, removing duplicates by id
  const allTeamMembers = [...owners];
  viewers.forEach((viewer) => {
    if (!allTeamMembers.find((m) => String(m.id) === String(viewer.id))) {
      allTeamMembers.push(viewer);
    }
  });

  // Use provided details or default values
  const created_at =
    details?.created_at ||
    backendWorkflow.user_pipeline_version?.version_created_at;
  const alertsCount = details?.alerts_count || details?.alerts?.length || 0;

  return {
    id: backendWorkflow._id || backendWorkflow.id,
    name: backendWorkflow.name || "Unnamed Workflow",
    category: description, // Show description instead of "General"
    location: formatTimeAgo(backendWorkflow.last_updated), // Show time ago instead of "Default"
    team: allTeamMembers, // Include both owners and viewers
    status: backendWorkflow.status || "Stopped", // Status: Running, Stopped, or Broken
    description: description,
    avgChange: "0%", // Can be calculated from historical data if available
    alerts: String(alertsCount).padStart(2, "0"),
    alertsChange: "0%", // Can be calculated from historical data if available
    nodes: pipeline.nodes || [],
    edges: pipeline.edges || [],
    members: backendWorkflow.owner_ids?.join(", ") || "",
    last_updated: backendWorkflow.last_updated,
    runtime: runtime,
    avgRunningTime: backendWorkflow.runtime || 0,
    created_at: created_at,
    // Include user_pipeline_version for RecentWorkflowCard
    user_pipeline_version: backendWorkflow.user_pipeline_version,
    // Include original backend data for reference
    owners: owners,
    viewer_ids: viewerIds,
  };
};

export const WorkflowsList = () => {
  const theme = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedTab, setSelectedTab] = useState(0);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [actionFilter, setActionFilter] = useState("notifications"); // notifications, pending_actions, actions_taken
  
  // Initialize search from URL params
  const initialSearch = searchParams.get('search') || '';
  const [globalSearchQuery, setGlobalSearchQuery] = useState(initialSearch);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Use ref for cache to avoid triggering re-renders when cache is updated inside useEffect
  const workflowDetailsCacheRef = useRef({});
  const [transformedWorkflows, setTransformedWorkflows] = useState([]);
  const { workflows, loading: globalLoading } = useGlobalState();
  const { alerts, getAlertsForPipeline, isConnected, ws } = useWebSocket();

  // Update URL when search changes
  const handleSearchChange = useCallback((value) => {
    setGlobalSearchQuery(value);
    if (value.trim()) {
      setSearchParams({ search: value });
    } else {
      setSearchParams({});
    }
  }, [setSearchParams]);

  // Fetch details for a specific workflow (using ref to avoid infinite loops)
  const fetchWorkflowDetails = useCallback(
    async (workflowId) => {
      if (workflowDetailsCacheRef.current[workflowId]) {
        return workflowDetailsCacheRef.current[workflowId];
      }

    try {
      // Ensure workflowId is a string
      const idString = typeof workflowId === 'string' ? workflowId : String(workflowId?.id || workflowId?._id || workflowId || '');
      if (!idString || idString === '[object Object]') {
        console.warn(`Invalid workflow ID for fetchPipelineDetails:`, workflowId);
        return null;
      }
      const details = await fetchPipelineDetails(workflowId);
      workflowDetailsCacheRef.current[workflowId] = details;
      return details;
    } catch (err) {
      console.warn(`Failed to fetch details for pipeline ${workflowId}:`, err);
      return null;
    }
  }, []); // No dependencies needed since we use ref

  // Update transformed workflows with details when workflows change (immediate display, async details)
  useEffect(() => {
    if (workflows.length === 0) {
      setTransformedWorkflows([]);
      if (selectedWorkflow) setSelectedWorkflow(null);
      return;
    }

    const updateWorkflowsWithDetails = async () => {
      try {
        setLoading(true);
        // Only fetch details for workflows that don't have them cached
        const workflowsToUpdate = workflows.filter((w) => {
          const workflowId = w.id || w._id;
          return workflowId && !workflowDetailsCacheRef.current[workflowId];
        });

        // Fetch details for workflows that need them
        if (workflowsToUpdate.length > 0) {
          await Promise.all(
            workflowsToUpdate.map(async (w) => {
              const workflowId = w.id || w._id;
              await fetchWorkflowDetails(workflowId);
            })
          );
        }

        // Transform all workflows with cached details
        const transformed = workflows.map((w) => {
          const workflowId = w.id || w._id;
          const details = workflowId
            ? workflowDetailsCacheRef.current[workflowId] || null
            : null;
          return transformWorkflow(w, details);
        });

        setTransformedWorkflows(transformed);

        // Update selected workflow if it exists
        if (selectedWorkflow) {
          const updated = transformed.find((w) => w.id === selectedWorkflow.id);
          if (updated) {
            setSelectedWorkflow(updated);
          }
        } else if (transformed.length > 0) {
          setSelectedWorkflow(transformed[0]);
        }
      } catch (err) {
        console.error("Error updating workflows with details:", err);
      }finally {
        setLoading(false);
      }
    };

    // Load details immediately (no delay)
    updateWorkflowsWithDetails()
  }, [workflows, fetchWorkflowDetails]); // Only depend on workflows and fetchWorkflowDetails

  // Handle WebSocket messages for workflow updates and alerts
  useEffect(() => {
    if (!ws || !isConnected) return;

    const handleMessage = (event) => {
      try {
        const data =
          typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        const messageType = data.message_type || data.type;

        // Handle workflow updates (status changes, runtime updates, etc.)
        // Note: Workflows are managed by GlobalStateContext, so we just need to update transformed workflows
        if (messageType === "workflow" && data._id) {
          const workflowId = String(data._id);

          // Invalidate cache for this workflow to refetch details (using ref)
          delete workflowDetailsCacheRef.current[workflowId];

          // Update selected workflow if it's the one being updated
          setSelectedWorkflow((prev) => {
            if (prev && (prev.id === workflowId || prev._id === workflowId)) {
              const hasChanges =
                (data.status && prev.status !== data.status) ||
                (data.runtime !== undefined && prev.runtime !== data.runtime) ||
                (data.last_updated && prev.last_updated !== data.last_updated);

              if (!hasChanges) return prev;

              return {
                ...prev,
                status: data.status || prev.status,
                runtime:
                  data.runtime !== undefined ? data.runtime : prev.runtime,
                last_updated: data.last_updated || prev.last_updated,
                location: formatTimeAgo(data.last_updated || prev.last_updated),
              };
            }
            return prev;
          });
        }
      } catch (error) {
        console.error(
          "Error handling WebSocket message in WorkflowsList:",
          error
        );
      }
    };

    ws.addEventListener("message", handleMessage);
    return () => {
      ws.removeEventListener("message", handleMessage);
    };
  }, [ws, isConnected]);

  // Update workflow alerts in real-time from WebSocket
  useEffect(() => {
    if (!isConnected) return;

    setTransformedWorkflows((prevWorkflows) => {
      let hasChanges = false;
      const updated = prevWorkflows.map((workflow) => {
        const workflowAlerts = getAlertsForPipeline(workflow.id);
        const alertsCount = workflowAlerts.length;
        const newAlerts = String(alertsCount).padStart(2, "0");

        if (workflow.alerts !== newAlerts) {
          hasChanges = true;
          return {
            ...workflow,
            alerts: newAlerts,
          };
        }
        return workflow;
      });

      return hasChanges ? updated : prevWorkflows;
    });
  }, [alerts.length, isConnected, getAlertsForPipeline]);

  // Update selected workflow alerts when alerts change
  useEffect(() => {
    if (!selectedWorkflow || !isConnected) return;

    const workflowAlerts = getAlertsForPipeline(selectedWorkflow.id);
    const newAlerts = String(workflowAlerts.length).padStart(2, "0");

    if (selectedWorkflow.alerts !== newAlerts) {
      setSelectedWorkflow((prev) => ({
        ...prev,
        alerts: newAlerts,
      }));
    }
  }, [alerts.length, selectedWorkflow?.id, isConnected, getAlertsForPipeline]);

  const handleLogout = () => {
    // Add logout logic here
  };
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false);
  const [createWorkflowDrawerOpen, setCreateWorkflowDrawerOpen] =
    useState(false);

  const handleAddNew = () => {
    setNewProjectModalOpen(true);
  };

  const handleSelectTemplate = (template) => {
    // If blank template, open the create workflow drawer
    if (template.id === "blank") {
      setNewProjectModalOpen(false);
      setCreateWorkflowDrawerOpen(true);
      return;
    }

    // For other templates, open the create workflow drawer
    // The actual template data will be handled in the drawer
    setNewProjectModalOpen(false);
    setCreateWorkflowDrawerOpen(true);
  };

  const handleCreateWorkflowComplete = async (workflowData) => {
    // The CreateWorkflowDrawer now handles the pipeline creation and saving
    // This callback receives the completed workflow data for any additional handling
    try {
      setLoading(true);
      
      const newWorkflowId = workflowData.pipelineId;
      
      // Workflows will be updated automatically via GlobalStateContext WebSocket
      // Just select the newly created workflow if we can find it
      if (newWorkflowId) {
        // Wait a bit for WebSocket to update, then find the workflow
        setTimeout(() => {
          const newWorkflow = transformedWorkflows.find(
            (w) => w.id === newWorkflowId || w._id === newWorkflowId
          );
          if (newWorkflow) {
            setSelectedWorkflow(newWorkflow);
          }
      }, 1000);
    }
    } catch (err) {
      console.error("Error handling workflow creation:", err);
      setError(err.message || "Failed to handle workflow creation");
    } finally {
      setLoading(false);
    }
  };

  // Filter workflows by status and search, limit to 10 max
  const filteredWorkflows = useMemo(() => {
    const filtered = transformedWorkflows.filter((workflow) => {
      const matchesSearch =
        workflow.name.toLowerCase().includes(globalSearchQuery.toLowerCase()) ||
        workflow.category
          .toLowerCase()
          .includes(globalSearchQuery.toLowerCase());

      // Filter by status based on selected tab
      // 0: All, 1: Running, 2: Stopped, 3: Broken
      if (selectedTab === 0) return matchesSearch; // All workflows
      if (selectedTab === 1)
        return matchesSearch && workflow.status === "Running"; // Running only
      if (selectedTab === 2)
        return matchesSearch && workflow.status === "Stopped"; // Stopped only
      if (selectedTab === 3)
        return matchesSearch && workflow.status === "Broken"; // Broken only

      return matchesSearch;
    });

    // Sort by last_updated (most recent first) and limit to 10
    return filtered
      .slice()
      .sort((a, b) => {
        const dateA = a.last_updated || a.created_at || new Date(0);
        const dateB = b.last_updated || b.created_at || new Date(0);
        return new Date(dateB) - new Date(dateA);
      })
      .slice(0, 10);
  }, [transformedWorkflows, globalSearchQuery, selectedTab]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        ml: "64px",
      }}
    >
      {/* TopBar */}
      <TopBar
        showSearch={true}
        userAvatar="https://i.pravatar.cc/150?img=1"
        searchPlaceholder="Search workflows, projects, or users..."
        searchValue={globalSearchQuery}
        onSearchChange={handleSearchChange}
        onLogout={handleLogout}
      />

      <Box
        sx={{
          ...styles.mainContainer,
          bgcolor: "background.default",
          flex: 1,
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {/* Main Content Area */}
        <Box
          sx={{
            ...styles.mainContentArea,
            bgcolor: "background.default",
            height: "100%",
            minHeight: 0,
          }}
        >
          {/* Main Content - Workflows List */}
          <Box
            sx={{
              width: { xs: "100%", lg: "33%" },
              minWidth: { lg: 350 },
              maxWidth: { lg: 500 },
              bgcolor: "background.paper",
              borderRight: "none",
              borderBottom: "none",
              height: "100%",
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              p: 3,
            }}
          >
            <WorkflowHeader
              onAddNew={handleAddNew}
              selectedTab={selectedTab}
              onTabChange={setSelectedTab}
            />

            {/* Scrollable Workflow Cards */}
            <Box
              sx={{
                flex: 1,
                minHeight: 0,
                overflowY: "auto",
                px: 2,
                pt: 2,
                pb: 3,
              }}
            >
              {globalLoading || loading ? (
                <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 4 }}>
                  <Loading />
                </Box>
              ) : error ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    py: 4,
                  }}
                >
                  <Typography color="error">{error}</Typography>
                </Box>
              ) : filteredWorkflows.length === 0 ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    py: 4,
                  }}
                >
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
                      sx={{
                        color: "text.secondary",
                        fontSize: "0.875rem",
                        mt: 2,
                      }}
                    >
                      No workflows found
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Box
                  sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}
                >
                  {filteredWorkflows.map((workflow) => (
                    <WorkflowCard
                      key={workflow.id}
                      workflow={workflow}
                      isSelected={selectedWorkflow?.id === workflow.id}
                      onClick={() => setSelectedWorkflow(workflow)}
                    />
                  ))}
                </Box>
              )}
            </Box>
          </Box>

          {selectedWorkflow && (
            <WorkflowDetails
              workflow={selectedWorkflow}
              actionFilter={actionFilter}
              onActionFilterChange={setActionFilter}
              logs={[]}
            />
          )}
        </Box>
      </Box>

      {/* New Project Modal */}
      <NewProjectModal
        open={newProjectModalOpen}
        onClose={() => setNewProjectModalOpen(false)}
        onSelectTemplate={handleSelectTemplate}
      />

      {/* Create Workflow Drawer */}
      <CreateWorkflowDrawer
        open={createWorkflowDrawerOpen}
        onClose={() => setCreateWorkflowDrawerOpen(false)}
        onComplete={handleCreateWorkflowComplete}
      />
    </Box>
  );
};

export default WorkflowsList;
