import { useState, useCallback, useEffect, useRef } from "react";
import { applyNodeChanges, applyEdgeChanges } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Box, IconButton } from "@mui/material";
import FullscreenExitIcon from "@mui/icons-material/FullscreenExit";

import { PropertyBar } from "./PropertyBar";
import {
  LockMessageHelper,
  ToolbarButtonHelper,
  DeleteEdgeHelper,
} from "./ToolbarHelpers";
import { NodeDrawer } from "./NodeDrawer";
import { nodeTypes, generateNode, fetchNodeSchema } from "../../utils/dashboard.utils";
import BottomToolbar from "./BottomToolbar";
import WorkflowCanvas from "./WorkflowCanvas";
import ZoomControl from "./ZoomControl";
import useUndoRedo, {
  ActionTypes,
  createAddNodeAction,
  createRemoveNodeAction,
  createAddEdgeAction,
  createRemoveEdgeAction,
  createMoveNodeAction,
  createUpdatePropertiesAction,
} from "../../hooks/useUndoRedo";
/**
 * Playground Component
 *
 * A reusable React Flow-based node editor with undo/redo, drag-and-drop,
 * node property editing, and fullscreen support.
 *
 * Supports two modes:
 * 1. Controlled mode: Pass nodes/edges as props with onChange callbacks
 * 2. Uncontrolled mode: Manages internal state, use initialNodes/initialEdges
 *
 * @param {Object} props
 * @param {Array} props.nodes - Controlled: current nodes array
 * @param {Array} props.edges - Controlled: current edges array
 * @param {Function} props.onNodesChange - Controlled: callback when nodes change
 * @param {Function} props.onEdgesChange - Controlled: callback when edges change
 * @param {Array} props.initialNodes - Uncontrolled: initial nodes (default: [])
 * @param {Array} props.initialEdges - Uncontrolled: initial edges (default: [])
 * @param {Function} props.onInit - Callback with React Flow instance
 * @param {Function} props.onNodeSelect - Callback when a node is selected
 * @param {Function} props.onEdgeSelect - Callback when an edge is selected
 * @param {boolean} props.readOnly - Disable all editing (default: false)
 * @param {boolean} props.showToolbar - Show bottom toolbar (default: true)
 * @param {boolean} props.showFullscreenButton - Show fullscreen toggle (default: true)
 * @param {number} props.drawerWidth - Left offset for layout (default: 0)
 * @param {string} props.height - Height of the playground (default: "100%")
 */
