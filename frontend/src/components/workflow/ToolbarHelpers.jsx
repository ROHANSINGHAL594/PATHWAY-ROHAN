import { Box, Typography } from "@mui/material";
import BackspaceIcon from "@mui/icons-material/Backspace";
import LockOpenIcon from "@mui/icons-material/LockOpen";

const containerStyles = {
  position: "absolute",
  bottom: 56,
  left: "50%",
  transform: "translateX(-50%)",
  display: "flex",
  alignItems: "center",
  gap: 0.3,
  zIndex: 1000,
};

const textStyles = (theme) => ({
  fontSize: theme.typography.caption.fontSize,
  color: theme.vars.palette.text.primary,
  textShadow: `1px 1px 2px ${theme.vars.palette.background.paper}, -1px -1px 2px ${theme.vars.palette.background.paper}, 0 0 3px ${theme.vars.palette.background.paper}`,
  display: "flex",
  alignItems: "center",
  gap: 0.2,
  fontWeight: theme.typography.fontWeightMedium,
});

const iconStyles = {
  fontSize: 11,
};

export function LockMessageHelper() {
  return (
    <Box sx={containerStyles}>
      <Typography variant="caption" sx={textStyles}>
        Click <LockOpenIcon sx={iconStyles} /> to unlock and make changes
      </Typography>
    </Box>
  );
}

export function ToolbarButtonHelper({ hoveredButton }) {
  const messages = {
    add: "Add Node (Press A)",
    undo: "Undo (Ctrl + Z)",
    redo: "Redo (Ctrl + Shift + Z)",
  };

  const message = messages[hoveredButton];
  if (!message) return null;

  return (
    <Box sx={containerStyles}>
      <Typography variant="caption" sx={textStyles}>
        {message}
      </Typography>
    </Box>
  );
}

export function DeleteEdgeHelper() {
  return (
    <Box sx={containerStyles}>
      <Typography variant="caption" sx={textStyles}>
        Click <BackspaceIcon sx={iconStyles} /> to delete connection
      </Typography>
    </Box>
  );
}
