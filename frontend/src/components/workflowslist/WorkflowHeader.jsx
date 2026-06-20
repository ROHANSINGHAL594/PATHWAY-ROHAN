import { useState } from "react";
import {
  Box,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import {
  Add as AddIcon,
  FilterListOutlined as FilterListOutlinedIcon,
  LoopOutlined as LoopOutlinedIcon,
  WarningAmberOutlined as WarningAmberOutlinedIcon,
  FlagOutlined as FlagOutlinedIcon,
  SaveOutlined as SaveOutlinedIcon,
} from "@mui/icons-material";

const WorkflowHeader = ({ onAddNew, selectedTab, onTabChange }) => {
  const [filterAnchorEl, setFilterAnchorEl] = useState(null);
  const filterOpen = Boolean(filterAnchorEl);

  const handleFilterClick = (event) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };

  const handleFilterOption = (option) => {
    // Map filter options to tab indices
    // 0: All, 1: Running, 2: Stopped, 3: Broken
    const filterMap = {
      all: 0,
      inProgress: 1, // Running
      save: 2, // Stopped
      broken: 3, // Broken
    };

    const tabIndex = filterMap[option] !== undefined ? filterMap[option] : 0;
    if (onTabChange) {
      onTabChange(tabIndex);
    }
    handleFilterClose();
  };

  return (
    <Box
      sx={{
        flexShrink: 0,
        pb: 2,
        borderBottom: { xs: `1px solid`, lg: "none" },
        borderColor: "divider",
      }}
    >
      {/* Header */}
      <Box sx={{ mb: 2, px: 2 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography
            variant="h6"
            sx={{
              fontWeight: 600,
              color: "text.primary",
              fontSize: "1.125rem",
            }}
          >
            Workflows
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon sx={{ fontSize: 16 }} />}
              onClick={onAddNew}
            >
              Add new
            </Button>
            {/* Filter */}
            <IconButton
              onClick={handleFilterClick}
              sx={{
                bgcolor: "background.elevation1",
                borderRadius: "8px",
                width: 36,
                height: 36,
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              <FilterListOutlinedIcon
                sx={{ fontSize: 20, color: "text.secondary" }}
              />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={filterOpen}
        onClose={handleFilterClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        slotProps={{
          paper: {
            elevation: 3,
            sx: {
              mt: 1,
              minWidth: 200,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
            },
          },
        }}
      >
        <MenuItem onClick={() => handleFilterOption("all")} sx={{ py: 1.5 }}>
          <ListItemIcon sx={{ mr: 2 }}>
            <Box
              sx={{
                bgcolor: "background.elevation1",
                borderRadius: "6px",
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <LoopOutlinedIcon
                sx={{ fontSize: 18, color: "text.secondary" }}
              />
            </Box>
          </ListItemIcon>
          <ListItemText>All Workflows</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => handleFilterOption("inProgress")}
          sx={{ py: 1.5 }}
        >
          <ListItemIcon sx={{ mr: 2 }}>
            <Box
              sx={{
                bgcolor: "background.elevation1",
                borderRadius: "6px",
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <LoopOutlinedIcon
                sx={{ fontSize: 18, color: "text.secondary" }}
              />
            </Box>
          </ListItemIcon>
          <ListItemText>Running</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterOption("save")} sx={{ py: 1.5 }}>
          <ListItemIcon sx={{ mr: 2 }}>
            <Box
              sx={{
                bgcolor: "background.elevation1",
                borderRadius: "6px",
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <SaveOutlinedIcon
                sx={{ fontSize: 18, color: "text.secondary" }}
              />
            </Box>
          </ListItemIcon>
          <ListItemText>Stopped</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterOption("broken")} sx={{ py: 1.5 }}>
          <ListItemIcon sx={{ mr: 2 }}>
            <Box
              sx={{
                bgcolor: "background.elevation1",
                borderRadius: "6px",
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <SaveOutlinedIcon
                sx={{ fontSize: 18, color: "error.main" }}
              />
            </Box>
          </ListItemIcon>
          <ListItemText>Broken</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default WorkflowHeader;