export default function Playground({
  // Controlled mode props
  nodes: controlledNodes,
  edges: controlledEdges,
  onNodesChange: onNodesChangeProp,
  onEdgesChange: onEdgesChangeProp,

  // Uncontrolled mode props
  initialNodes = [],
  initialEdges = [],

  // React Flow instance
  onInit,

  // Selection callbacks
  onNodeSelect,
  onEdgeSelect,

  // Mode controls
  readOnly = false,
  showToolbar = true,
  showFullscreenButton = true,

  // Layout
  drawerWidth = 0,
  height = "100%",

  // Z-index for nested drawers (e.g., inside CreateWorkflowDrawer)
  drawerZIndex,
}) {
  // Determine if we're in controlled mode
  const isControlled =
    controlledNodes !== undefined && controlledEdges !== undefined;

  // Internal state for uncontrolled mode
  const [internalNodes, setInternalNodes] = useState(initialNodes);
  const [internalEdges, setInternalEdges] = useState(initialEdges);

  // Use controlled or internal state
  const currentNodes = isControlled ? controlledNodes : internalNodes;
  const currentEdges = isControlled ? controlledEdges : internalEdges;

  // State setters that work for both modes
  const setCurrentNodes = useCallback(
    (nodesOrUpdater) => {
      if (isControlled && onNodesChangeProp) {
        // For controlled mode, we need to compute the new value and pass it up
        const newNodes =
          typeof nodesOrUpdater === "function"
            ? nodesOrUpdater(controlledNodes)
            : nodesOrUpdater;
        onNodesChangeProp(newNodes);
      } else {
        setInternalNodes(nodesOrUpdater);
      }
    },
    [isControlled, onNodesChangeProp, controlledNodes]
  );

  const setCurrentEdges = useCallback(
    (edgesOrUpdater) => {
      if (isControlled && onEdgesChangeProp) {
        const newEdges =
          typeof edgesOrUpdater === "function"
            ? edgesOrUpdater(controlledEdges)
            : edgesOrUpdater;
        onEdgesChangeProp(newEdges);
      } else {
        setInternalEdges(edgesOrUpdater);
      }
    },
    [isControlled, onEdgesChangeProp, controlledEdges]
  );

  // React Flow instance
  const [rfInstance, setRfInstance] = useState(null);

  // UI State
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLocked, setIsLocked] = useState(readOnly);
  const [hoveredToolbarButton, setHoveredToolbarButton] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Undo/Redo System (using custom hook)
  const {
    undoStack,
    redoStack,
    canUndo,
    canRedo,
    addAction,
    popUndo,
    popRedo,
    isExecuting,
    setExecuting,
  } = useUndoRedo({ maxLimit: 10 });

  // Track node positions for move detection
  const nodePositionsRef = useRef({});

  // Sync readOnly prop with isLocked state
  useEffect(() => {
    setIsLocked(readOnly);
  }, [readOnly]);

  // Initialize node positions tracking
  useEffect(() => {
    const positions = {};
    currentNodes.forEach((node) => {
      positions[node.id] = { x: node.position.x, y: node.position.y };
    });
    nodePositionsRef.current = positions;
  }, [currentNodes.length]);

  // Handle React Flow initialization
  const handleInit = useCallback(
    (instance) => {
      setRfInstance(instance);
      if (onInit) {
        onInit(instance);
      }
    },
    [onInit]
  );

  // Execute an action (for redo)
  const executeAction = useCallback(
    (action) => {
      setExecuting(true);

      switch (action.type) {
        case ActionTypes.ADD_NODE:
          setCurrentNodes((prev) => [...prev, action.node]);
          break;

        case ActionTypes.REMOVE_NODE:
          setCurrentNodes((prev) => prev.filter((n) => n.id !== action.nodeId));
          setCurrentEdges((prev) =>
            prev.filter(
              (e) => e.source !== action.nodeId && e.target !== action.nodeId
            )
          );
          break;

        case ActionTypes.ADD_EDGE:
          setCurrentEdges((prev) => [...prev, action.edge]);
          break;

        case ActionTypes.REMOVE_EDGE:
          setCurrentEdges((prev) => prev.filter((e) => e.id !== action.edgeId));
          break;

        case ActionTypes.MOVE_NODE:
          setCurrentNodes((prev) =>
            prev.map((n) =>
              n.id === action.nodeId
                ? { ...n, position: action.newPosition }
                : n
            )
          );
          nodePositionsRef.current[action.nodeId] = action.newPosition;
          break;

        case ActionTypes.UPDATE_PROPERTIES:
          setCurrentNodes((prev) =>
            prev.map((n) =>
              n.id === action.nodeId
                ? {
                    ...n,
                    data: { ...n.data, properties: action.newProperties },
                  }
                : n
            )
          );
          break;

        default:
          console.warn("Unknown action type:", action.type);
      }

      setTimeout(() => {
        setExecuting(false);
      }, 50);
    },
    [setCurrentNodes, setCurrentEdges, setExecuting]
  );

  // Reverse an action (for undo)
  const reverseAction = useCallback(
    (action) => {
      setExecuting(true);

      switch (action.type) {
        case ActionTypes.ADD_NODE:
          setCurrentNodes((prev) =>
            prev.filter((n) => n.id !== action.node.id)
          );
          setCurrentEdges((prev) =>
            prev.filter(
              (e) => e.source !== action.node.id && e.target !== action.node.id
            )
          );
          break;

        case ActionTypes.REMOVE_NODE:
          setCurrentNodes((prev) => [...prev, action.node]);
          if (action.connectedEdges && action.connectedEdges.length > 0) {
            setCurrentEdges((prev) => [...prev, ...action.connectedEdges]);
          }
          break;

        case ActionTypes.ADD_EDGE:
          setCurrentEdges((prev) =>
            prev.filter((e) => e.id !== action.edge.id)
          );
          break;

        case ActionTypes.REMOVE_EDGE:
          setCurrentEdges((prev) => [...prev, action.edge]);
          break;

        case ActionTypes.MOVE_NODE:
          setCurrentNodes((prev) =>
            prev.map((n) =>
              n.id === action.nodeId
                ? { ...n, position: action.oldPosition }
                : n
            )
          );
          nodePositionsRef.current[action.nodeId] = action.oldPosition;
          break;

        case ActionTypes.UPDATE_PROPERTIES:
          setCurrentNodes((prev) =>
            prev.map((n) =>
              n.id === action.nodeId
                ? {
                    ...n,
                    data: { ...n.data, properties: action.oldProperties },
                  }
                : n
            )
          );
          break;

        default:
          console.warn("Unknown action type:", action.type);
      }

      setTimeout(() => {
        setExecuting(false);
      }, 50);
    },
    [setCurrentNodes, setCurrentEdges, setExecuting]
  );

  // Handle node changes from React Flow
  const onNodesChange = useCallback(
    (changes) => {
      if (!isExecuting()) {
        changes.forEach((change) => {
          if (change.type === "position" && change.dragging === false) {
            const oldPosition = nodePositionsRef.current[change.id];
            const newPosition = change.position;

            if (
              oldPosition &&
              (oldPosition.x !== newPosition.x ||
                oldPosition.y !== newPosition.y)
            ) {
              addAction(
                createMoveNodeAction(change.id, oldPosition, newPosition)
              );
              nodePositionsRef.current[change.id] = { ...newPosition };
            }
          } else if (change.type === "remove") {
            const nodeToRemove = currentNodes.find((n) => n.id === change.id);
            const connectedEdges = currentEdges.filter(
              (e) => e.source === change.id || e.target === change.id
            );

            if (nodeToRemove) {
              addAction(
                createRemoveNodeAction(change.id, nodeToRemove, connectedEdges)
              );
            }
          }
        });
      }

      setCurrentNodes((ns) => applyNodeChanges(changes, ns));
    },
    [setCurrentNodes, addAction, currentNodes, currentEdges, isExecuting]
  );

  // Handle edge changes from React Flow
  const onEdgesChange = useCallback(
    (changes) => {
      if (!isExecuting()) {
        changes.forEach((change) => {
          if (change.type === "remove") {
            const edgeToRemove = currentEdges.find((e) => e.id === change.id);

            if (edgeToRemove) {
              addAction(createRemoveEdgeAction(change.id, edgeToRemove));
            }

            if (selectedEdge && change.id === selectedEdge.id) {
              setSelectedEdge(null);
            }
          }
        });
      }

      setCurrentEdges((es) => applyEdgeChanges(changes, es));
    },
    [setCurrentEdges, addAction, currentEdges, selectedEdge, isExecuting]
  );

  // Handle new connections
  const onConnect = useCallback(
    (params) => {
      const newEdge = {
        ...params,
        id: `${params.source}-${params.target}-${Date.now()}`,
        animated: true,
      };

      if (!isExecuting()) {
        addAction(createAddEdgeAction(newEdge));
      }

      setCurrentEdges((es) => [...es, newEdge]);
    },
    [setCurrentEdges, addAction, isExecuting]
  );

  // Add node from schema
  const handleAddNode = useCallback(
    (schema) => {
      const newNode = generateNode(schema, currentNodes);

      if (!isExecuting()) {
        addAction(createAddNodeAction(newNode));
        nodePositionsRef.current[newNode.id] = { ...newNode.position };
      }

      setCurrentNodes((prev) => [...prev, newNode]);
    },
    [currentNodes, addAction, setCurrentNodes, isExecuting]
  );

  // Undo handler
  const handleUndo = useCallback(() => {
    const action = popUndo();
    if (action) {
      reverseAction(action);
    }
  }, [popUndo, reverseAction]);

  // Redo handler
  const handleRedo = useCallback(() => {
    const action = popRedo();
    if (action) {
      executeAction(action);
    }
  }, [popRedo, executeAction]);

  // Node click handler
  const onNodeClick = useCallback(
    (event, node) => {
      setSelectedNode(node);
      setSelectedEdge(null);
      if (onNodeSelect) {
        onNodeSelect(node);
      }
    },
    [onNodeSelect]
  );

  // Edge click handler
  const onEdgeClick = useCallback(
    (event, edge) => {
      setSelectedEdge(edge);
      setSelectedNode(null);
      if (onEdgeSelect) {
        onEdgeSelect(edge);
      }
    },
    [onEdgeSelect]
  );

  // Fullscreen handlers
  const handleEnterFullscreen = useCallback(() => {
    setIsFullscreen(true);
    setSelectedNode(null);
  }, []);

  const handleExitFullscreen = useCallback(() => {
    setIsFullscreen(false);
  }, []);

  // Lock toggle handler
  const handleLockToggle = useCallback(() => {
    if (!readOnly) {
      setIsLocked((prev) => !prev);
    }
  }, [readOnly]);

  const handleFitScreen = useCallback(() => {
    if (!rfInstance) {
      console.warn('ReactFlow instance not available');
      return;
    }

    try {
      // ReactFlow v12+ uses fitView method directly on the instance
      if (typeof rfInstance.fitView === 'function') {
        rfInstance.fitView({ 
          padding: 0.1, 
          maxZoom: 0.9,
          duration: 300,
          includeHiddenNodes: false
        });
      } else if (rfInstance.getNodes && rfInstance.getViewport && rfInstance.setViewport) {
        // Fallback implementation using getNodes
        const nodes = rfInstance.getNodes();
        if (!nodes || nodes.length === 0) {
          console.warn('No nodes to fit');
          return;
        }
        
        // Calculate bounding box
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        
        nodes.forEach(node => {
          const nodeWidth = node.measured?.width || node.width || 200;
          const nodeHeight = node.measured?.height || node.height || 100;
          
          minX = Math.min(minX, node.position.x);
          maxX = Math.max(maxX, node.position.x + nodeWidth);
          minY = Math.min(minY, node.position.y);
          maxY = Math.max(maxY, node.position.y + nodeHeight);
        });
        
        const width = maxX - minX;
        const height = maxY - minY;
        
        if (width > 0 && height > 0) {
          // Get container dimensions from viewport or use defaults
          const viewport = rfInstance.getViewport();
          const containerWidth = viewport.width || window.innerWidth;
          const containerHeight = viewport.height || window.innerHeight;
          
          // Calculate scale to fit with padding
          const padding = 40;
          const scale = Math.min(
            (containerWidth - padding * 2) / width,
            (containerHeight - padding * 2) / height,
            0.9
          );
          
          // Calculate center position
          const x = (containerWidth - width * scale) / 2 - minX * scale;
          const y = (containerHeight - height * scale) / 2 - minY * scale;
          
          rfInstance.setViewport({ x, y, zoom: scale }, { duration: 300 });
        }
      } else {
        console.error('ReactFlow instance does not have required methods');
      }
    } catch (error) {
      console.error('Error fitting view:', error);
    }
  }, [rfInstance]);

  const handleZoomIn = useCallback(() => {
    if (rfInstance) {
      const currentZoom = rfInstance.getZoom();
      const roundedZoom = Math.round((currentZoom * 100) / 10) * 10;
      const newZoom = Math.min((roundedZoom + 10) / 100, 2); // Max 200%, increment by 10%
      rfInstance.zoomTo(newZoom);
      setZoomLevel(newZoom * 100);
    }
  }, [rfInstance]);

  const handleZoomOut = useCallback(() => {
    if (rfInstance) {
      const currentZoom = rfInstance.getZoom();
      const roundedZoom = Math.round((currentZoom * 100) / 10) * 10;
      const newZoom = Math.max((roundedZoom - 10) / 100, 0.1); // Min 10%, decrement by 10%
      rfInstance.zoomTo(newZoom);
      setZoomLevel(newZoom * 100);
    }
  }, [rfInstance]);

  const handleZoomChange = useCallback((zoomPercent) => {
    if (rfInstance) {
      const newZoom = zoomPercent / 100;
      rfInstance.zoomTo(newZoom);
      setZoomLevel(zoomPercent);
    }
  }, [rfInstance]);

  // Update zoom level when viewport changes
  useEffect(() => {
    if (rfInstance) {
      const updateZoom = () => {
        const zoom = rfInstance.getZoom();
        setZoomLevel(zoom * 100);
      };
      
      // Update zoom on viewport change
      const unsubscribe = rfInstance.onViewportChange?.(updateZoom);
      
      return () => {
        if (unsubscribe) unsubscribe();
      };
    }
  }, [rfInstance]);

  // Keyboard shortcuts for undo/redo/add
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Press A to toggle add node drawer
      if (
        (e.key === "a" || e.key === "A") &&
        !isLocked &&
        !isFullscreen &&
        !e.ctrlKey &&
        !e.metaKey
      ) {
        const activeElement = document.activeElement;
        if (
          activeElement &&
          (activeElement.tagName === "INPUT" ||
            activeElement.tagName === "TEXTAREA" ||
            activeElement.isContentEditable)
        ) {
          return;
        }
        if (selectedNode) {
          return;
        }
        e.preventDefault();
        setDrawerOpen((prev) => !prev);
      }

      // Ctrl+Z or Cmd+Z for undo
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      }

      // Ctrl+Y or Cmd+Y or Ctrl+Shift+Z for redo
      if (
        (e.ctrlKey || e.metaKey) &&
        (e.key === "y" || (e.shiftKey && e.key === "z"))
      ) {
        e.preventDefault();
        handleRedo();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleUndo, handleRedo, isLocked, isFullscreen, selectedNode]);

  // Backspace to delete selected edge
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Backspace" && selectedEdge && !isFullscreen && !isLocked) {
        e.preventDefault();

        const edgeToRemove = currentEdges.find(
          (edge) => edge.id === selectedEdge.id
        );

        if (edgeToRemove && !isExecuting()) {
          addAction(createRemoveEdgeAction(selectedEdge.id, edgeToRemove));
        }

        setCurrentEdges((edges) =>
          edges.filter((edge) => edge.id !== selectedEdge.id)
        );
        setSelectedEdge(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    selectedEdge,
    isFullscreen,
    isLocked,
    setCurrentEdges,
    addAction,
    currentEdges,
    isExecuting,
  ]);

  // ESC to exit fullscreen
  useEffect(() => {
    if (!isFullscreen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        handleExitFullscreen();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen, handleExitFullscreen]);

  // Update properties handler
  const handleUpdateProperties = useCallback(
    (nodeId, data) => {
      if (!isExecuting()) {
        const node = currentNodes.find((n) => n.id === nodeId);
        if (node) {
          addAction(
            createUpdatePropertiesAction(
              nodeId,
              node.data?.properties || {},
              data
            )
          );
        }
      }

      setCurrentNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, properties: data } } : n
        )
      );
      setSelectedNode(null);
    },
    [currentNodes, addAction, setCurrentNodes, isExecuting]
  );

  // Drag over handler
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  // Drop handler
  const onDrop = useCallback(
    async (event) => {
      event.preventDefault();

      const nodeName = event.dataTransfer.getData("application/reactflow");

      if (!nodeName || !rfInstance) {
        return;
      }

      try {
        const position = rfInstance.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });

        const schema = await fetchNodeSchema(nodeName);
        const newNode = generateNode(schema, currentNodes);
        newNode.position = position;

        if (!isExecuting()) {
          addAction(createAddNodeAction(newNode));
          nodePositionsRef.current[newNode.id] = { ...newNode.position };
        }

        setCurrentNodes((prev) => [...prev, newNode]);
      } catch (err) {
        console.error("Failed to add node:", err);
      }
    },
    [rfInstance, currentNodes, setCurrentNodes, addAction, isExecuting]
  );

  // Pane click handler - deselect
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  // Create styled edges with selection highlighting
  const styledEdges = currentEdges.map((edge) => ({
    ...edge,
    selected: selectedEdge?.id === edge.id,
    style:
      selectedEdge?.id === edge.id
        ? {
            stroke: "#2196F3",
            strokeWidth: 2.5,
            filter: "drop-shadow(0 0 2px rgba(33, 150, 243, 0.4))",
          }
        : {
            ...edge.style,
            stroke: edge.style?.stroke || "#b1b1b7",
            strokeWidth: edge.style?.strokeWidth || 2,
          },
    animated: selectedEdge?.id === edge.id ? true : edge.animated,
  }));

  // Fullscreen view
  if (isFullscreen) {
    return (
      <Box
        sx={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          width: "100vw",
          height: "100vh",
          bgcolor: "#ffffff",
          zIndex: 9999,
        }}
      >
        <WorkflowCanvas
          nodes={currentNodes}
          edges={styledEdges}
          nodeTypes={nodeTypes}
          onNodesChange={() => {}}
          onEdgesChange={() => {}}
          onConnect={() => {}}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          onInit={handleInit}
          onPaneClick={onPaneClick}
          onFullscreenClick={handleExitFullscreen}
        />

        {/* Exit Fullscreen Button */}
        <Box
          sx={{
            position: "fixed",
            bottom: 12,
            right: 12,
            display: "flex",
            gap: 0.5,
            bgcolor: "#C3D3DB",
            borderRadius: "8px",
            padding: "4px 8px",
            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.08)",
            zIndex: 10000,
          }}
        >
          <IconButton
            onClick={handleExitFullscreen}
            sx={{
              bgcolor: "#F7FAFC",
              color: "#1f2937",
              "&:hover": { bgcolor: "#e5e7eb" },
              width: 30,
              height: 30,
              borderRadius: "6px",
            }}
          >
            <FullscreenExitIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>
      </Box>
    );
  }

  // Normal view
  return (
    <Box
      sx={{
        height: height,
        width: "100%",
        bgcolor: "background.paper",
        position: "relative",
        padding: 0,
        display: "flex",
        alignItems: "stretch",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      <WorkflowCanvas
        nodes={currentNodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        onNodesChange={isLocked ? () => {} : onNodesChange}
        onEdgesChange={isLocked ? () => {} : onEdgesChange}
        onConnect={isLocked ? undefined : onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onInit={handleInit}
        onDrop={isLocked ? undefined : onDrop}
        onDragOver={isLocked ? undefined : onDragOver}
        onPaneClick={onPaneClick}
        onCanvasClick={(e) => {
          if (
            e.target.classList.contains("react-flow__pane") ||
            e.target.classList.contains("react-flow__renderer")
          ) {
            setSelectedNode(null);
            setSelectedEdge(null);
          }
        }}
        onFullscreenClick={
          showFullscreenButton ? handleEnterFullscreen : undefined
        }
        isLocked={isLocked}
        onLockToggle={readOnly ? undefined : handleLockToggle}
      />

      {/* Lock Message Helper */}
      {isLocked && !hoveredToolbarButton && <LockMessageHelper />}

      {/* Toolbar Button Helper */}
      {hoveredToolbarButton && (
        <ToolbarButtonHelper hoveredButton={hoveredToolbarButton} />
      )}

      {/* Delete Edge Helper */}
      {selectedEdge && !isLocked && !hoveredToolbarButton && (
        <DeleteEdgeHelper />
      )}

      {/* Bottom Toolbar */}
      {showToolbar && (
        <BottomToolbar
          onAddClick={() => !isLocked && setDrawerOpen(true)}
          onUndoClick={handleUndo}
          onRedoClick={handleRedo}
          onHoverChange={setHoveredToolbarButton}
          addDisabled={isLocked}
          undoDisabled={isLocked || !canUndo}
          redoDisabled={isLocked || !canRedo}
          isLocked={isLocked}
          onLockToggle={readOnly ? undefined : handleLockToggle}
        />
      )}

      {/* Zoom Control */}
      {showToolbar && (
        <ZoomControl
          zoom={zoomLevel}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onZoomChange={handleZoomChange}
          onFitScreen={handleFitScreen}
          propertyBarOpen={Boolean(selectedNode)}
        />
      )}

      {/* Node Drawer */}
      <NodeDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onAddNode={handleAddNode}
        setNodes={setCurrentNodes}
        currentNodes={currentNodes}
        undoDeque={undoStack}
        zIndex={drawerZIndex}
      />

      {/* Property Bar */}
      <PropertyBar
        open={Boolean(selectedNode)}
        selectedNode={selectedNode}
        onClose={() => setSelectedNode(null)}
        onUpdateProperties={handleUpdateProperties}
        readOnly={isLocked}
      />
    </Box>
  );
}

// Export for use in other components
export { Playground };
