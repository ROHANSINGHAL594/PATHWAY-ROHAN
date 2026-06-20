import React from "react";
import { Box } from "@mui/material";
import Logo from "../../assets/logo.svg";
import "../../css/loading.css";

const Loading = () => {
  return (
    <Box
      sx={(theme) => ({
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        width: "100%",
        backgroundColor: theme.vars.palette.background.default,
      })}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
        }}
      >
        <Box
          component="img"
          src={Logo}
          alt="Laminar Logo"
          sx={{ width: "5rem", height: "auto" }}
        />
        <Box
          sx={(theme) => ({
            width: "12rem",
            height: "0.25rem",
            backgroundColor: theme.vars.palette.grey[300],
            borderRadius: "0.125rem",
            overflow: "hidden",
            position: "relative",
          })}
        >
          <Box
            className="loading-bar-indicator"
            sx={(theme) => ({
              width: "4rem",
              height: "100%",
              backgroundColor: theme.vars.palette.primary.dark,
              borderRadius: "0.125rem",
              position: "absolute",
            })}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default Loading;

