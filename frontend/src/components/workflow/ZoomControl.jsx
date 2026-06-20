import { Box, IconButton, TextField } from "@mui/material";
import { Add as AddIcon, Remove as RemoveIcon } from "@mui/icons-material";
import { useState, useEffect } from "react";
import { useTheme } from "@mui/material/styles";

const ZoomControl = ({ zoom = 100, onZoomIn, onZoomOut, onZoomChange, propertyBarOpen = false }) => {
  const theme = useTheme();
  const [editableZoom, setEditableZoom] = useState(Math.round(zoom / 10) * 10);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setEditableZoom(Math.round(zoom / 10) * 10);
    }
  }, [zoom, isEditing]);

  const handleZoomChange = (e) => {
    const value = e.target.value.replace(/[^0-9]/g, '').slice(0, 3);
    setEditableZoom(value);
  };

  const handleZoomSubmit = () => {
    const numValue = parseInt(editableZoom) || 100;
    const clampedValue = Math.max(10, Math.min(200, numValue));
    const roundedValue = Math.round(clampedValue / 10) * 10;
    setEditableZoom(roundedValue);
    if (onZoomChange) {
      onZoomChange(roundedValue);
    }
    setIsEditing(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleZoomSubmit();
    } else if (e.key === 'Escape') {
      setEditableZoom(Math.round(zoom / 10) * 10);
      setIsEditing(false);
    }
  };

  return (
    <Box
      sx={{
        position: "absolute",
        bottom: 52,
        right: propertyBarOpen ? "400px" : "24px",
        display: "flex",
        alignItems: "center",
        gap: 0,
        bgcolor: 'background.elevation1',
        border: "1px solid",
        borderColor: 'divider',
        borderRadius: "100px",
        padding: "0",
        height: "48px",
        boxShadow: theme.palette.mode === 'dark'
          ? '0px -2px 6px 0px rgba(0, 0, 0, 0.3), 2px 10px 10px 0px rgba(0, 0, 0, 0.2), 1px 20px 19px 0px rgba(0, 0, 0, 0.2), 6px 33px 46px 0px rgba(0, 0, 0, 0.3)'
          : '0px -2px 6px 0px rgba(0, 0, 0, 0.03), 2px 10px 10px 0px rgba(0, 0, 0, 0.01), 1px 20px 19px 0px rgba(0, 0, 0, 0.03), 6px 33px 46px 0px rgba(0, 0, 0, 0.07)',
        zIndex: 1000,
        transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <IconButton
        onClick={onZoomOut}
        sx={{
          color: "text.primary",
          "&:hover": { bgcolor: 'action.hover' },
          width: 40,
          height: 40,
        }}
      >
        <RemoveIcon sx={{ fontSize: 20 }} />
      </IconButton>

      <Box 
        sx={{ 
          minWidth: "60px", 
          textAlign: "center",
          px: 1,
        }}
      >
        <TextField
          value={isEditing ? editableZoom : `${editableZoom}%`}
          onChange={handleZoomChange}
          onFocus={() => {
            setIsEditing(true);
            setEditableZoom(String(Math.round(zoom / 10) * 10));
          }}
          onBlur={handleZoomSubmit}
          onKeyDown={handleKeyPress}
          variant="standard"
          InputProps={{
            disableUnderline: true,
            sx: {
              fontSize: "0.875rem",
              fontWeight: 500,
              textAlign: "center",
              bgcolor: theme.palette.mode === 'dark' 
                ? 'rgba(255, 255, 255, 0.1)' 
                : 'rgba(255, 255, 255, 0.3)',
              borderRadius: '4px',
              px: 0.5,
              py: 0.25,
              color: 'text.primary',
              '& input': {
                textAlign: 'center',
                padding: '2px 4px',
                cursor: 'pointer',
                color: 'text.primary',
              }
            }
          }}
          sx={{
            width: '50px',
            '& .MuiInput-input': {
              textAlign: 'center',
            }
          }}
        />
      </Box>

      <IconButton
        onClick={onZoomIn}
        sx={{
          color: "text.primary",
          "&:hover": { bgcolor: 'action.hover' },
          width: 40,
          height: 40,
        }}
      >
        <AddIcon sx={{ fontSize: 20 }} />
      </IconButton>
    </Box>
  );
};

export default ZoomControl;

