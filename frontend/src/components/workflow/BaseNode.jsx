import React, { memo, useState, useCallback, useRef, useEffect } from "react";
import { Handle, Position, useReactFlow } from "@xyflow/react";
import {
  Paper,
  Typography,
  Stack,
  IconButton,
  Tooltip,
  Box,
  useTheme,
} from "@mui/material";
import {
  Delete,
  FileCopy,
  Edit,
  Input as InputIcon,
  Transform as TransformIcon,
  ControlCamera as ControlCameraIcon,
} from "@mui/icons-material";
import NodeDataTable from "./NodeDataTable";
import "../../css/BaseNode.css";
import { useGlobalContext } from "../../context/GlobalContext";
import { useGlobalWorkflow } from "../../context/GlobalWorkflowContext";

// Helper function to get icon based on node category
const getCategoryIcon = (category, label) => {
  const iconProps = { sx: { fontSize: 16, color: "rgba(0, 0, 0, 0.9)" } };
  const categoryLower = (category || "").toLowerCase();
  const labelLower = (label || "").toLowerCase();

  // IO nodes (input/output)
  if (
    categoryLower.includes("io") ||
    categoryLower.includes("input") ||
    categoryLower.includes("output")
  ) {
    return <InputIcon {...iconProps} />;
  }

  // Agent nodes
  if (
    categoryLower.includes("agent") ||
    categoryLower.includes("action") ||
    categoryLower.includes("logic")
  ) {
    return <ControlCameraIcon {...iconProps} />;
  }

  // Table/Transform nodes
  if (
    categoryLower.includes("table") ||
    categoryLower.includes("temporal") ||
    categoryLower.includes("transform")
  ) {
    return <TransformIcon {...iconProps} />;
  }

  // Fallback to TransformIcon for unknown types
  return <TransformIcon {...iconProps} />;
};

