import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "@xyflow/react/dist/style.css";
import { Box, Alert, Snackbar } from "@mui/material";

import { useGlobalContext } from "../context/GlobalContext";
import { useGlobalWorkflow } from "../context/GlobalWorkflowContext";
import {
  savePipelineAPI,
  toggleStatus as togglePipelineStatus,
  spinupPipeline,
  spindownPipeline,
  saveDraftsAPI,
  fetchAndSetPipeline,
} from "../utils/pipelineUtils";
import { fetchAllWorkflows } from "../utils/developerDashboard.api";
import PipelineNavBar from "../components/workflow/PipelineNavBar";
import Playground from "../components/workflow/Playground";
import RunBook from "../components/workflow/RunBook";
import AIAssistantButton from "../components/workflow/AIAssistantButton";
import WorkflowAIAssistant from "../components/workflow/WorkflowAIAssistant";

// Drawer width constant
export const DRAWER_WIDTH = 64;

/**
 * WorkflowPage Component
 *
 * A page for editing and managing a specific pipeline workflow.
 * Uses the Playground component for the visual node editor and handles
 * pipeline-specific operations like save, run, spinup/spindown.
 */
export default function WorkflowPage() {
  const [shareAnchorEl, setShareAnchorEl] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isRunBookOpen, setRunBookOpen] = useState(false);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);
  const playgroundRef = useRef(null);
  const navigate = useNavigate();
  const { pipelineId } = useParams();

  const {
    loading,
    setLoading,
    error,
    setError,
    containerId,
    setContainerId,
    user,
    setViewport,
    workflows,
  } = useGlobalContext();

  const {
    edges: currentEdges,
    nodes: currentNodes,
    setNodes: setCurrentNodes,
    setEdges: setCurrentEdges,
    setRfInstance,
    status: currentPipelineStatus,
    setStatus: setCurrentPipelineStatus,
    id: currentPipelineId,
    setId: setCurrentPipelineId,
    rfInstance,
    versionId: currentVersionId,
    setVersionId: setCurrentVersionId,
    workflowData: currentWorkflowData,
    setWorkflowData: setCurrentWorkflowData,
    fullPipeline,
    setFullPipeline,
  } = useGlobalWorkflow();

  // Track loaded pipeline to prevent re-loading
  const loadedPipelineRef = useRef(null);
  const isLoadingRef = useRef(false);
  const viewportDataRef = useRef(null); // Store viewport data for applying when rfInstance is ready

  // Load pipeline data when pipelineId changes (from URL), TODO: check for debounce

  useEffect(() => {
    // Skip if no pipelineId
    if (!pipelineId) {
      // Clear state if no pipelineId
      setCurrentNodes([]);
      setCurrentEdges([]);
      setCurrentPipelineId(null);
      setCurrentVersionId(null);
      setCurrentPipelineStatus("Stopped");
      return;
    }

    // Normalize pipelineId to string for comparison
    const normalizedPipelineId = String(pipelineId);

    // Clear old workflow data immediately when pipelineId changes
    if (loadedPipelineRef.current !== normalizedPipelineId) {
      setCurrentNodes([]);
      setCurrentEdges([]);
      setError(null);
      setLoading(true); // Show loading state immediately
    }

    // Skip if already loading the same pipeline
    if (
      isLoadingRef.current &&
      loadedPipelineRef.current === normalizedPipelineId
    ) {
      return;
    }

    let isMounted = true;
    isLoadingRef.current = true;

    const loadPipelineData = async () => {
      setLoading(true);
      setError(null);

      try {
        // First, try to find the workflow in the workflows list to get current_version_id
        let versionId = null;

        // Check both _id and id fields, and normalize to strings for comparison
        const workflow = workflows?.find((w) => {
          const workflowId = String(w._id || w.id || "");
          return workflowId === normalizedPipelineId;
        });

        if (workflow && workflow.current_version_id) {
          versionId = workflow.current_version_id;
        } else {
          // If not found in workflows list, fetch from retrieve_all
          const workflowResponse = await fetchAllWorkflows();
          if (workflowResponse.status === "success" && workflowResponse.data) {
            const foundWorkflow = workflowResponse.data.find((w) => {
              const workflowId = String(w._id || w.id || "");
              return workflowId === normalizedPipelineId;
            });
            setCurrentWorkflowData(foundWorkflow);
            setCurrentPipelineStatus(foundWorkflow?.status);
            if (foundWorkflow && foundWorkflow.current_version_id) {
              versionId = foundWorkflow.current_version_id;
            }
          }
        }

        if (!versionId) {
          throw new Error(
            "Could not find version ID for this pipeline. The pipeline may not exist or you may not have access to it."
          );
        }

        // Use fetchAndSetPipeline to load the pipeline data
        const result = await fetchAndSetPipeline(pipelineId, versionId, {
          setCurrentPipelineId,
          setCurrentVersionId,
          setError,
          setLoading,
          setCurrentEdges,
          setCurrentNodes,
          setViewport: null, // Don't use setViewport from context, we'll apply it via rfInstance
          setCurrentPipelineStatus,
          setContainerId,
          setFullPipeline, // Store full pipeline data for preserving additional fields
        });

        // Store viewport data for applying when rfInstance is ready
        if (result?.version?.pipeline?.viewport) {
          viewportDataRef.current = result.version.pipeline.viewport;
        }

        // Mark as loaded
        if (isMounted) {
          loadedPipelineRef.current = normalizedPipelineId;
        }
      } catch (err) {
        console.error("Error loading pipeline:", err);
        if (isMounted) {
          setError(err.message || "Failed to load pipeline data");
          setLoading(false);
        }
      } finally {
        if (isMounted) {
          isLoadingRef.current = false;
        }
      }
    };

    loadPipelineData();

    return () => {
      isMounted = false;
      isLoadingRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineId]); // Only depend on pipelineId to avoid infinite loops

  // Reset loaded ref when pipelineId changes (runs before main load effect)
  useEffect(() => {
    if (pipelineId) {
      const normalizedPipelineId = String(pipelineId);
      if (loadedPipelineRef.current !== normalizedPipelineId) {
        // Reset refs for new pipeline (don't reset isLoadingRef here to avoid race condition)
        loadedPipelineRef.current = null;
        viewportDataRef.current = null;
      }
    } else {
      // Clear everything if no pipelineId
      loadedPipelineRef.current = null;
      viewportDataRef.current = null;
      isLoadingRef.current = false;
    }
  }, [pipelineId]);

  // Clear workflow state when component unmounts
  useEffect(() => {
    return () => {
      // Clear workflow state when navigating away
      setCurrentNodes([]);
      setCurrentEdges([]);
      setCurrentPipelineId(null);
      setCurrentVersionId(null);
      setCurrentPipelineStatus("Stopped");
      setRfInstance(null);
      loadedPipelineRef.current = null;
      viewportDataRef.current = null;
      isLoadingRef.current = false;
    };
  }, [
    setCurrentNodes,
    setCurrentEdges,
    setCurrentPipelineId,
    setCurrentVersionId,
    setCurrentPipelineStatus,
    setRfInstance,
  ]);

  // Apply viewport when rfInstance and nodes are ready
  useEffect(() => {
    if (rfInstance && viewportDataRef.current && currentNodes.length > 0) {
      const viewport = viewportDataRef.current;
      try {
        if (rfInstance.setViewport) {
          rfInstance.setViewport(viewport, { duration: 0 });
          viewportDataRef.current = null; // Clear after applying
        } else if (rfInstance.fitView) {
          // Fallback to fitView if setViewport not available
          rfInstance.fitView({ padding: 0.2, maxZoom: 0.9, duration: 0 });
          viewportDataRef.current = null;
        }
      } catch (error) {
        console.error("Error applying viewport:", error);
      }
    }
  }, [rfInstance, currentNodes]);

  // Debug: Log nodes and edges when they change
  useEffect(() => {
    console.log("Current nodes in Workflows page:", {
      count: currentNodes.length,
      nodes: currentNodes,
      edges: currentEdges,
    });
  }, [currentNodes, currentEdges]);

  // Debounced auto-save drafts when nodes/edges change
  const autoSaveTimerRef = useRef(null);
  const isInitialLoadRef = useRef(true);
  const lastSavedDataRef = useRef(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState(null); // 'saving', 'saved', null

  // Auto-save with debounce (2 seconds after last change)
  useEffect(() => {
    // Skip auto-save on initial load
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      return;
    }

    // Skip if missing required data
    if (!currentPipelineId || !currentVersionId || !rfInstance) {
      return;
    }

    // Get current flow data to compare
    const currentFlowData = JSON.stringify({
      nodes: currentNodes,
      edges: currentEdges,
    });

    // Skip if data hasn't changed
    if (lastSavedDataRef.current === currentFlowData) {
      return;
    }

    // Clear previous timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    // Set new debounced save timer (2 seconds)
    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        setAutoSaveStatus("saving");
        await saveDraftsAPI(
          currentVersionId,
          rfInstance,
          setCurrentVersionId,
          currentPipelineId,
          () => {}, // Don't use global loading for auto-save
          (err) => console.warn("Auto-save warning:", err),
          "", // description
          fullPipeline // Pass full pipeline to preserve additional fields like 'agents'
        );
        lastSavedDataRef.current = currentFlowData;
        setAutoSaveStatus("saved");

        // Clear saved status after 2 seconds
        setTimeout(() => setAutoSaveStatus(null), 2000);
      } catch (err) {
        console.error("Auto-save failed:", err);
        setAutoSaveStatus(null);
      }
    }, 2000);

    // Cleanup timer on unmount
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [
    currentNodes,
    currentEdges,
    currentPipelineId,
    currentVersionId,
    rfInstance,
    setCurrentVersionId,
    fullPipeline,
  ]);

  useEffect(() => {
    fetchAndSetPipeline(currentPipelineId, currentVersionId, {
      setCurrentPipelineId,
      setCurrentVersionId,
      setError,
      setLoading,
      setCurrentEdges,
      setCurrentNodes,
      setViewport,
      setCurrentPipelineStatus,
      setContainerId,
    });
  }, []);

  // Pipeline status toggle handler
  const handleToggleStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await togglePipelineStatus(currentPipelineId, currentPipelineStatus);
      // Toggle the status: Running -> Stopped, Stopped -> Running
      const newStatus =
        currentPipelineStatus === "Running" ? "Stopped" : "Running";
      setCurrentPipelineStatus(newStatus);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [
    currentPipelineId,
    currentPipelineStatus,
    setCurrentPipelineStatus,
    setLoading,
    setError,
  ]);

  // Spin up pipeline container
  const handleSpinup = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await spinupPipeline(currentPipelineId);
      setContainerId(data.pipeline_container_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentPipelineId, setContainerId, setLoading, setError]);

  // Spin down pipeline container
  const handleSpindown = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await spindownPipeline(currentPipelineId);
      setContainerId(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentPipelineId, setContainerId, setLoading, setError]);

  // Save pipeline handler
  const handleSave = useCallback(() => {
    savePipelineAPI(
      rfInstance,
      currentPipelineId,
      setCurrentPipelineId,
      currentVersionId,
      setCurrentVersionId,
      setError,
      setLoading
    );
  }, [
    rfInstance,
    currentPipelineId,
    setCurrentPipelineId,
    currentVersionId,
    setCurrentVersionId,
    setError,
    setLoading,
  ]);

  // Share menu handlers
  const handleShareClick = useCallback((event) => {
    setShareAnchorEl(event.currentTarget);
  }, []);

  const handleShareClose = useCallback(() => {
    setShareAnchorEl(null);
  }, []);

  // Export JSON handler
  const handleExportJSON = useCallback(() => {
    if (!rfInstance) {
      setError("No workflow data available to export");
      return;
    }

    try {
      const flowData = rfInstance.toObject();
      const exportData = {
        ...flowData,
        metadata: {
          pipelineName: `Pipeline ${
            pipelineId ? pipelineId.toLowerCase() : "a"
          }`,
          pipelineId: currentPipelineId,
          versionId: currentVersionId,
          exportedAt: new Date().toISOString(),
          exportedBy: user?.name || user?.id || "Unknown",
        },
      };

      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pipeline-${pipelineId || "workflow"}-${
        new Date().toISOString().split("T")[0]
      }.json`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      setError("Failed to export workflow. Please try again.");
    }
  }, [
    rfInstance,
    pipelineId,
    currentPipelineId,
    currentVersionId,
    user,
    setError,
  ]);

  // Navigation handler - refresh state and navigate to workflows page
  const handleBackClick = useCallback(() => {
    // Clear any local state before navigating
    window.location.href = "/workflows";
  }, []);

  // Fullscreen handlers
  const handleEnterFullscreen = useCallback(() => {
    setIsFullscreen(true);
  }, []);

  const handleExitFullscreen = useCallback(() => {
    setIsFullscreen(false);
  }, []);

  // Keyboard shortcut for fullscreen (F key)
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
        return;
      }

      if (e.key === "f" || e.key === "F") {
        if (!isFullscreen) {
          handleEnterFullscreen();
        }
      }

      if (e.key === "Escape" && isFullscreen) {
        handleExitFullscreen();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen, handleEnterFullscreen, handleExitFullscreen]);

  // Node/Edge change handlers for controlled mode
  const handleNodesChange = useCallback(
    (newNodes) => {
      setCurrentNodes(newNodes);
    },
    [setCurrentNodes]
  );

  const handleEdgesChange = useCallback(
    (newEdges) => {
      setCurrentEdges(newEdges);
    },
    [setCurrentEdges]
  );

  return (
    <>
      {/* Fullscreen Mode */}
      {isFullscreen && (
        <Box
          sx={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            zIndex: 9999,
            bgcolor: "background.default",
          }}
        >
          <Playground
            ref={playgroundRef}
            nodes={currentNodes}
            edges={currentEdges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onInit={setRfInstance}
            height="100vh"
            showToolbar={true}
            showFullscreenButton={true}
            isFullscreen={true}
            onExitFullscreen={handleExitFullscreen}
          />
        </Box>
      )}

      {/* Normal Mode */}
      {!isFullscreen && (
        <Box
          sx={{
            transition: "margin-left 0.3s ease",
            left: DRAWER_WIDTH,
            position: "absolute",
            width: `calc(100vw - ${DRAWER_WIDTH}px)`,
            height: "100vh",
            bgcolor: "background.default",
            overflow: "hidden",
          }}
        >
          {/* Pipeline Navigation Bar */}
          {/* TODO: Name rendering */}
          <PipelineNavBar
            onBackClick={handleBackClick}
            pipelineName={`${
              currentWorkflowData?.name || pipelineId
                ? pipelineId.toLowerCase()
                : "Unnamed Workflow"
            }`}
            loading={loading}
            shareAnchorEl={shareAnchorEl}
            onShareClick={handleShareClick}
            onShareClose={handleShareClose}
            onSave={handleSave}
            onSpinup={handleSpinup}
            onSpindown={handleSpindown}
            onToggleStatus={handleToggleStatus}
            currentPipelineStatus={currentPipelineStatus}
            currentPipelineId={currentPipelineId}
            containerId={containerId}
            onFullscreenClick={handleEnterFullscreen}
            onRunBook={() => setRunBookOpen((state) => !state)}
            onExportJSON={handleExportJSON}
            pipelineId={pipelineId}
            userAvatar="https://i.pravatar.cc/40"
            autoSaveStatus={autoSaveStatus}
          />

          <Playground
            ref={playgroundRef}
            nodes={currentNodes}
            edges={currentEdges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onInit={setRfInstance}
            height="calc(100vh - 48px)"
            showToolbar={true}
            showFullscreenButton={false}
          />
        </Box>
      )}

      <RunBook open={isRunBookOpen} onClose={() => setRunBookOpen(false)} />

      {/* AI Assistant Button */}
      {!isFullscreen && (
        <AIAssistantButton onClick={() => setIsAIAssistantOpen(true)} />
      )}

      {/* AI Assistant Sidebar */}
      <WorkflowAIAssistant
        open={isAIAssistantOpen}
        onClose={() => setIsAIAssistantOpen(false)}
      />

      {/* Error Snackbar */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      >
        <Alert
          onClose={() => setError(null)}
          severity="error"
          sx={{ width: "100%" }}
        >
          {error}
        </Alert>
      </Snackbar>
    </>
  );
}
