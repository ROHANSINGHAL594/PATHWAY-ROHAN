import { useState, useEffect, useMemo } from "react";
import { Box, Typography, TextField, MenuItem, Select, FormControl, Button, Chip, OutlinedInput } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

const AddAIAgent = ({ formData, onInputChange, onSelectChange, onAgentsChange, nodes = [] }) => {
  // Convert nodes to tool options - use node id as tool id and node label or node_id as label
  const toolOptions = useMemo(() => {
    return nodes.map((node) => ({
      id: node.id, // The unique instance id of the node in the canvas
      label: node.data?.ui?.label || node.node_id || node.id,
      nodeType: node.node_id, // The type of node (e.g., "csv", "kafka", etc.)
    }));
  }, [nodes]);
  const [agents, setAgents] = useState([]);
  const [currentAgent, setCurrentAgent] = useState({
    name: "",
    description: "",
    tools: [],
  });

  // Notify parent when agents change (include current agent if valid)
  useEffect(() => {
    if (onAgentsChange) {
      // Include the current agent if it has valid data
      const currentAgentIsValid = currentAgent.name && currentAgent.description && currentAgent.tools.length > 0;
      const allAgents = currentAgentIsValid 
        ? [...agents, { ...currentAgent }]
        : [...agents];
      onAgentsChange(allAgents);
    }
  }, [agents, currentAgent, onAgentsChange]);

  const handleFieldChange = (field) => (event) => {
    const newValue = event.target.value;
    setCurrentAgent((prev) => ({
      ...prev,
      [field]: newValue,
    }));
  };

  const handleToolsChange = (event) => {
    const value = event.target.value;
    // Handle both string and array (for multiple select)
    setCurrentAgent((prev) => ({
      ...prev,
      tools: typeof value === 'string' ? value.split(',') : value,
    }));
  };

  const handleAddAgent = () => {
    if (currentAgent.name && currentAgent.description && currentAgent.tools.length > 0) {
      const newAgents = [...agents, { ...currentAgent }];
      setAgents(newAgents);
      
      // Clear current agent form
      setCurrentAgent({
        name: "",
        description: "",
        tools: [],
      });
    }
  };

  const isFormComplete = currentAgent.name && currentAgent.description && currentAgent.tools.length > 0;

  // Render agent form section
  const renderAgentForm = (agentData, index, isEditable = false, showLabel = true) => (
    <Box
      key={index}
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2.5,
        p: 0,
        mb: 2.5,
      }}
    >
      {showLabel && (
        <Typography
          variant="h6"
          sx={{
            fontWeight: 600,
            color: "text.primary",
            mb: -1,
            textAlign: "right",
            fontSize: "1.25rem",
          }}
        >
          Agent {index}
        </Typography>
      )}

      {/* Name Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Name
        </Typography>
        {isEditable ? (
          <TextField
            fullWidth
            placeholder="Name"
            value={agentData.name}
            onChange={handleFieldChange("name")}
            variant="filled"
            disabled={false}
            required
            InputProps={{
              disableUnderline: true,
            }}
            sx={{
              pointerEvents: "auto !important",
              "& .MuiFilledInput-root": {
                pointerEvents: "auto !important",
                bgcolor: "background.elevation2",
                borderRadius: 2,
                "&:hover": { bgcolor: "background.elevation1" },
                "&.Mui-focused": {
                  bgcolor: "background.elevation1",
                  boxShadow: (theme) => `0 0 0 2px ${theme.palette.primary.light}`,
                },
              },
              "& .MuiFilledInput-input": {
                py: 1.5,
                px: 2,
                fontSize: "0.875rem",
                pointerEvents: "auto !important",
                "&::placeholder": { color: "text.secondary", opacity: 1 },
              },
            }}
          />
        ) : (
          <Typography
            variant="body2"
            sx={{
              color: "text.primary",
              py: 1.5,
              px: 2,
              bgcolor: "background.elevation2",
              borderRadius: 2,
            }}
          >
            {agentData.name}
          </Typography>
        )}
      </Box>

      {/* Description Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Description
        </Typography>
        {isEditable ? (
          <TextField
            fullWidth
            placeholder="Description"
            value={agentData.description}
            onChange={handleFieldChange("description")}
            variant="filled"
            multiline
            rows={4}
            disabled={false}
            required
            InputProps={{
              disableUnderline: true,
            }}
            sx={{
              pointerEvents: "auto !important",
              "& .MuiFilledInput-root": {
                pointerEvents: "auto !important",
                bgcolor: "background.elevation2",
                borderRadius: 2,
                "&:hover": { bgcolor: "background.elevation1" },
                "&.Mui-focused": {
                  bgcolor: "background.elevation1",
                  boxShadow: (theme) => `0 0 0 2px ${theme.palette.primary.light}`,
                },
              },
              "& .MuiFilledInput-input": {
                py: 1,
                px: 1.5,
                fontSize: "0.875rem",
                pointerEvents: "auto !important",
                "&::placeholder": { color: "text.secondary", opacity: 1 },
              },
            }}
          />
        ) : (
          <Typography
            variant="body2"
            sx={{
              color: "text.primary",
              py: 1.5,
              px: 2,
              bgcolor: "background.elevation2",
              borderRadius: 2,
              whiteSpace: "pre-wrap",
            }}
          >
            {agentData.description}
          </Typography>
        )}
      </Box>

      {/* Tools Selection Dropdown (Multi-select) */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Tools
        </Typography>
        {isEditable ? (
          <FormControl
            fullWidth
            variant="filled"
            sx={{
              pointerEvents: "auto !important",
              "& .MuiFilledInput-root": {
                pointerEvents: "auto !important",
                bgcolor: "background.elevation2",
                borderRadius: 2,
                "&:hover": { bgcolor: "background.elevation1" },
                "&.Mui-focused": {
                  bgcolor: "background.elevation1",
                  boxShadow: (theme) => `0 0 0 2px ${theme.palette.primary.light}`,
                },
                "&:before": {
                  display: "none",
                },
                "&:after": {
                  display: "none",
                },
              },
              "& .MuiFilledInput-input": {
                py: 1,
                px: 1.5,
                fontSize: "0.875rem",
                pointerEvents: "auto !important",
              },
              "& .MuiSelect-icon": {
                color: "text.secondary",
                pointerEvents: "auto !important",
              },
            }}
          >
            <Select
              multiple
              value={agentData.tools}
              onChange={handleToolsChange}
              displayEmpty
              disabled={false}
              required
              input={<OutlinedInput />}
              renderValue={(selected) => {
                if (selected.length === 0) {
                  return <Typography sx={{ color: "text.secondary" }}>Select tools (nodes)</Typography>;
                }
                return (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => {
                      const tool = toolOptions.find(t => t.id === value);
                      return <Chip key={value} label={tool?.label || value} size="small" />;
                    })}
                  </Box>
                );
              }}
              MenuProps={{
                disablePortal: false,
                style: { zIndex: 10004 },
              }}
              sx={{
                pointerEvents: "auto !important",
                cursor: "pointer",
                bgcolor: "background.elevation2",
                borderRadius: 2,
                "& .MuiOutlinedInput-notchedOutline": {
                  border: "none",
                },
                "& .MuiSelect-select": {
                  pointerEvents: "auto !important",
                  cursor: "pointer",
                  py: 1.5,
                  "&:focus": {
                    bgcolor: "transparent",
                  },
                },
              }}
            >
              {toolOptions.length === 0 ? (
                <MenuItem disabled value="">
                  No nodes available - add nodes in Step 2
                </MenuItem>
              ) : (
                toolOptions.map((option) => (
                  <MenuItem key={option.id} value={option.id}>
                    {option.label}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        ) : (
          <Box
            sx={{
              py: 1.5,
              px: 2,
              bgcolor: "background.elevation2",
              borderRadius: 2,
              display: 'flex',
              flexWrap: 'wrap',
              gap: 0.5,
            }}
          >
            {agentData.tools.map((toolId) => {
              const tool = toolOptions.find(t => t.id === toolId);
              return <Chip key={toolId} label={tool?.label || toolId} size="small" />;
            })}
          </Box>
        )}
      </Box>
    </Box>
  );

  return (
    <Box 
      sx={{ 
        display: "flex", 
        flexDirection: "column", 
        gap: 2.5,
        position: "relative",
        zIndex: 1,
        pointerEvents: "auto",
      }}
    >
      {/* Render all added agents */}
      {agents.map((agent, index) => renderAgentForm(agent, index + 1, false, true))}

      {/* Current agent form (editable) - always show label */}
      {renderAgentForm(currentAgent, agents.length + 1, true, true)}

      {/* Add Agent Button - Always visible */}
      <Box sx={{ display: "flex", justifyContent: "flex-start", mt: -1 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddAgent}
          disabled={!isFormComplete}
          sx={{
            textTransform: "none",
            borderRadius: 2,
            px: 3,
            py: 1,
            bgcolor: "primary.main",
            color: "common.white",
            fontWeight: 500,
            "&:hover": {
              bgcolor: "primary.dark",
            },
            "&:disabled": {
              bgcolor: "action.disabledBackground",
              color: "action.disabled",
            },
          }}
        >
          Add More Agents
        </Button>
      </Box>
    </Box>
  );
};

export default AddAIAgent;
