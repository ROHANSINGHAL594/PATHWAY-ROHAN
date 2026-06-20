//TODO: Make the node accept only one input per handle

import React, { useState, useEffect } from "react";
import {
  Drawer,
  Box,
  Typography,
  Grid,
  Paper,
  Avatar,
  Collapse,
  IconButton,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
  useTheme,
} from "@mui/material";
import {
  ExpandMore,
  ExpandLess,
  Extension,
  Close as CloseIcon,
  Search as SearchIcon,
  Input as InputIcon,
  Transform as TransformIcon,
  ControlCamera as ControlCameraIcon,
  Launch as OutputIcon,
  ViewList as ViewListIcon,
  ArrowForward as ArrowForwardIcon,
} from "@mui/icons-material";
import { fetchNodeTypes } from "../../utils/dashboard.utils";
import "../../css/NodeDrawer.css";

/**
 * Get icon for category type
 */
const getCategoryIcon = (category, theme) => {
  const iconProps = {
    sx: { fontSize: 20, color: theme.palette.text.secondary },
  };

  switch (category.toLowerCase()) {
    case "input":
      return <InputIcon {...iconProps} />;
    case "output":
      return <OutputIcon {...iconProps} />;
    case "transform":
    case "table":
    case "temporal":
      return <TransformIcon {...iconProps} />;
    default:
      return <Extension {...iconProps} />;
  }
};

/**
 * Get icon component for individual node based on category
 */
const getNodeIcon = (category) => {
  const iconProps = { sx: { fontSize: 50, color: "#77878F" } };
  const categoryLower = (category || "").toLowerCase();

  // IO nodes
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

  // Default fallback
  return <ArrowForwardIcon {...iconProps} />;
};