export const BaseNode = memo(
  ({
    id,
    data,
    selected,
    inputs = [],
    outputs = [],
    properties = [],
    styles = {},
    contextMenu = [],
    category,
    nodeType,
    onEditClick,
  }) => {
    const theme = useTheme();
    const { setNodes, getNode, getNodes, getEdges } = useReactFlow();
    const { status } = useGlobalWorkflow();
    
    // Check if this is an output node (write nodes that don't persist to postgres)
    // Output nodes have outdegree=0 AND have node_id ending with '_write'
    const isOutputNode = useCallback(() => {
      const edges = getEdges();
      // Count outgoing edges from this node
      const outgoingEdges = edges.filter(edge => edge.source === id);
      
      // If node has outgoing edges, it's definitely not an output node
      if (outgoingEdges.length > 0) {
        return false;
      }
      
      // Node has no outgoing edges - check if it's a write node
      // Output nodes have node_id ending with '_write' (e.g., kafka_write, csv_write)
      const isWriteNode = nodeType && nodeType.endsWith('_write');
      
      // Also check if it's explicitly an IO output node (category='io' and has n_inputs property)
      const hasInputsOnly = data?.properties?.n_inputs === 1;
      
      // It's an output node if it's a write node OR if it's an IO node with only inputs
      return isWriteNode || (category === 'io' && hasInputsOnly);
    }, [id, nodeType, category, data?.properties?.n_inputs, getEdges]);
    
    // Compute table name for NodeDataTable: {node_id}__{index}
    const getTableName = useCallback(() => {
      if (!nodeType) return id; // fallback
      const nodes = getNodes();
      const nodeIndex = nodes.findIndex(n => n.id === id);
      if (nodeIndex >= 0) {
        return `${nodeType}__${nodeIndex}`;
      }
      return id;
    }, [nodeType, id, getNodes]);

    // Convert properties to array and get top 3
    const getDisplayProperties = () => {
      // If properties is already an array, use it
      if (Array.isArray(properties)) {
        return properties.slice(0, 3);
      }

      // If properties is an object (from data.properties), convert to array
      if (properties && typeof properties === "object") {
        const propsArray = Object.entries(properties)
          .filter(
            ([key, value]) =>
              key !== "node_id" &&
              key !== "category" &&
              key !== "n_inputs" &&
              value !== null &&
              value !== undefined
          )
          .map(([key, value]) => ({
            label: key,
            value:
              typeof value === "object" ? JSON.stringify(value) : String(value),
            type: typeof value === "object" ? "json" : "string",
          }));
        return propsArray.slice(0, 3);
      }

      return [];
    };

    const displayProps = getDisplayProperties();

    // Default actions
    const handleCopy = useCallback(() => {
      const node = getNode(id);
      if (node) {
        const newNode = {
          ...node,
          id: `${id}_copy_${Date.now()}`,
          position: { x: node.position.x + 25, y: node.position.y + 25 },
        };
        setNodes((nds) => [...nds, newNode]);
      }
    }, [id, getNode, setNodes]);

    const handleCut = useCallback(() => {
      handleCopy();
      setNodes((nds) => nds.filter((n) => n.id !== id));
    }, [handleCopy, id, setNodes]);

    const handleDelete = useCallback(() => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
    }, [id, setNodes]);

    const handleDuplicate = useCallback(() => {
      const node = getNode(id);
      if (node) {
        const newNodeId = `${id}_dup_${Date.now()}`;
        const newNode = {
          ...node,
          id: newNodeId,
          position: { x: node.position.x + 40, y: node.position.y + 40 },
          selected: true, // Select the new node
        };
        setNodes((nds) => [
          ...nds.map((n) => ({ ...n, selected: false })), // Deselect all existing nodes
          newNode, // Add new node with selected: true
        ]);
      }
    }, [id, getNode, setNodes]);

    const handleEdit = useCallback(() => {
      // Call parent's onEditClick handler to toggle property bar
      if (onEditClick) {
        onEditClick(id);
      }
    }, [id, onEditClick]);

    // Hover state for floating actions
    const [isHovered, setIsHovered] = useState(false);

    // Hover state for property tooltips
    const [hoveredProp, setHoveredProp] = useState(null);
    const [showTooltip, setShowTooltip] = useState(false);
    const hoverTimeoutRef = useRef(null);

    // Hover state for data table
    const [showDataTable, setShowDataTable] = useState(false);
    const dataTableTimeoutRef = useRef(null);
    const hideTableTimeoutRef = useRef(null);
    const nodeRef = useRef(null);
    const [isHoveringHandle, setIsHoveringHandle] = useState(false);
    const [hoveredHandleId, setHoveredHandleId] = useState(null);

    // Property hover handlers
    const handlePropertyMouseEnter = (propKey, propValue) => {
      setHoveredProp({ key: propKey, value: propValue });

      // Show tooltip after 0.5 seconds
      hoverTimeoutRef.current = setTimeout(() => {
        setShowTooltip(true);
      }, 500);
    };

    const handlePropertyMouseLeave = () => {
      // Clear timeout if mouse leaves before 2 seconds
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
      setShowTooltip(false);
      setHoveredProp(null);
    };

    // Action buttons configuration
    const actionButtons = [
      {
        label: "Edit",
        icon: <Edit />,
        onClick: handleEdit,
      },
      {
        label: "Duplicate",
        icon: <FileCopy />,
        onClick: handleDuplicate,
      },
      {
        label: "Delete",
        icon: <Delete />,
        onClick: handleDelete,
      },
    ];

    // Data table hover handlers
    const handleNodeMouseEnter = (e) => {
      // Check if hovering over a handle (connection point)
      const target = e.target;
      const isHandle =
        target.classList.contains("react-flow__handle") ||
        target.closest(".react-flow__handle");

      if (isHandle) {
        setIsHoveringHandle(true);
        return; // Don't show data table when hovering over handles
      }

      setIsHovered(true);

      // Clear any pending hide timeout
      if (hideTableTimeoutRef.current) {
        clearTimeout(hideTableTimeoutRef.current);
        hideTableTimeoutRef.current = null;
      }

      // Only set show timeout if table is not already visible and not hovering over handle
      if (!showDataTable && !dataTableTimeoutRef.current && !isHoveringHandle) {
        // Show data table after 800ms hover
        dataTableTimeoutRef.current = setTimeout(() => {
          setShowDataTable(true);
          dataTableTimeoutRef.current = null;
        }, 800);
      }
    };

    const handleNodeMouseLeave = () => {
      setIsHovered(false);

      // Clear show timeout if mouse leaves before table appears
      if (dataTableTimeoutRef.current) {
        clearTimeout(dataTableTimeoutRef.current);
        dataTableTimeoutRef.current = null;
      }

      // Only start hide timeout if not already pending
      if (!hideTableTimeoutRef.current) {
        // Hide data table after 500ms delay
        hideTableTimeoutRef.current = setTimeout(() => {
          setShowDataTable(false);
          hideTableTimeoutRef.current = null;
        }, 500);
      }
    };

    // Handler for when mouse enters the data table
    const handleTableMouseEnter = () => {
      // Clear any pending hide timeout when mouse enters table
      if (hideTableTimeoutRef.current) {
        clearTimeout(hideTableTimeoutRef.current);
        hideTableTimeoutRef.current = null;
      }

      // Clear any pending show timeout
      if (dataTableTimeoutRef.current) {
        clearTimeout(dataTableTimeoutRef.current);
        dataTableTimeoutRef.current = null;
      }

      // Ensure table remains visible
      setShowDataTable(true);
    };

    // Handler for when mouse leaves the data table
    const handleTableMouseLeave = () => {
      // Only start hide timeout if not already pending
      if (!hideTableTimeoutRef.current) {
        // Hide table after 500ms when mouse leaves table
        hideTableTimeoutRef.current = setTimeout(() => {
          setShowDataTable(false);
          hideTableTimeoutRef.current = null;
        }, 500);
      }
    };

    // Cleanup timeouts on unmount
    useEffect(() => {
      return () => {
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current);
        }
        if (dataTableTimeoutRef.current) {
          clearTimeout(dataTableTimeoutRef.current);
        }
        if (hideTableTimeoutRef.current) {
          clearTimeout(hideTableTimeoutRef.current);
        }
      };
    }, []);

    return (
      <div
        ref={nodeRef}
        className="base-node-wrapper"
        onMouseEnter={handleNodeMouseEnter}
        onMouseLeave={handleNodeMouseLeave}
        style={{ position: "relative" }}
      >
        {/* Extended Action Bar */}
        {isHovered && (
          <div className="base-node-action-bar">
            {actionButtons.map((action, idx) => (
              <Tooltip key={idx} title={action.label} arrow placement="top">
                <IconButton
                  onClick={(e) => {
                    e.stopPropagation();
                    action.onClick();
                  }}
                  className="base-node-action-btn"
                >
                  {action.icon}
                </IconButton>
              </Tooltip>
            ))}
          </div>
        )}

        <Paper
          elevation={0}
          className={`base-node-paper ${selected ? "selected" : ""}`}
          sx={{
            minWidth: styles.minWidth || 200,
            minHeight: styles.minHeight || 100,
            bgcolor: "background.paper",
            border: selected
              ? `2px solid ${styles.borderColor || theme.palette.primary.main}`
              : `1px solid`,
            borderColor: selected
              ? styles.borderColor || theme.palette.primary.main
              : "divider",
            boxShadow: theme.shadows[2],
            "&:hover": {
              boxShadow: theme.shadows[4],
            },
            "&.selected": {
              boxShadow: theme.shadows[6],
            },
          }}
        >
          {/* Node Header (Colored) - Icon + Title */}
          <div
            className="base-node-header"
            style={{
              backgroundColor: styles.bgColor || "#e0e0e0",
            }}
          >
            <div className="base-node-header-left">
              <div className="base-node-indicator-dot">
                {getCategoryIcon(category, data?.ui?.label)}
              </div>
              <Typography
                variant="subtitle2"
                className="base-node-title-in-header"
              >
                {data?.ui?.label || "Node"}
              </Typography>
            </div>
          </div>

          {/* Node Body (White) - Properties Only */}
          <div className="base-node-body">
            {/* Properties */}
            {displayProps.length > 0 ? (
              <div className="base-node-properties">
                {displayProps.map((prop, idx) => {
                  const propKey = `${prop.label}-${idx}`;
                  const isHoveredProp =
                    hoveredProp?.key === propKey && showTooltip;

                  // Check if property value is empty
                  const isEmpty =
                    !prop.value ||
                    prop.value === "" ||
                    prop.value === "null" ||
                    prop.value === "undefined";

                  const displayValue = isEmpty
                    ? "Not assigned"
                    : prop.type === "json"
                    ? "JSON"
                    : prop.value;

                  return (
                    <div key={propKey} className="base-node-property-row">
                      <Typography
                        variant="caption"
                        className="base-node-property-label"
                      >
                        {prop.label}
                      </Typography>
                      <div
                        className="base-node-property-value"
                        onMouseEnter={() =>
                          handlePropertyMouseEnter(propKey, prop.value)
                        }
                        onMouseLeave={handlePropertyMouseLeave}
                        style={{ position: "relative" }}
                      >
                        <div
                          className="base-node-property-value-text"
                          style={{
                            color: isEmpty
                              ? theme.palette.text.disabled
                              : "inherit",
                            fontStyle: isEmpty ? "italic" : "normal",
                          }}
                        >
                          {displayValue}
                        </div>

                        {/* Delayed Tooltip */}
                        {isHoveredProp && !isEmpty && (
                          <Box
                            sx={{
                              position: "absolute",
                              top: "100%",
                              left: 0,
                              marginTop: "8px",
                              padding: "8px 12px",
                              bgcolor: "background.paper",
                              color: "text.primary",
                              border: "1px solid",
                              borderColor: "divider",
                              borderRadius: "6px",
                              fontSize: "0.75rem",
                              maxWidth: "300px",
                              wordBreak: "break-word",
                              zIndex: 9000,
                              boxShadow: theme.shadows[4],
                              animation: "fadeIn 0.2s ease-in",
                              pointerEvents: "none",
                              whiteSpace: "pre-wrap",
                            }}
                          >
                            {prop.type === "json" ? prop.value : prop.value}
                          </Box>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  fontStyle: "italic",
                  textAlign: "left",
                  display: "block",
                  fontSize: "0.75rem",
                }}
              >
                Click to add properties
              </Typography>
            )}
          </div>

          {/* INPUT HANDLES */}
          {inputs.map((input, i) => {
            const handleId = input.id || `in-${i}`;
            const isHovered = hoveredHandleId === handleId;
            return (
              <Handle
                key={`in-${i}`}
                type="target"
                position={input.position || Position.Left}
                id={handleId}
                onMouseEnter={() => {
                  setHoveredHandleId(handleId);
                  setIsHoveringHandle(true);
                  // Cancel data table timeout
                  if (dataTableTimeoutRef.current) {
                    clearTimeout(dataTableTimeoutRef.current);
                    dataTableTimeoutRef.current = null;
                  }
                }}
                onMouseLeave={() => {
                  setHoveredHandleId(null);
                  setIsHoveringHandle(false);
                }}
                style={{
                  background: isHovered
                    ? "#4CAF50"
                    : theme.palette.background.paper,
                  top: input.top || `${((i + 1) / (inputs.length + 1)) * 100}%`,
                  left: "-5px",
                  width: isHovered ? 14 : 10,
                  height: isHovered ? 14 : 10,
                  borderRadius: "50%",
                  border: isHovered
                    ? "3px solid #2E7D32"
                    : `2px solid ${theme.palette.divider}`,
                  boxShadow: isHovered
                    ? "0 0 8px rgba(76, 175, 80, 0.6)"
                    : "none",
                  transition: "all 0.2s ease",
                  zIndex: isHovered ? 100 : 1,
                }}
              />
            );
          })}

          {/* OUTPUT HANDLES */}
          {outputs.map((output, i) => {
            const handleId = output.id || `out-${i}`;
            const isHovered = hoveredHandleId === handleId;
            return (
              <Handle
                key={`out-${i}`}
                type="source"
                position={output.position || Position.Right}
                id={handleId}
                onMouseEnter={() => {
                  setHoveredHandleId(handleId);
                  setIsHoveringHandle(true);
                  // Cancel data table timeout
                  if (dataTableTimeoutRef.current) {
                    clearTimeout(dataTableTimeoutRef.current);
                    dataTableTimeoutRef.current = null;
                  }
                }}
                onMouseLeave={() => {
                  setHoveredHandleId(null);
                  setIsHoveringHandle(false);
                }}
                style={{
                  background: isHovered
                    ? "#2196F3"
                    : theme.palette.background.paper,
                  top:
                    output.top || `${((i + 1) / (outputs.length + 1)) * 100}%`,
                  right: "-5px",
                  width: isHovered ? 14 : 10,
                  height: isHovered ? 14 : 10,
                  borderRadius: "50%",
                  border: isHovered
                    ? "3px solid #1565C0"
                    : `2px solid ${theme.palette.divider}`,
                  boxShadow: isHovered
                    ? "0 0 8px rgba(33, 150, 243, 0.6)"
                    : "none",
                  transition: "all 0.2s ease",
                  zIndex: isHovered ? 100 : 1,
                }}
              />
            );
          })}
        </Paper>

        {/* Data table for non-output nodes only */}
        {status == "Running" && !isOutputNode() ? (
          <NodeDataTable
            nodeId={id}
            tableName={getTableName()}
            isVisible={showDataTable}
            nodeRef={nodeRef}
            onMouseEnter={handleTableMouseEnter}
            onMouseLeave={handleTableMouseLeave}
          />
        ) : null}
      </div>
    );
  }
);
