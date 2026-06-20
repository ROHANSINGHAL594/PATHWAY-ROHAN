import { Box } from "@mui/material";
import { ReactFlow, Background} from "@xyflow/react";
import { useTheme, useColorScheme} from "@mui/material/styles";

const WorkflowCanvas = ({
  nodes,
  edges,
  nodeTypes,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onEdgeClick,
  onInit,
  onDrop,
  onDragOver,
  onPaneClick,
  onCanvasClick,
  nodesDraggable = true,
  nodesConnectable = true,
  elementsSelectable = true,
  isLocked = false,
  onLockToggle,
}) => {
  const theme = useTheme();
  const { colorMode } = useColorScheme();
  const resolvedMode = colorMode || theme.palette.mode;

  return (
    <Box
      sx={{
        flex: 1,
        bgcolor: "background.elevation1",
        borderRadius: 0,
        overflow: "hidden",
        border: "none",
        width: "100%",
        height: "100%",
        minHeight: 0,
      }}
      onClick={onCanvasClick}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={isLocked ? undefined : onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onInit={onInit}
        onDrop={isLocked ? undefined : onDrop}
        onDragOver={isLocked ? undefined : onDragOver}
        onPaneClick={onPaneClick}
        nodesDraggable={!isLocked}
        nodesConnectable={!isLocked}
        elementsSelectable={!isLocked}
        defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
        fitView
        fitViewOptions={{ maxZoom: 0.9 }}
        colorMode={resolvedMode}
      >
        <Background
          color={
            theme.palette.mode === "dark" ? theme.palette.divider : "#DBE6EB"
          }
          gap={16}
          size={2}
        />
      </ReactFlow>
    </Box>
  );
};

export default WorkflowCanvas;