export const NodeDrawer = ({
  open,
  onClose,
  onAddNode,
  onDragStart: onDragStartProp,
  currentNodes = [],
  undoDeque = [],
  zIndex,
}) => {
  const theme = useTheme();
  const [openSections, setOpenSections] = useState({});
  const [nodeCategories, setNodeCategories] = useState({});
  const [loading, setLoading] = useState(true);
  const [clickedNode, setClickedNode] = useState(null);
  const [activeTab, setActiveTab] = useState(1); // Default to "All Files" tab
  const [searchQuery, setSearchQuery] = useState("");

  // Compute recent nodes from current workspace and undo deque
  const recentNodes = React.useMemo(() => {
    const nodeSet = new Set();

    // Add nodes from current workspace
    currentNodes.forEach((node) => {
      if (node.data?.ui?.label) {
        nodeSet.add(node.data.ui.label);
      }
    });

    // Add nodes from undo deque (actions involving nodes)
    undoDeque.forEach((action) => {
      if (action.type === "ADD_NODE" && action.node?.data?.ui?.label) {
        nodeSet.add(action.node.data.ui.label);
      } else if (
        action.type === "REMOVE_NODE" &&
        action.node?.data?.ui?.label
      ) {
        nodeSet.add(action.node.data.ui.label);
      }
    });

    // Convert to array and limit to 10 most recent
    return Array.from(nodeSet).slice(0, 10);
  }, [currentNodes, undoDeque]);

  // Fetch all node categories dynamically from backend
  useEffect(() => {
    const loadNodeTypes = async () => {
      try {
        setLoading(true);
        const data = await fetchNodeTypes();
        // data.input=["hello"];
        setNodeCategories(data || {});

        // close all sections by default
        const initialOpen = Object.keys(data || {}).reduce((acc, key) => {
          acc[key] = false;
          return acc;
        }, {});
        setOpenSections(initialOpen);
      } catch (err) {
        console.error("Failed to load node types:", err);
      } finally {
        setLoading(false);
      }
    };
    loadNodeTypes();
  }, []);

  // Auto-expand/collapse sections based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      // If search is cleared, close all sections
      setOpenSections((prev) => {
        const closed = {};
        Object.keys(prev).forEach((key) => {
          closed[key] = false;
        });
        return closed;
      });
    } else {
      // If search has input, open all sections that have matching nodes
      setOpenSections((prev) => {
        const updated = { ...prev };
        Object.entries(nodeCategories).forEach(([key, nodes]) => {
          const hasMatchingNodes = nodes.some((node) =>
            node.toLowerCase().includes(searchQuery.toLowerCase())
          );
          if (hasMatchingNodes) {
            updated[key] = true;
          }
        });
        return updated;
      });
    }
  }, [searchQuery, nodeCategories]);

  const toggleSection = (key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleNodeClick = (nodeName) => {
    // Show drag and drop popup
    setClickedNode(nodeName);

    // Hide popup after 2 seconds
    setTimeout(() => {
      setClickedNode(null);
    }, 2000);
  };

  const onDragStart = (event, nodeName) => {
    event.dataTransfer.setData("application/reactflow", nodeName);
    event.dataTransfer.effectAllowed = "move";

    // Close the drawer immediately when drag starts
    onClose();

    // Notify parent component if needed
    if (onDragStartProp) {
      onDragStartProp(nodeName);
    }
  };

  // Helper to get category for a node name
  const getCategoryForNode = (nodeName) => {
    for (const [category, nodes] of Object.entries(nodeCategories)) {
      if (nodes.includes(nodeName)) {
        return category;
      }
    }
    return "default";
  };

  const renderCategory = (key, nodes = []) => {
    // Filter nodes based on search query
    const filteredNodes = nodes.filter((node) =>
      node.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (searchQuery && filteredNodes.length === 0) return null;

    return (
      <Box key={key} sx={{ mb: 2 }}>
        {/* Header */}
        <Box
          onClick={() => toggleSection(key)}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            cursor: "pointer",
            px: 2,
            py: 1.5,
            borderRadius: 1,
            "&:hover": { bgcolor: "action.hover" },
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            {getCategoryIcon(key, theme)}
            <Typography
              variant="subtitle1"
              fontWeight={600}
              sx={{
                fontSize: "0.875rem",
                color: "text.primary",
              }}
            >
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </Typography>
          </Box>
          <IconButton size="small" sx={{ color: "text.secondary" }}>
            {openSections[key] ? (
              <ExpandLess fontSize="small" />
            ) : (
              <ExpandMore fontSize="small" />
            )}
          </IconButton>
        </Box>

        {/* Node List */}
        <Collapse in={openSections[key]}>
          {loading ? (
            <Typography
              variant="body2"
              sx={{
                textAlign: "center",
                color: "#9ca3af",
                fontSize: "0.8125rem",
                py: 1.5,
                px: 2,
              }}
            >
              Loading...
            </Typography>
          ) : !filteredNodes || filteredNodes.length === 0 ? (
            <Typography
              variant="body2"
              sx={{
                textAlign: "center",
                color: "#9ca3af",
                fontSize: "0.8125rem",
                py: 1.5,
                px: 2,
              }}
            >
              No nodes found.
            </Typography>
          ) : (
            <Grid
              container
              spacing={1.5}
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: 1.5,
                px: 2,
                pb: 1.5,
              }}
            >
              {filteredNodes.map((nodeName, i) => (
                <Box
                  key={i}
                  onClick={() => handleNodeClick(nodeName)}
                  draggable
                  onDragStart={(event) => onDragStart(event, nodeName)}
                  sx={{
                    position: "relative",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    cursor: "grab",
                    transition: "all 0.2s ease",
                    "&:active": {
                      cursor: "grabbing",
                    },
                  }}
                >
                  {/* Image Container with Gray Background */}
                  <Paper
                    elevation={0}
                    sx={{
                      width: "100%",
                      height: 100,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: 2,
                      bgcolor: "background.elevation1",
                      border: "1px solid",
                      borderColor: "divider",
                      transition: "all 0.2s ease",
                      mb: 1,
                      "&:hover": {
                        transform: "translateY(-2px)",
                        boxShadow: theme.shadows[2],
                        borderColor: "divider",
                      },
                    }}
                  >
                    {getNodeIcon(key)}

                    {/* Drag and Drop Popup */}
                    {clickedNode === nodeName && (
                      <Box
                        sx={{
                          position: "absolute",
                          top: "50%",
                          left: "50%",
                          transform: "translate(-50%, -50%)",
                          bgcolor: "background.paper",
                          color: "text.primary",
                          border: "1px solid",
                          borderColor: "divider",
                          padding: "6px 12px",
                          borderRadius: "6px",
                          fontSize: "0.6875rem",
                          fontWeight: 500,
                          whiteSpace: "nowrap",
                          zIndex: 10,
                          pointerEvents: "none",
                          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
                          animation: "fadeInOut 2s ease-in-out",
                        }}
                      >
                        Drag and Drop
                      </Box>
                    )}
                  </Paper>

                  {/* Text Outside Gray Background */}
                  <Typography
                    variant="body2"
                    sx={{
                      textAlign: "center",
                      wordBreak: "break-word",
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#374151",
                      width: "100%",
                      px: 1,
                      pointerEvents: "none",
                      lineHeight: 1.3,
                      mb: 0.5,
                    }}
                  >
                    {nodeName}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      textAlign: "center",
                      fontSize: "0.6875rem",
                      fontWeight: 400,
                      color: "#9ca3af",
                      pointerEvents: "none",
                    }}
                  >
                    ID: {nodeName.split("_")[0]}
                  </Typography>
                </Box>
              ))}
            </Grid>
          )}
        </Collapse>
      </Box>
    );
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        zIndex: zIndex || 1200,
        "& .MuiDrawer-paper": {
          width: 400,
          boxSizing: "border-box",
          bgcolor: "background.paper",
          top: 0,
          borderLeft: "1px solid",
          borderColor: "divider",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: { xs: "16px 16px", md: "17px 24px" },
          borderBottom: "2px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: 700, fontSize: "1rem", color: "text.primary" }}
        >
          All Nodes
        </Typography>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: "text.secondary",
            "&:hover": { bgcolor: "action.hover" },
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* --- START CHANGED SECTION: Small Tabs and Search Bar --- */}
      <Box
        sx={{
          px: 3,
          py: 1, // Reduced padding vertical
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between", // Ensures Left/Right separation
          gap: 1,
        }}
      >
        {/* Tabs on the left - Smaller */}
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{
            minHeight: 30, // Smaller height
            "& .MuiTab-root": {
              minHeight: 30,
              minWidth: "auto",
              px: 1.5, // Tighter padding
              textTransform: "none",
              fontWeight: 500,
              fontSize: "0.75rem", // Smaller font
              color: "text.secondary",
              "&.Mui-selected": {
                color: "primary.main",
              },
            },
            "& .MuiTabs-indicator": {
              bgcolor: "primary.main",
              height: 2,
            },
          }}
        >
          <Tab label="Recent" />
          <Tab label="All Files" />
        </Tabs>

        {/* Search Bar on the right - Smaller */}
        <TextField
          placeholder="Search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 16, color: "text.secondary" }} />
              </InputAdornment>
            ),
          }}
          sx={{
            width: 140, // Reduced width
            "& .MuiOutlinedInput-root": {
              borderRadius: 20,
              bgcolor: "action.hover",
              fontSize: "0.75rem", // Smaller text
              height: 30, // Smaller height
              "& fieldset": {
                borderColor: "transparent",
              },
              "&:hover fieldset": {
                borderColor: "divider",
              },
              "&.Mui-focused fieldset": {
                borderColor: "primary.main",
                borderWidth: 1,
              },
              "& input": {
                py: 0, // Remove padding for perfect centering in small height
              },
            },
          }}
        />
      </Box>
      {/* --- END CHANGED SECTION --- */}

      {/* Scrollable Content */}
      <Box sx={{ overflowY: "auto", flex: 1 }}>
        {activeTab === 0 ? (
          // Recent Tab
          <Box sx={{ px: 1 }}>
            {recentNodes.length === 0 ? (
              <Typography
                variant="body2"
                sx={{
                  textAlign: "center",
                  color: "text.secondary",
                  fontSize: "0.8125rem",
                  py: 4,
                }}
              >
                No recent nodes
              </Typography>
            ) : (
              <Box sx={{ px: 2, py: 1 }}>
                <Grid
                  container
                  spacing={1.5}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 1.5,
                  }}
                >
                  {recentNodes.map((nodeName, i) => (
                    <Box
                      key={i}
                      onClick={() => handleNodeClick(nodeName)}
                      draggable
                      onDragStart={(event) => onDragStart(event, nodeName)}
                      sx={{
                        position: "relative",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        cursor: "grab",
                        transition: "all 0.2s ease",
                        "&:active": {
                          cursor: "grabbing",
                        },
                      }}
                    >
                      {/* Image Container with Gray Background */}
                      <Paper
                        elevation={0}
                        sx={{
                          width: "100%",
                          height: 100,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 2,
                          bgcolor: "background.elevation1",
                          border: "1px solid",
                          borderColor: "divider",
                          transition: "all 0.2s ease",
                          mb: 1,
                          "&:hover": {
                            transform: "translateY(-2px)",
                            boxShadow: theme.shadows[2],
                            borderColor: "divider",
                          },
                        }}
                      >
                        {getNodeIcon(getCategoryForNode(nodeName))}
                      </Paper>

                      {/* Text Outside Gray Background */}
                      <Typography
                        variant="body2"
                        sx={{
                          textAlign: "center",
                          wordBreak: "break-word",
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          color: "text.primary",
                          width: "100%",
                          px: 1,
                          pointerEvents: "none",
                          lineHeight: 1.3,
                          mb: 0.5,
                        }}
                      >
                        {nodeName}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          textAlign: "center",
                          fontSize: "0.6875rem",
                          fontWeight: 400,
                          color: "text.secondary",
                          pointerEvents: "none",
                        }}
                      >
                        ID: {nodeName.split("_")[0]}
                      </Typography>
                    </Box>
                  ))}
                </Grid>
              </Box>
            )}
          </Box>
        ) : (
          // All Files Tab
          <Box>
            {Object.keys(nodeCategories).length === 0 && !loading ? (
              <Typography
                variant="body2"
                sx={{
                  textAlign: "center",
                  color: "text.secondary",
                  fontSize: "0.8125rem",
                  py: 4,
                }}
              >
                No node categories found.
              </Typography>
            ) : (
              Object.entries(nodeCategories).map(([key, nodes]) =>
                renderCategory(key, nodes)
              )
            )}
          </Box>
        )}
      </Box>
    </Drawer>
  );
};
