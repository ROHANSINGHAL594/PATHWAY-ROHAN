import React from "react";
import { useMediaQuery, Box, Typography } from "@mui/material";
import DesktopWindowsIcon from "@mui/icons-material/DesktopWindows";

const MobileViewBlocker = ({ children }) => {
  const isMobile = useMediaQuery((theme) => theme.breakpoints.down("sm"));

  if (isMobile) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          textAlign: "center",
          p: 3,
        }}
      >
        <DesktopWindowsIcon sx={{ fontSize: 80, mb: 3 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Desktop Experience Recommended
        </Typography>
        <Typography variant="body1">
          For the best experience, please use a desktop or laptop computer. This
          dashboard is not optimized for mobile devices.
        </Typography>
      </Box>
    );
  }

  return children;
};

export default MobileViewBlocker;
