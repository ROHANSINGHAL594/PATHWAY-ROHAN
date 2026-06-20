import { useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import { Add as AddIcon, Undo as UndoIcon, Redo as RedoIcon } from "@mui/icons-material";
import NearMeOutlinedIcon from '@mui/icons-material/NearMeOutlined';
import NearMeIcon from '@mui/icons-material/NearMe';
import { useTheme } from "@mui/material/styles";

const BottomToolbar = ({ 
  onAddClick, 
  onUndoClick, 
  onRedoClick, 
  onHoverChange, 
  addDisabled = false, 
  undoDisabled = false, 
  redoDisabled = false,
  isLocked = false,
  onLockToggle,
}) => {
  const theme = useTheme();
  const [hoveredButton, setHoveredButton] = useState(null);

  const handleMouseEnter = (buttonType, tooltipText) => {
    setHoveredButton(buttonType);
    if (onHoverChange) {
      onHoverChange(buttonType);
    }
  };

  const handleMouseLeave = () => {
    setHoveredButton(null);
    if (onHoverChange) {
      onHoverChange(null);
    }
  };

  const getTooltipText = (buttonType) => {
    switch (buttonType) {
      case 'add':
        return 'Add Node (Press A)';
      case 'lock':
        return isLocked ? 'Unlock' : 'Lock';
      case 'undo':
        return 'Undo (Ctrl + Z)';
      case 'redo':
        return 'Redo (Ctrl + Shift + Z)';
      default:
        return '';
    }
  };

  return (
    <>
      {/* Tooltip */}
      {hoveredButton && (
        <Box
          sx={{
            position: "absolute",
            bottom: 100,
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            alignItems: "center",
            gap: 0.3,
            zIndex: 1001,
            pointerEvents: "none",
          }}
        >
          <Typography 
            variant="caption" 
            sx={{ 
              fontSize: "0.6rem",
              color: "text.primary",
              textShadow: theme.palette.mode === 'dark' 
                ? "1px 1px 2px rgba(0, 0, 0, 0.9), -1px -1px 2px rgba(0, 0, 0, 0.9), 0 0 3px rgba(0, 0, 0, 0.8)"
                : "1px 1px 2px rgba(255, 255, 255, 0.9), -1px -1px 2px rgba(255, 255, 255, 0.9), 0 0 3px rgba(255, 255, 255, 0.8)",
              display: "flex",
              alignItems: "center",
              gap: 0.2,
              fontWeight: 500,
            }}
          >
            {getTooltipText(hoveredButton)}
          </Typography>
        </Box>
      )}

      {/* Toolbar */}
    <Box
      sx={{
        position: "absolute",
        bottom: 52,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        alignItems: "center",
        gap: 0,
        bgcolor: 'background.elevation1',
        border: "1px solid",
        borderColor: 'divider',
        borderRadius: "12px",
        padding: "0",
        width: "170px",
        height: "48px",
        boxShadow: theme.palette.mode === 'dark'
          ? '0px -2px 6px 0px rgba(0, 0, 0, 0.3), 2px 10px 10px 0px rgba(0, 0, 0, 0.2), 1px 20px 19px 0px rgba(0, 0, 0, 0.2), 6px 33px 46px 0px rgba(0, 0, 0, 0.3)'
          : '0px -2px 6px 0px rgba(0, 0, 0, 0.03), 2px 10px 10px 0px rgba(0, 0, 0, 0.01), 1px 20px 19px 0px rgba(0, 0, 0, 0.03), 6px 33px 46px 0px rgba(0, 0, 0, 0.07)',
        zIndex: 1000,
      }}
    >
      <IconButton
        onClick={onAddClick}
        disabled={addDisabled}
          onMouseEnter={() => handleMouseEnter('add', 'Add Node (Press A)')}
          onMouseLeave={handleMouseLeave}
        sx={{
          bgcolor: 'background.paper',
          color: addDisabled ? 'text.disabled' : "text.primary",
          "&:hover": { bgcolor: addDisabled ? "transparent" : 'action.hover' },
          width: 40,
          height: 40,
          m: 0.5,
          cursor: addDisabled ? "not-allowed" : "pointer",
        }}
      >
        <AddIcon sx={{ fontSize: 20 }} />
      </IconButton>

      <IconButton
          onClick={onLockToggle}
          onMouseEnter={() => handleMouseEnter('lock', isLocked ? 'Unlock' : 'Lock')}
          onMouseLeave={handleMouseLeave}
        sx={{
          color: "text.primary",
          "&:hover": { bgcolor: 'action.hover' },
          width: 40,
          height: 40,
          cursor: "pointer",
        }}
      >
          {isLocked ? 
          <NearMeIcon sx={{ fontSize: 20, transform: 'scaleX(-1)' }} /> : 
          <NearMeOutlinedIcon sx={{ fontSize: 20, transform: 'scaleX(-1)' }} />
        }
      </IconButton>

      <IconButton
        onClick={onUndoClick}
        disabled={undoDisabled}
          onMouseEnter={() => handleMouseEnter('undo', 'Undo (Ctrl + Z)')}
          onMouseLeave={handleMouseLeave}
        sx={{
          color: undoDisabled ? 'text.disabled' : "text.primary",
          "&:hover": { bgcolor: undoDisabled ? "transparent" : 'action.hover' },
          width: 40,
          height: 40,
          cursor: undoDisabled ? "not-allowed" : "pointer",
        }}
      >
        <UndoIcon sx={{ fontSize: 20 }} />
      </IconButton>

      <IconButton
        onClick={onRedoClick}
        disabled={redoDisabled}
          onMouseEnter={() => handleMouseEnter('redo', 'Redo (Ctrl + Shift + Z)')}
          onMouseLeave={handleMouseLeave}
        sx={{
          color: redoDisabled ? 'text.disabled' : "text.primary",
          "&:hover": { bgcolor: redoDisabled ? "transparent" : 'action.hover' },
          width: 40,
          height: 40,
          cursor: redoDisabled ? "not-allowed" : "pointer",
        }}
      >
        <RedoIcon sx={{ fontSize: 20 }} />
      </IconButton>
    </Box>
    </>
  );
};

export default BottomToolbar;
