import { useState, useEffect, useCallback, useRef } from "react";
import {
  Typography,
  Button,
  IconButton,
  Slide,
  Box,
  CircularProgress,
  Snackbar,
  Alert,
  useTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate } from "react-router-dom";
import Playground from "../workflow/Playground";
import StepSidebar, { STEP_SIDEBAR_COLLAPSED_WIDTH } from "./StepSidebar";
import BasicInformationForm from "./BasicInformationForm";
import AddAIAgent from "./AddAIAgent";
import ContractParserWebSocket from "../../utils/contractParserWebSocket";
import { create_pipeline, savePipelineAPI } from "../../utils/pipelineUtils";
import NodeApprovalPopup from "./NodeApprovalPopup";

// Stepper steps configuration
const steps = [
  { id: 1, label: "Basic Information" },
  { id: 2, label: "AI Assistant" },
  { id: 3, label: "Add AI Agents" },
];

const CreateWorkflowDrawer = ({ open, onClose, onComplete }) => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    members: "",
    document: null,
    selectedMembers: [],
    agent: [],
  });
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  // Pipeline nodes and edges state (managed here, passed to Playground)
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [rfInstance, setRfInstance] = useState(null);
  const [agents, setAgents] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // AI chatbot state
  const [isGenerating, setIsGenerating] = useState(false);

  // WebSocket and contract parser state
  const wsRef = useRef(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [proposedNode, setProposedNode] = useState(null);
  const [proposedNodePosition, setProposedNodePosition] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [awaitingInput, setAwaitingInput] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [isRenderingNode, setIsRenderingNode] = useState(false);
  const finalFlowchartRef = useRef(null);
  const rfInstanceRef = useRef(null);
  const renderingTimeoutRef = useRef(null); // Timeout to clear rendering state if flowchart_update doesn't arrive
  const hasSentDescriptionFromChat = useRef(false);

  useEffect(() => {
    if (open) {
      setCurrentStep(1);
      setFormData({
        name: "",
        description: "",
        members: "",
        document: null,
        agent: [],
        selectedMembers: [],
      });
      setNodes([]);
      setEdges([]);
      setRfInstance(null);
      setAgents([]);
      setIsGenerating(false);
      setChatMessages([]);
      setProposedNode(null);
      setProposedNodePosition(null);
      setAwaitingInput(false);
      setWsConnected(false);
      finalFlowchartRef.current = null;
      hasSentDescriptionFromChat.current = false;
    } else {
      // Disconnect WebSocket when drawer closes, TODO: Sure ?
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      // Reset users list when drawer closes to fetch fresh data next time
      setAllUsers([]);
      setLoadingUsers(false);
      hasSentDescriptionFromChat.current = false;
    }
  }, [open]);

  // Automatically open sidebar when reaching step 2, close on step 3
  useEffect(() => {
    if (currentStep === 2) {
      setIsSidebarCollapsed(false);
    } else if (currentStep === 3) {
      setIsSidebarCollapsed(true);
    }
  }, [currentStep]);

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Connect to WebSocket when moving to step 2 (only if description or PDF provided)
  useEffect(() => {
    if (currentStep === 2 && !wsRef.current && open) {
      const hasNoInput = !formData.document && (!formData.description || !formData.description.trim());
      
      console.log("Step 2 - Checking input:", {
        hasDocument: !!formData.document,
        hasDescription: !!formData.description,
        descriptionValue: formData.description,
        hasNoInput: hasNoInput
      });
      
      // If no input provided, show welcome message and don't connect to server
      if (hasNoInput) {
        const welcomeMessage = `### 👋 Welcome to the SLA Definition Assistant

I help you create clear, measurable, and actionable **Service Level Agreements (SLAs)** for your systems.

To get started, please **describe the metrics** you want to track.  

For example: uptime, API latency, error rate, data freshness, support response time, or any custom metric you want to define.

**What metrics would you like to create SLAs for?**`;

        setChatMessages([
          {
            role: "assistant",
            content: welcomeMessage,
          },
        ]);
        setIsGenerating(false);
        setAwaitingInput(true);
        return; // Don't connect to server
      }

      // Connect to WebSocket only if we have input (description or PDF)
      const connectWebSocket = async () => {
        try {
          setIsGenerating(true);
          console.log("Connecting to contract parser agent WebSocket...");
          const ws = new ContractParserWebSocket({
            onOpen: () => {
              setWsConnected(true);
              console.log("WebSocket connected");
            },
            onMessage: (data) => {
              handleWebSocketMessage(data);
            },
            onError: (error) => {
              console.error("WebSocket error:", error);
              setSnackbar({
                open: true,
                message: "Failed to connect to AI agent",
                severity: "error",
              });
              setIsGenerating(false);
            },
            onClose: () => {
              setWsConnected(false);
              setIsGenerating(false);
            },
            onNodeProposed: (data) => {
              handleNodeProposed(data);
            },
            onFlowchartUpdate: (data) => {
              // Handle flowchart updates (when flowchart.json is updated)
              // Merge with existing nodes to keep all previously approved nodes
              console.log("[WebSocket] flowchart_update received via callback - CLEARING RENDERING STATE NOW");
              console.log("[WebSocket] flowchart_update details:", {
                nodeCount: data.flowchart?.nodes?.length || 0,
                edgeCount: data.flowchart?.edges?.length || 0,
                nodeIds: data.flowchart?.nodes?.map(n => n.id) || [],
              });
              // Clear timeout since flowchart_update arrived
              if (renderingTimeoutRef.current) {
                clearTimeout(renderingTimeoutRef.current);
                renderingTimeoutRef.current = null;
                console.log("[WebSocket] Cleared rendering timeout in callback");
              }
              // IMPORTANT: Clear rendering state IMMEDIATELY before merge
              setIsRenderingNode(false);
              setIsGenerating(false);
              if (data.flowchart) {
                updateNodesFromFlowchart(data.flowchart, true); // true = merge with existing
              }
              // Clear proposed node state after merge
              setProposedNode(null);
              setProposedNodePosition(null);
              console.log("[WebSocket] flowchart_update callback complete - isRenderingNode cleared");
            },
            onFinal: async (data) => {
              // Store final flowchart - don't save yet, wait for Create button
              console.log("Final flowchart received:", data);
              if (data.flowchart) {
                finalFlowchartRef.current = data.flowchart;
                // Update nodes/edges from final flowchart (process them first)
                await updateNodesFromFlowchart(data.flowchart);
                // Don't save to MongoDB here - will save when Create button is clicked
                setChatMessages((prev) => [
                  ...prev,
                  {
                    role: "system",
                    content:
                      "Workflow generation complete! Click 'Next' to review and then 'Create' to save.",
                  },
                ]);
              }
            },
          });

          // Determine what to send: PDF (with optional description) or description only
          let initialData = null;

          console.log("Preparing initial data:", {
            hasDocument: !!formData.document,
            hasDescription: !!formData.description,
            descriptionValue: formData.description
          });

          if (
            formData.document &&
            formData.document.type === "application/pdf"
          ) {
            // Upload PDF first, then send path with description as additional context
            console.log("Uploading PDF file:", formData.document.name);
            try {
              const formDataUpload = new FormData();
              formDataUpload.append("file", formData.document);

              // Get base URL for HTTP requests (not WebSocket URL)
              const baseUrl = import.meta.env.VITE_CONTRACT_PARSER || "http://localhost:8001";
              // Remove /ws if present, and ensure we have the base HTTP URL
              // Convert ws:// to http:// and remove trailing /ws
              let httpBaseUrl = baseUrl.replace(/\/ws$/, "").replace(/^ws:\/\//, "http://");
              // If it's still a WebSocket URL format, convert it
              if (httpBaseUrl.startsWith("ws://")) {
                httpBaseUrl = httpBaseUrl.replace(/^ws:\/\//, "http://");
              }
              
              console.log("[PDF Upload] Base URL:", baseUrl);
              console.log("[PDF Upload] HTTP Base URL:", httpBaseUrl);
              console.log("[PDF Upload] Uploading to:", `${httpBaseUrl}/upload-pdf`);

              const uploadResponse = await fetch(
                `${httpBaseUrl}/upload-pdf`,
                {
                  method: "POST",
                  body: formDataUpload,
                }
              );

              if (!uploadResponse.ok) {
                throw new Error(
                  `Failed to upload PDF: ${uploadResponse.statusText}`
                );
              }

              const uploadResult = await uploadResponse.json();
              console.log("PDF uploaded successfully:", uploadResult);

              // Send PDF path to WebSocket, with description as additional context if provided
              initialData = {
                pdf_path: uploadResult.pdf_path,
              };

              // Include description as additional context if provided
              if (formData.description && formData.description.trim()) {
                initialData.description = formData.description;
                console.log(
                  "Including description as additional context with PDF"
                );
              }
            } catch (error) {
              console.error("Error uploading PDF:", error);
              setSnackbar({
                open: true,
                message: `Failed to upload PDF: ${error.message}`,
                severity: "error",
              });
              setIsGenerating(false);
              return;
            }
          } else if (formData.description && formData.description.trim()) {
            // Format description into metrics (option 2)
            console.log("Formatting description as metrics:", formData.description);
            const descriptionValue = formData.description.trim();
            const metrics = ContractParserWebSocket.formatDescriptionToMetrics(
              descriptionValue
            );
            console.log("Formatted metrics:", metrics);
            initialData = { metrics };
            console.log("Initial data with metrics:", initialData);
          } else {
            // This shouldn't happen if hasNoInput check worked, but add safety check
            console.error("No initial data to send - this should not happen", {
              hasDocument: !!formData.document,
              hasDescription: !!formData.description,
              descriptionValue: formData.description
            });
            setSnackbar({
              open: true,
              message: "Please provide a description or upload a PDF",
              severity: "error",
            });
            setIsGenerating(false);
            return;
          }

          // Ensure initialData is set before connecting
          if (!initialData) {
            console.error("initialData is null - cannot connect", {
              hasDocument: !!formData.document,
              hasDescription: !!formData.description,
              descriptionValue: formData.description,
              documentType: formData.document?.type
            });
            setSnackbar({
              open: true,
              message: "No data to send to server. Please provide a description or upload a PDF.",
              severity: "error",
            });
            setIsGenerating(false);
            return;
          }

          console.log("Connecting to WebSocket with initial data:", initialData);
          // Connect and send initial data
          await ws.connect(initialData);
          wsRef.current = ws;
          console.log("WebSocket connection established");
        } catch (error) {
          console.error("Error connecting WebSocket:", error);
          setSnackbar({
            open: true,
            message: "Failed to connect to AI agent",
            severity: "error",
          });
          setIsGenerating(false);
        }
      };

      connectWebSocket();
    }

    return () => {
      // Cleanup on unmount or step change
      if (currentStep !== 2 && wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
        setWsConnected(false);
      }
      // Clear rendering timeout on cleanup
      if (renderingTimeoutRef.current) {
        clearTimeout(renderingTimeoutRef.current);
        renderingTimeoutRef.current = null;
      }
    };
  }, [currentStep, open]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data) => {
    const msgType = data.type;

    switch (msgType) {
      case "session_start":
        // If no input was provided and we haven't sent description from chat yet,
        // don't show session_start message, keep welcome message
        const hasNoInput = !formData.document && (!formData.description || !formData.description.trim());
        if (!hasNoInput || hasSentDescriptionFromChat.current) {
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: data.message || "Session started" },
        ]);
          // When description/PDF is provided, stop generating after session starts
          setIsGenerating(false);
        } else {
          // Ensure generating is false and input is enabled when we have welcome message
          setIsGenerating(false);
          setAwaitingInput(true);
        }
        break;

      case "phase":
        // If no input was provided and we haven't sent description from chat yet,
        // don't show phase messages, keep welcome message
        const hasNoInputPhase = !formData.document && (!formData.description || !formData.description.trim());
        if (!hasNoInputPhase || hasSentDescriptionFromChat.current) {
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: `\n${data.message}\n` },
        ]);
          // When description/PDF is provided, ensure generating is false when phase messages arrive
          setIsGenerating(false);
        }
        break;

      case "agent_response":
        // Remove "Agent:" prefix if present at the start of the message
        let agentMessage = data.message || "";
        if (agentMessage.startsWith("Agent:")) {
          agentMessage = agentMessage.substring(6).trim();
        }
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: agentMessage },
        ]);
        // Keep isGenerating true to show "Generating workflow..." during the 1 second delay
        // await_input will set it to false when it arrives
        // This allows the frontend to show the loading state during the delay
        break;

      case "await_input":
        // Server is waiting for user input - always enable input
        console.log("[WebSocket] Server awaiting input - enabling chatbox");
        setAwaitingInput(true);
        setIsGenerating(false); // Stop showing "Generating..." and enable input
        
        // Only add "Waiting for your response..." message if we already have messages
        // (to avoid showing it when we have the welcome message at the very start)
        const hasNoInputCheck = !formData.document && (!formData.description || !formData.description.trim());
        if (hasNoInputCheck && !hasSentDescriptionFromChat.current) {
          // Don't add this message, keep the welcome message
          // But still ensure input is enabled (already done above)
        } else {
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: "Waiting for your response..." },
        ]);
        }
        break;

      case "phase1_complete":
        // Phase 1 complete - all nodes should already be there from individual approvals
        // But merge anyway to ensure everything is correct (merge=true to keep any proposed nodes)
        console.log("[WebSocket] Phase 1 complete - merging final flowchart");
        if (data.flowchart) {
          updateNodesFromFlowchart(data.flowchart, true); // true = merge with existing
        }
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: "Phase 1 Complete!" },
        ]);
        setIsGenerating(false);
        break;

      case "node_approved":
        // Node was approved - flowchart_update should come immediately after this
        // DO NOT update nodes/edges here - flowchart_update will merge everything correctly
        // The flowchart_update will include ALL nodes (previous + newly approved)
        console.log("[WebSocket] Node approved - flowchart_update should arrive next with all nodes");
        // Keep isRenderingNode true until flowchart_update arrives and completes the merge
        // Set a timeout fallback to clear it if flowchart_update doesn't arrive within 3 seconds
        if (renderingTimeoutRef.current) {
          clearTimeout(renderingTimeoutRef.current);
        }
        renderingTimeoutRef.current = setTimeout(() => {
          console.warn("[WebSocket] Timeout: flowchart_update didn't arrive, clearing rendering state");
          setIsRenderingNode(false);
          setIsGenerating(false);
        }, 3000); // 3 second timeout
        setIsGenerating(false);
        break;

      case "flowchart_update":
        // Flowchart update - merge with existing nodes to keep all previously accepted nodes
        console.log("[WebSocket] flowchart_update received in message handler - CLEARING RENDERING STATE NOW");
        // Clear timeout since flowchart_update arrived
        if (renderingTimeoutRef.current) {
          clearTimeout(renderingTimeoutRef.current);
          renderingTimeoutRef.current = null;
          console.log("[WebSocket] Cleared rendering timeout in message handler");
        }
        // IMPORTANT: Clear rendering state IMMEDIATELY before merge
        setIsRenderingNode(false);
        setIsGenerating(false);
        if (data.flowchart) {
          console.log("[WebSocket] flowchart_update - calling updateNodesFromFlowchart with merge=true");
          updateNodesFromFlowchart(data.flowchart, true); // true = merge with existing
        }
        // Clear proposed node state after merge
        setProposedNode(null);
        setProposedNodePosition(null);
        console.log("[WebSocket] flowchart_update message handler complete - isRenderingNode cleared");
        break;

      case "phase2_complete":
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: data.message || "Phase 2 Complete!" },
        ]);
        break;

      case "done":
        setChatMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `Session ended: ${data.reason || "complete"}`,
          },
        ]);
        setIsGenerating(false);
        break;

      case "error":
        setChatMessages((prev) => [
          ...prev,
          { role: "error", content: `Error: ${data.message}` },
        ]);
        setIsGenerating(false);
        break;

      case "status":
        setChatMessages((prev) => [
          ...prev,
          { role: "system", content: data.message },
        ]);
        break;
    }
  }, [formData.document, formData.description]);

  // Handle node proposed - render immediately with proper processing
  const handleNodeProposed = useCallback(async (data) => {
    const node = data.node;

    // Use position from JSON - it's the correct final position
    // The node should appear exactly where it will be in the final workflow
    let nodePosition = node.position;
    if (
      !nodePosition ||
      typeof nodePosition.x !== "number" ||
      typeof nodePosition.y !== "number"
    ) {
      // Only default if position is truly missing - but it should always be in JSON
      console.warn("[Node Proposed] Node missing position, using default:", node.id);
      nodePosition = { x: 0, y: 0 };
    } else {
      console.log("[Node Proposed] Using position from JSON:", {
        nodeId: node.id,
        position: nodePosition,
      });
    }

    // Process the node immediately to ensure it renders properly
    try {
      const { add_to_node_types } = await import("../../utils/pipelineUtils");
      await add_to_node_types([node]);

      // Ensure type is set
      if (!node.type && node.node_id) {
        node.type = node.node_id;
      } else if (!node.type) {
        node.type = "default";
      }

      // Ensure data structure is correct
      if (!node.data) {
        node.data = {};
      }
      if (!node.data.properties) {
        node.data.properties = node.properties || {};
      }
    } catch (error) {
      console.error("Error processing proposed node:", error);
    }

    // Add proposed node to canvas - render it immediately with proper structure
    // Use the position from the node (from JSON) - it's the correct final position
    const tempNode = {
      ...node,
      id: `proposed-${node.id}`,
      position: nodePosition, // Use position from JSON - this is where it will finally be
      data: {
        ...node.data,
        isProposed: true,
      },
    };

    setProposedNode(tempNode);
    setProposedNodePosition(nodePosition);
    
    console.log("[Node Proposed] Node will be rendered at position from JSON:", {
      nodeId: node.id,
      position: nodePosition,
      finalPosition: nodePosition, // Same position - no repositioning needed
    });

    // Add to nodes immediately for visualization (already processed)
    // CRITICAL: Keep ALL previously accepted nodes + add the new proposed node
    // Only remove the previous proposed node (if any), but keep ALL approved nodes
    setNodes((prev) => {
      console.log("[Node Proposed] Current nodes before adding proposed:", prev.length, "IDs:", prev.map(n => n.id));
      
      // Get the ID of the previous proposed node (if any)
      const previousProposedId = proposedNode?.id;

      // Filter: Keep ALL approved nodes + the new proposed node, remove only the old proposed node
      const filtered = prev.filter((n) => {
        // Keep all approved nodes (don't start with "proposed-")
        if (!n.id.startsWith("proposed-")) {
          return true; // Keep all approved nodes
        }
        // Remove only the previous proposed node (if it exists and is different from new one)
        if (previousProposedId && n.id === previousProposedId) {
          return false; // Remove the old proposed node
        }
        // Keep the new proposed node if it's already in the list
        if (n.id === tempNode.id) {
          return true;
        }
        // Remove any other proposed nodes (shouldn't happen, but just in case)
        return false;
      });

      // Check if the new proposed node is already in the list
      const nodeExists = filtered.some((n) => n.id === tempNode.id);

      // Ensure all nodes have valid positions
      const validatedFiltered = filtered.map((n) => {
        if (
          !n.position ||
          typeof n.position.x !== "number" ||
          typeof n.position.y !== "number"
        ) {
          return {
            ...n,
            position: { x: 0, y: 0 },
          };
        }
        return n;
      });

      // Add the new proposed node if it doesn't exist
      const result = nodeExists ? validatedFiltered : [...validatedFiltered, tempNode];
      
      console.log("[Node Proposed] Nodes after adding proposed:", result.length, "IDs:", result.map(n => n.id));
      console.log("[Node Proposed] Approved nodes count:", result.filter(n => !n.id.startsWith("proposed-")).length);
      
      return result;
    });

    // Also add edges immediately if provided
    if (data.edges && data.edges.length > 0) {
      setEdges((prev) => {
        // Get the ID of the previous proposed node (if any)
        const previousProposedId = proposedNode?.id;

        const newEdges = data.edges.map((edge) => {
          // Convert source/target to use proposed- prefix for the new proposed node
          let source = edge.source;
          let target = edge.target;

          // If source is the new node, add proposed- prefix
          if (source === node.id) {
            source = `proposed-${node.id}`;
          }
          // If target is the new node, add proposed- prefix
          if (target === node.id) {
            target = `proposed-${node.id}`;
          }

          return {
            ...edge,
            source: source,
            target: target,
          };
        });

        // Remove only edges that connect to the previous proposed node
        // Keep all other edges (including those connecting approved nodes)
        const filtered = prev.filter((e) => {
          // Keep edges that don't involve any proposed nodes (these are between approved nodes)
          if (
            !e.source?.startsWith("proposed-") &&
            !e.target?.startsWith("proposed-")
          ) {
            return true;
          }
          // Remove edges that connect to the previous proposed node
          // But keep edges that might connect approved nodes to other approved nodes
          if (previousProposedId) {
            return !(
              e.source === previousProposedId || e.target === previousProposedId
            );
          }
          // If no previous proposed node, remove all proposed edges (they'll be replaced)
          return false;
        });

        return [...filtered, ...newEdges];
      });
    }

    // Don't reposition the node - use the position from JSON
    // The node should appear at its final position from the start
    // Only fit viewport to show all nodes if needed
    setTimeout(() => {
      if (rfInstanceRef.current) {
        try {
          const rfInstance = rfInstanceRef.current;

          // Get the node dimensions (default if not available)
          const nodeWidth = tempNode.measured?.width || 200;
          const nodeHeight = tempNode.measured?.height || 100;

          // Get ReactFlow container element to get actual dimensions
          const reactFlowElement = rfInstance.getViewport();
          const reactFlowContainer = document.querySelector(".react-flow");
          const containerRect = reactFlowContainer?.getBoundingClientRect();

          // Get actual container dimensions
          const containerWidth =
            containerRect?.width || window.innerWidth - 600;
          const containerHeight = containerRect?.height || window.innerHeight;

          // Use the node's position from JSON (already set in nodePosition)
          // Just ensure it's visible in viewport
          const nodeX = nodePosition.x;
          const nodeY = nodePosition.y;
          
          // Check if node is visible, if not, adjust viewport slightly
          const currentViewport = rfInstance.getViewport();
          const zoom = currentViewport.zoom || 1;
          
          // Calculate if node is in viewport
          const nodeScreenX = (nodeX - currentViewport.x) * zoom;
          const nodeScreenY = (nodeY - currentViewport.y) * zoom;
          
          // If node is outside viewport, center viewport on all nodes
          if (nodeScreenX < 0 || nodeScreenX > containerWidth || 
              nodeScreenY < 0 || nodeScreenY > containerHeight) {
            // Fit view to show all nodes
            rfInstance.fitView({ padding: 0.2, includeHiddenNodes: false });
          }
          
          // Don't reposition the node - it's already at the correct position from JSON
          // The node should appear exactly where it will be in the final workflow
          console.log("[Node Proposed] Node rendered at JSON position:", {
            nodeId: node.id,
            position: nodePosition,
          });
        } catch (error) {
          console.error("Error checking viewport for proposed node:", error);
          // Fallback: use fitView to show all nodes if needed
          try {
            rfInstanceRef.current.fitView({ padding: 0.2, duration: 500 });
          } catch (fallbackError) {
            console.error("Fallback fitView also failed:", fallbackError);
          }
        }
      }
    }, 300); // Small delay to ensure node is rendered
  }, []);

  // Update nodes from flowchart
  const updateNodesFromFlowchart = useCallback(async (flowchart, mergeWithExisting = false) => {
    if (flowchart.nodes && flowchart.edges) {
      console.log("Updating nodes from flowchart:", {
        nodeCount: flowchart.nodes.length,
        edgeCount: flowchart.edges.length,
        mergeWithExisting: mergeWithExisting,
      });

      // Remove proposed nodes from the new flowchart
      const cleanNodes = flowchart.nodes.filter(
        (n) => !n.id.startsWith("proposed-")
      );

      // Process nodes to ensure they have proper types and structure
      try {
        const { add_to_node_types } = await import("../../utils/pipelineUtils");
        if (cleanNodes.length > 0) {
          await add_to_node_types(cleanNodes);
        }

        // Validate and ensure nodes have required properties
        const validatedNodes = cleanNodes.map((node, index) => {
          // Ensure node has required properties
          if (!node.id) {
            console.warn("Node missing id:", node);
            node.id = `node-${index}`;
          }

          // Ensure position exists - use the position from flowchart (it should be correct)
          if (
            !node.position ||
            typeof node.position.x !== "number" ||
            typeof node.position.y !== "number"
          ) {
            console.warn("Node missing or invalid position:", node);
            node.position = node.position || { x: index * 250, y: index * 150 };
          }

          // Ensure type exists - use node_id if type is missing
          if (!node.type && node.node_id) {
            node.type = node.node_id;
          } else if (!node.type) {
            console.warn("Node missing both type and node_id:", node);
            node.type = "default";
          }

          // Ensure data exists
          if (!node.data) {
            node.data = {};
          }

          return node;
        });

        if (mergeWithExisting) {
          // Merge with existing nodes - keep all existing approved nodes, update/add new ones
          // The flowchart_update contains ALL nodes (Phase 1 + all Phase 2 accepted so far)
          // So we should use validatedNodes as the source of truth, but also keep any proposed nodes
          // that haven't been replaced yet
          setNodes((prevNodes) => {
            console.log("[Merge] Starting merge:");
            console.log("  - Previous nodes:", prevNodes.length, "IDs:", prevNodes.map(n => n.id));
            console.log("  - Flowchart nodes:", validatedNodes.length, "IDs:", validatedNodes.map(n => n.id));
            
            // Simple merge: use flowchart nodes as source of truth, keep any proposed nodes
            const flowchartNodeIds = new Set(validatedNodes.map(n => n.id));
            const proposedNodes = prevNodes.filter(n => 
              n.id.startsWith("proposed-") && 
              !flowchartNodeIds.has(n.id.replace("proposed-", ""))
            );
            
            const finalNodes = [
              ...validatedNodes, // All accepted nodes from flowchart (with correct JSON positions)
              ...proposedNodes,  // Any proposed nodes that haven't been accepted yet
            ];

            console.log("[Merge] Final result:", {
              previousCount: prevNodes.length,
              previousApprovedCount: prevNodes.filter(n => !n.id.startsWith("proposed-")).length,
              flowchartNodesCount: validatedNodes.length,
              proposedNodesCount: proposedNodes.length,
              finalCount: finalNodes.length,
              finalNodeIds: finalNodes.map(n => n.id),
            });

            // Verify: flowchart should include all previously accepted nodes
            const previousApprovedIds = prevNodes
              .filter(n => !n.id.startsWith("proposed-"))
              .map(n => n.id);
            const missingNodes = previousApprovedIds.filter(id => !flowchartNodeIds.has(id));
            if (missingNodes.length > 0) {
              console.error("[Merge] ERROR: Previously accepted nodes missing from flowchart:", missingNodes);
              console.error("[Merge] Keeping them anyway as a safety measure");
            }

            return finalNodes;
          });
          
          // Log after state update is queued
          console.log("[Merge] State update queued - nodes should now include all accepted nodes");

          // Merge edges - replace all edges with the ones from flowchart
          // (flowchart should have all edges including connections to old nodes)
          const flowchartEdges = flowchart.edges || [];
          console.log("[Merge] Setting edges from flowchart:", flowchartEdges.length, "edges");
          console.log("[Merge] Edge details:", flowchartEdges.map(e => `${e.source} -> ${e.target}`));
          setEdges(flowchartEdges);
          
          console.log("[Merge] COMPLETE - All nodes and edges should now be visible");
        } else {
          // Replace all nodes (for final update or phase1_complete)
          console.log("Replacing all nodes with validated nodes:", validatedNodes);
        setNodes(validatedNodes);
        setEdges(flowchart.edges || []);
        }
      } catch (error) {
        console.error("Error processing nodes:", error);
        // Fallback: set nodes without processing
        if (mergeWithExisting) {
          setNodes((prevNodes) => {
            const existingNodesMap = new Map();
            prevNodes.forEach((n) => {
              if (!n.id.startsWith("proposed-")) {
                existingNodesMap.set(n.id, n);
              }
            });
            cleanNodes.forEach((newNode) => {
              existingNodesMap.set(newNode.id, newNode);
            });
            return Array.from(existingNodesMap.values());
          });
        } else {
        setNodes(cleanNodes);
        }
        setEdges(flowchart.edges || []);
      }
    }
  }, []);

  // Handle node approval
  // Handle node approval - just remove dialog and continue (node already rendered)
  const handleNodeApproval = useCallback((action) => {
    if (!wsRef.current) return;

    if (action === "approve") {
      // Node is already rendered, just send approval and freeze buttons
      wsRef.current.sendApproval("approve");
      setIsRenderingNode(true); // Freeze buttons and show "Rendering node..."
      setIsGenerating(false);
    } else if (action === "reject") {
      // Feedback will be sent via handleNodeRejection
    }
  }, []);

  // Handle node rejection - send feedback, remove node, server will regenerate
  const handleNodeRejection = useCallback((feedback) => {
    if (!wsRef.current) return;
    setIsRenderingNode(false); // Unfreeze buttons when rejecting
    // Send feedback and remove proposed node (server will regenerate)
    wsRef.current.sendApproval("reject", feedback);
    // Remove proposed node from canvas (server will send new one)
    setNodes((prev) => prev.filter((n) => !n.id.startsWith("proposed-")));
    setEdges((prev) =>
      prev.filter(
        (e) =>
          !(e.source && e.source.startsWith("proposed-")) &&
          !(e.target && e.target.startsWith("proposed-"))
      )
    );
    setProposedNode(null);
    setProposedNodePosition(null);
    setIsGenerating(true); // Show generating while waiting for regenerated node
  }, []);

  // Save final flowchart to MongoDB
  // const saveFinalFlowchart = useCallback(
  //   async (flowchart) => {
  //     try {
  //       console.log("Saving final flowchart to MongoDB:", {
  //         nodeCount: flowchart.nodes?.length || 0,
  //         edgeCount: flowchart.edges?.length || 0,
  //         name: formData.name,
  //         description: formData.description,
  //       });

  //       const viewerIds = formData.selectedMembers.map((user) =>
  //         String(user.id)
  //       );

  //       // Process nodes before saving to ensure they're valid
  //       const processedNodes = flowchart.nodes || [];
  //       if (processedNodes.length > 0) {
  //         try {
  //           const { add_to_node_types } = await import(
  //             "../../utils/pipelineUtils"
  //           );
  //           await add_to_node_types(processedNodes);
  //         } catch (error) {
  //           console.warn("Error processing nodes before save:", error);
  //         }
  //       }

  //       const pipeline = {
  //         nodes: processedNodes,
  //         edges: flowchart.edges || [],
  //         viewport: flowchart.viewport || { x: 0, y: 0, zoom: 1 },
  //       };

  //       const result = await createPipelineWithDetails(
  //         formData.name,
  //         formData.description,
  //         viewerIds,
  //         pipeline
  //       );

  //       console.log("Pipeline created successfully:", result);

  //       // Extract pipeline and version IDs from response
  //       const pipelineId =
  //         result.pipeline_id || result.id || result.workflow_id;
  //       const versionId = result.version_id || result.current_version_id;

  //       console.log(
  //         "Extracted IDs - Pipeline ID:",
  //         pipelineId,
  //         "Version ID:",
  //         versionId
  //       );

  //       if (!pipelineId || !versionId) {
  //         console.warn(
  //           "Missing pipeline_id or version_id in response:",
  //           result
  //         );
  //         throw new Error("Pipeline created but missing IDs in response");
  //       }

  //       setSnackbar({
  //         open: true,
  //         message: `Pipeline saved successfully! ID: ${pipelineId}`,
  //         severity: "success",
  //       });

  //       // Trigger completion callback with the result
  //       if (onComplete) {
  //         console.log("Calling onComplete with:", {
  //           pipelineId,
  //           versionId,
  //           nodeCount: processedNodes.length,
  //           edgeCount: pipeline.edges.length,
  //         });
  //         onComplete({
  //           ...formData,
  //           nodes: processedNodes,
  //           edges: pipeline.edges,
  //           pipelineId: pipelineId,
  //           versionId: versionId,
  //         });
  //       }

  //       // Close drawer after a short delay to show success message
  //       setTimeout(() => {
  //         onClose();
  //       }, 2000);
  //     } catch (error) {
  //       console.error("Error saving final flowchart:", error);
  //       setSnackbar({
  //         open: true,
  //         message: `Failed to save pipeline: ${error.message}`,
  //         severity: "error",
  //       });
  //     }
  //   },
  //   [formData, onComplete]
  // );

  // Send user input to WebSocket
  const sendUserInput = useCallback(
    async (message) => {
      // Check if we have no initial input (no description, no PDF, and WebSocket not connected)
      const hasNoInitialInput = !formData.document && (!formData.description || !formData.description.trim());
      const isNotConnected = !wsRef.current || !wsConnected;
      
      // If no input was provided initially and WebSocket is not connected, connect now with user's message
      if (hasNoInitialInput && isNotConnected && !hasSentDescriptionFromChat.current) {
        console.log("No initial input provided. Connecting to server with first chat message as description.");
        
        // Add user message to chat first - remove "You:" prefix if present
        let userMessage = message || "";
        if (userMessage.startsWith("You:")) {
          userMessage = userMessage.substring(4).trim();
        }
        setChatMessages((prev) => [
          ...prev,
          { role: "user", content: userMessage },
        ]);
        
        // Update formData with the description
        setFormData((prev) => ({
          ...prev,
          description: message.trim(),
        }));
        
        // Format the message as description (metrics)
        const metrics = ContractParserWebSocket.formatDescriptionToMetrics(message.trim());
        
        // Connect to WebSocket with description as initial data
        try {
          setIsGenerating(true);
          setAwaitingInput(false);
          
          const ws = new ContractParserWebSocket({
            onOpen: () => {
              setWsConnected(true);
              console.log("WebSocket connected with description from chat");
            },
            onMessage: (data) => {
              handleWebSocketMessage(data);
            },
            onError: (error) => {
              console.error("WebSocket error:", error);
              setSnackbar({
                open: true,
                message: "Failed to connect to AI agent",
                severity: "error",
              });
              setIsGenerating(false);
            },
            onClose: () => {
              setWsConnected(false);
              setIsGenerating(false);
            },
            onNodeProposed: (data) => {
              handleNodeProposed(data);
            },
            onFlowchartUpdate: (data) => {
              // Merge with existing nodes to keep all previously approved nodes
              console.log("[WebSocket] flowchart_update received via callback (chat input) - CLEARING RENDERING STATE NOW");
              console.log("[WebSocket] flowchart_update details:", {
                nodeCount: data.flowchart?.nodes?.length || 0,
                nodeIds: data.flowchart?.nodes?.map(n => n.id) || [],
              });
              // Clear timeout since flowchart_update arrived
              if (renderingTimeoutRef.current) {
                clearTimeout(renderingTimeoutRef.current);
                renderingTimeoutRef.current = null;
                console.log("[WebSocket] Cleared rendering timeout in callback (chat input)");
              }
              // IMPORTANT: Clear rendering state IMMEDIATELY before merge
              setIsRenderingNode(false);
              setIsGenerating(false);
              if (data.flowchart) {
                updateNodesFromFlowchart(data.flowchart, true); // true = merge with existing
              }
              // Clear proposed node state after merge
              setProposedNode(null);
              setProposedNodePosition(null);
              console.log("[WebSocket] flowchart_update callback (chat input) complete - isRenderingNode cleared");
            },
            onFinal: async (data) => {
              console.log("Final flowchart received:", data);
              if (data.flowchart) {
                finalFlowchartRef.current = data.flowchart;
                await updateNodesFromFlowchart(data.flowchart);
                setChatMessages((prev) => [
                  ...prev,
                  {
                    role: "system",
                    content:
                      "Workflow generation complete! Click 'Next' to review and then 'Create' to save.",
                  },
                ]);
              }
            },
          });

          const initialData = { metrics };
          await ws.connect(initialData);
          wsRef.current = ws;
          hasSentDescriptionFromChat.current = true;
        } catch (error) {
          console.error("Error connecting WebSocket:", error);
          setSnackbar({
            open: true,
            message: "Failed to connect to AI agent",
            severity: "error",
          });
          setIsGenerating(false);
        }
      } else if (wsRef.current && wsConnected) {
        // Normal message sending (WebSocket already connected)
        console.log("Sending user input to server:", message);
        wsRef.current.sendUserInput(message);
        // Remove "You:" prefix if present
        let userMessage = message || "";
        if (userMessage.startsWith("You:")) {
          userMessage = userMessage.substring(4).trim();
        }
        setChatMessages((prev) => [
          ...prev,
          { role: "user", content: userMessage },
        ]);
        setAwaitingInput(false);
        setIsGenerating(true); // Show generating while waiting for response
      } else {
        console.warn("Cannot send message: WebSocket not connected");
      }
    },
    [wsConnected, formData.description, formData.document, handleWebSocketMessage, handleNodeProposed, updateNodesFromFlowchart, setSnackbar]
  );

  const handleNext = async () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    } else {
      // Step 3: Create workflow with all details using the new API
      setIsCreating(true);
      try {
        // Always use current nodes and edges state (includes user changes)
        // Remove any "proposed-" prefixes from node IDs
        const currentNodes = (nodes || []).map((node) => {
          // Remove "proposed-" prefix if present
          const cleanId = node.id.startsWith("proposed-")
            ? node.id.replace("proposed-", "")
            : node.id;
          return {
            ...node,
            id: cleanId,
            data: {
              ...node.data,
              isProposed: false, // Ensure isProposed is false
            },
          };
        });

        // Clean up edges - remove "proposed-" prefix and ensure they reference valid nodes
        const currentEdges = (edges || [])
          .map((edge) => ({
            ...edge,
            source: edge.source?.startsWith("proposed-")
              ? edge.source.replace("proposed-", "")
              : edge.source,
            target: edge.target?.startsWith("proposed-")
              ? edge.target.replace("proposed-", "")
              : edge.target,
          }))
          .filter((edge) => {
            // Only keep edges where both source and target nodes exist
            const sourceExists = currentNodes.some((n) => n.id === edge.source);
            const targetExists = currentNodes.some((n) => n.id === edge.target);
            return sourceExists && targetExists;
          });

        // Get current viewport from ReactFlow instance
        let currentViewport = { x: 0, y: 0, zoom: 1 };
        if (rfInstanceRef.current) {
          try {
            const viewport = rfInstanceRef.current.getViewport();
            const zoom = rfInstanceRef.current.getZoom();
            currentViewport = {
              x: viewport.x || 0,
              y: viewport.y || 0,
              zoom: zoom || 1,
            };
          } catch (error) {
            console.warn("Error getting viewport:", error);
          }
        }
        // Extract viewer IDs from selected members
        const viewerIds = formData.selectedMembers.map((user) =>
          String(user.id)
        );

        // Process nodes before saving to ensure they're valid, TODO: check ?
        if (currentNodes.length > 0) {
          try {
            const { add_to_node_types } = await import(
              "../../utils/pipelineUtils"
            );
            await add_to_node_types(currentNodes);
          } catch (error) {
            console.warn("Error processing nodes before save:", error);
          }
        }

        // Build pipeline structure from nodes and edges
        const pipeline = {
          nodes: currentNodes || [],
          edges: currentEdges || [],
          agents: agents || [],
          viewport: currentViewport,
        };

        // Step 1: Create the pipeline
        let newPipelineId = null;
        let newVersionId = null;

        await create_pipeline(
          formData.name || "New Workflow",
          (id) => {
            newPipelineId = id;
          },
          (id) => {
            newVersionId = id;
          },
          (error) => {
            throw new Error(error);
          },
          () => {} // setLoading - we handle our own loading state
        );

        if (!newPipelineId || !newVersionId) {
          throw new Error("Failed to create pipeline - no ID returned");
        }

        // Step 2: Save the pipeline with nodes, edges, and viewport
        const saveResponse = await fetch(
          `${import.meta.env.VITE_API_SERVER}/version/save`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              version_updated_at: new Date().toISOString(),
              version_description: formData.description || "",
              current_version_id: newVersionId,
              workflow_id: newPipelineId,
              pipeline: pipeline,
            }),
          }
        );

        if (!saveResponse.ok) {
          const errText = await saveResponse.text();
          throw new Error(
            `Failed to save pipeline: ${errText || saveResponse.status}`
          );
        }

        const saveData = await saveResponse.json();

        // Show success message
        setSnackbar({
          open: true,
          message: "Pipeline created successfully!",
          severity: "success",
        });

        // Get the final pipeline ID
        const finalPipelineId = saveData.workflow_id || newPipelineId;

        // Complete workflow creation
        if (onComplete) {
          onComplete({
            name: formData.name,
            description: formData.description,
            selectedMembers: formData.selectedMembers,
            viewerIds: viewerIds,
            currentNodes,
            currentEdges,
            currentViewport,
            agents,
            pipelineId: finalPipelineId,
            versionId: saveData.version_id || newVersionId,
          });
        }

        // Close drawer and redirect to the workflow page after a short delay
        setTimeout(() => {
          onClose();
          // Navigate to the workflow page and refresh
          navigate(`/workflows/${finalPipelineId}`);
          // FIX: Force a full page refresh to ensure all state is updated
          window.location.reload();
        }, 1000);
      } catch (error) {
        console.error("Error creating workflow:", error);
        setSnackbar({
          open: true,
          message: `Failed to create pipeline: ${error.message}`,
          severity: "error",
        });
      } finally {
        setIsCreating(false);
      }
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const handleInputChange = (field) => (event) => {
    const value = event.target.value;
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSelectChange = (field) => (event) => {
    const value = event.target.value;
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setFormData((prev) => ({
      ...prev,
      document: file,
    }));
  };

  // Handle members selection change
  const handleMembersChange = useCallback((newMembers) => {
    setFormData((prev) => ({
      ...prev,
      selectedMembers: newMembers,
    }));
  }, []);

  const getStepStatus = (stepId) => {
    if (stepId < currentStep) return "completed";
    if (stepId === currentStep) return "current";
    return "pending";
  };

  // Handle nodes change from Playground (controlled mode)
  const handleNodesChange = useCallback((newNodes) => {
    // Simply update nodes - positions are controlled by flowchart updates
    setNodes(newNodes);
  }, []);

  // Handle edges change from Playground (controlled mode)
  const handleEdgesChange = useCallback((newEdges) => {
    setEdges(newEdges);
  }, []);

  // Handle Playground init to get rfInstance
  const handlePlaygroundInit = useCallback((instance) => {
    setRfInstance(instance);
  }, []);

  // Handle agents change from AddAIAgent
  const handleAgentsChange = useCallback((newAgents) => {
    setAgents(newAgents);
  }, []);

  // Handle workflow generation from AI chatbot
  const handleWorkflowGenerated = useCallback(
    (generatedNodes, generatedEdges) => {
      if (generatedNodes && generatedEdges) {
        setNodes(generatedNodes);
        setEdges(generatedEdges);
      }
    },
    []
  );

  // Handle accept workflow from AI chatbot
  const handleAcceptWorkflow = useCallback(() => {
    // Automatically advance to next step when workflow is accepted
    if (currentStep === 2) {
      setCurrentStep(3);
    }
  }, [currentStep]);

  // Handle decline workflow from AI chatbot
  const handleDeclineWorkflow = useCallback(() => {
    // Reset nodes and edges if declined
    setNodes([]);
    setEdges([]);
  }, []);

  return (
    <>
      {/* Backdrop */}
      {open && (
        <Box
          onClick={onClose}
          sx={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            bgcolor: "rgba(0, 0, 0, 0.5)",
            zIndex: 11,
          }}
        />
      )}

      {/* Sliding Drawer */}
      <Slide direction="up" in={open} mountOnEnter unmountOnExit>
        <Box
          sx={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            height: "100vh",
            width: "100vw",
            zIndex: 9999,
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              display: "flex",
              minHeight: "100vh",
              bgcolor: "background.paper",
              height: "100%",
              width: "100%",
              overflow: "hidden",
            }}
          >
            {/* Left Sidebar */}
            <StepSidebar
              steps={steps}
              currentStep={currentStep}
              isSidebarCollapsed={isSidebarCollapsed}
              onToggleCollapse={() =>
                setIsSidebarCollapsed(!isSidebarCollapsed)
              }
              getStepStatus={getStepStatus}
              formData={formData}
              onWorkflowGenerated={handleWorkflowGenerated}
              isGenerating={isGenerating}
              setIsGenerating={setIsGenerating}
              currentStepValue={currentStep}
              onAcceptWorkflow={handleAcceptWorkflow}
              onDeclineWorkflow={handleDeclineWorkflow}
              chatMessages={chatMessages}
              onSendMessage={sendUserInput}
              awaitingInput={awaitingInput}
            />

            {/* Main Content - Full width, sidebar overlays for step 2+ */}
            <Box
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                bgcolor: "background.paper",
                minWidth: 0,
                overflow: "hidden",
                width: "100%",
                position: "relative",
                marginLeft:
                  currentStep > 1 && isSidebarCollapsed
                    ? `${STEP_SIDEBAR_COLLAPSED_WIDTH}px`
                    : 0,
                transition: "margin-left 0.3s ease",
              }}
            >
              {/* Header */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  px: 3,
                  py: 2,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 600,
                    color: "text.primary",
                  }}
                >
                  Create Workflow
                </Typography>
                <IconButton
                  onClick={onClose}
                  size="small"
                  sx={{
                    color: "text.secondary",
                    "&:hover": { bgcolor: "action.hover" },
                  }}
                >
                  <CloseIcon />
                </IconButton>
              </Box>

              {/* Step 1: Basic Information Form */}
              {currentStep === 1 && (
                <Box
                  sx={{
                    flex: 1,
                    p: 4,
                    display: "flex",
                    justifyContent: "center",
                    overflow: "auto",
                  }}
                >
                  <Box sx={{ width: "100%", maxWidth: 600 }}>
                    <Typography
                      variant="h5"
                      sx={{
                        fontWeight: 600,
                        color: "text.primary",
                        mb: 4,
                      }}
                    >
                      Basic Information
                    </Typography>

                    <BasicInformationForm
                      formData={formData}
                      onInputChange={handleInputChange}
                      onFileChange={handleFileChange}
                      onMembersChange={handleMembersChange}
                      allUsers={allUsers}
                      setAllUsers={setAllUsers}
                      loadingUsers={loadingUsers}
                      setLoadingUsers={setLoadingUsers}
                    />

                    {/* Navigation Buttons */}
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 1.5,
                        mt: 2,
                        mb: 4,
                      }}
                    >
                      <Button
                        variant="text"
                        onClick={handleBack}
                        disabled={currentStep === 1}
                        sx={{
                          py: 1,
                          px: 3,
                          color: "primary.main",
                          textTransform: "none",
                          fontWeight: 500,
                          borderRadius: 2,
                          "&:hover": {
                            bgcolor: "action.hover",
                          },
                          "&:disabled": {
                            color: "text.disabled",
                          },
                        }}
                      >
                        Back
                      </Button>
                      <Button
                        variant="contained"
                        onClick={handleNext}
                        disabled={isGenerating}
                        sx={{
                          py: 1,
                          px: 3,
                          bgcolor: "primary.main",
                          color: "common.white",
                          textTransform: "none",
                          fontWeight: 500,
                          borderRadius: 2,
                          boxShadow: "none",
                          "&:hover": {
                            bgcolor: "primary.dark",
                            boxShadow: "none",
                          },
                          "&:disabled": {
                            bgcolor: "action.disabledBackground",
                            color: "action.disabled",
                          },
                        }}
                      >
                        {isGenerating ? (
                          <>
                            <CircularProgress
                              size={16}
                              sx={{ mr: 1, color: "inherit" }}
                            />
                            Generating...
                          </>
                        ) : (
                          "Next"
                        )}
                      </Button>
                    </Box>
                  </Box>
                </Box>
              )}

              {/* Step 2: AI Assistant - Show canvas with chatbot in sidebar */}
              {currentStep === 2 && (
                <Box
                  sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  {/* Playground Canvas */}
                  <Box
                    sx={{
                      flex: 1,
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <Playground
                      nodes={nodes}
                      edges={edges}
                      onNodesChange={handleNodesChange}
                      onEdgesChange={handleEdgesChange}
                      onInit={(instance) => {
                        rfInstanceRef.current = instance;
                        handlePlaygroundInit(instance);
                      }}
                      readOnly={false}
                      drawerZIndex={10001}
                    />

                    {/* Node Approval Popup - positioned over the canvas */}
                    {proposedNode &&
                      proposedNodePosition &&
                      rfInstanceRef.current && (
                        <Box
                          sx={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            pointerEvents: "none",
                            zIndex: 10000,
                          }}
                        >
                          <NodeApprovalPopup
                            nodeId={proposedNode.id}
                            isRendering={isRenderingNode}
                            position={(() => {
                              try {
                                // Convert ReactFlow coordinates to screen coordinates relative to the canvas
                                const rfInstance = rfInstanceRef.current;
                                const viewport = rfInstance.getViewport();
                                const zoom = rfInstance.getZoom();

                                // Get ReactFlow container
                                const reactFlowContainer =
                                  document.querySelector(".react-flow");
                                const containerRect =
                                  reactFlowContainer?.getBoundingClientRect();

                                if (!containerRect) {
                                  throw new Error(
                                    "ReactFlow container not found"
                                  );
                                }

                                // Get the node's screen position relative to the ReactFlow container
                                const nodeWidth =
                                  proposedNode.measured?.width || 200;
                                const nodeHeight =
                                  proposedNode.measured?.height || 100;

                                // Calculate node center in flow coordinates
                                const nodeCenterX =
                                  proposedNodePosition.x + nodeWidth / 2;
                                const nodeCenterY =
                                  proposedNodePosition.y + nodeHeight / 2;

                                // Convert to screen coordinates relative to ReactFlow container
                                const screenX = nodeCenterX * zoom + viewport.x;
                                const screenY = nodeCenterY * zoom + viewport.y;

                                // Position dialog ABOVE the node (not over it)
                                // Calculate popup height (approximately 120px)
                                const popupHeight = 120;
                                const popupWidth = 280;
                                
                                // Center horizontally above the node
                                const dialogX = screenX - popupWidth / 2;
                                // Position above the node with some spacing
                                const dialogY = screenY - (nodeHeight * zoom) / 2 - popupHeight - 10;

                                // Ensure dialog is within container bounds
                                const containerWidth = containerRect.width;
                                const containerHeight = containerRect.height;

                                let finalX = dialogX;
                                let finalY = dialogY;

                                // If dialog would go outside left edge, shift it right
                                if (finalX < 10) {
                                  finalX = 10;
                                }
                                // If dialog would go outside right edge, shift it left
                                if (finalX + popupWidth > containerWidth - 10) {
                                  finalX = containerWidth - popupWidth - 10;
                                }
                                
                                // If dialog would go above container, position it below the node instead
                                if (finalY < 10) {
                                  finalY = screenY + (nodeHeight * zoom) / 2 + 10;
                                }
                                
                                // If dialog would go below container, position it above (even if partially off-screen)
                                if (finalY + popupHeight > containerHeight - 10) {
                                  finalY = screenY - (nodeHeight * zoom) / 2 - popupHeight - 10;
                                }

                                return { x: finalX, y: finalY };
                              } catch (error) {
                                console.error(
                                  "Error calculating popup position:",
                                  error
                                );
                                // Fallback: center of container
                                return {
                                  x: window.innerWidth * 0.6,
                                  y: window.innerHeight * 0.5,
                                };
                              }
                            })()}
                            onApprove={() => handleNodeApproval("approve")}
                            onReject={handleNodeRejection}
                          />
                        </Box>
                      )}
                  </Box>

                  {/* Navigation Buttons for AI Assistant Step */}
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 1.5,
                      p: 2,
                      borderTop: "1px solid",
                      borderColor: "divider",
                      bgcolor: "background.paper",
                    }}
                  >
                    <Button
                      variant="text"
                      onClick={handleBack}
                      sx={{
                        py: 1,
                        px: 3,
                        color: "primary.main",
                        textTransform: "none",
                        fontWeight: 500,
                        borderRadius: 2,
                        "&:hover": {
                          bgcolor: "action.hover",
                        },
                        "&:disabled": {
                          color: "text.disabled",
                        },
                      }}
                    >
                      Back
                    </Button>
                    <Button
                      variant="contained"
                      onClick={handleNext}
                      disabled={nodes.length === 0}
                      sx={{
                        py: 1,
                        px: 3,
                        bgcolor: "primary.main",
                        color: "common.white",
                        textTransform: "none",
                        fontWeight: 500,
                        borderRadius: 2,
                        boxShadow: "none",
                        "&:hover": {
                          bgcolor: "primary.dark",
                          boxShadow: "none",
                        },
                        "&:disabled": {
                          bgcolor: "action.disabledBackground",
                          color: "action.disabled",
                        },
                      }}
                    >
                      Next
                    </Button>
                  </Box>
                </Box>
              )}

              {/* Step 3: Nodes Setup - Add AI Agent Form */}
              {currentStep === 3 && (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    flex: 1,
                    overflow: "auto",
                    px: 3,
                    py: 4,
                    position: "relative",
                    zIndex: 1,
                    pointerEvents: "auto",
                    alignItems: "center",
                  }}
                >
                  <Box sx={{ width: "100%", maxWidth: 600 }}>
                    <Typography
                      variant="h5"
                      sx={{
                        fontWeight: 700,
                        color: "text.primary",
                        mb: 3,
                      }}
                    >
                      Add AI Agents
                    </Typography>

                    <AddAIAgent
                      formData={formData}
                      onInputChange={handleInputChange}
                      onSelectChange={handleSelectChange}
                      onAgentsChange={handleAgentsChange}
                      nodes={nodes}
                    />
                  </Box>

                  {/* Navigation Buttons */}
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 1.5,
                      p: 2,
                      bgcolor: "background.paper",
                      width: "100%",
                      maxWidth: 600,
                    }}
                  >
                    <Button
                      variant="text"
                      onClick={handleBack}
                      sx={{
                        py: 1,
                        px: 3,
                        color: "primary.main",
                        textTransform: "none",
                        fontWeight: 500,
                        borderRadius: 2,
                        "&:hover": {
                          bgcolor: "action.hover",
                        },
                        "&:disabled": {
                          color: "text.disabled",
                        },
                      }}
                    >
                      Back
                    </Button>
                    <Button
                      variant="contained"
                      onClick={handleNext}
                      disabled={isCreating}
                      sx={{
                        py: 1,
                        px: 3,
                        bgcolor: "primary.main",
                        color: "common.white",
                        textTransform: "none",
                        fontWeight: 500,
                        borderRadius: 2,
                        boxShadow: "none",
                        "&:hover": {
                          bgcolor: "primary.dark",
                          boxShadow: "none",
                        },
                        "&:disabled": {
                          bgcolor: "action.disabledBackground",
                          color: "action.disabled",
                        },
                      }}
                    >
                      {isCreating ? (
                        <>
                          <CircularProgress
                            size={16}
                            sx={{ mr: 1, color: "inherit" }}
                          />
                          Creating...
                        </>
                      ) : (
                        "Create"
                      )}
                    </Button>
                  </Box>
                </Box>
              )}
            </Box>
          </Box>
        </Box>
      </Slide>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        sx={{ zIndex: 10000 }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default CreateWorkflowDrawer;
