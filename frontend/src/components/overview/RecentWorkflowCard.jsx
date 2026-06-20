import React, { useState } from "react";
import {
  Box,
  Typography,
  Avatar,
  AvatarGroup,
  Chip,
  IconButton,
  useTheme,
} from "@mui/material";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
dayjs.extend(relativeTime);

const RecentWorkflowCard = ({ workflow, onClick, selected }) => {
  const theme = useTheme();
  const [isPressed, setIsPressed] = useState(false);

  // Use theme colors for status
  const statusColors = {
    Running: theme.palette.success.main,
    Stopped: theme.palette.warning.main,
    Broken: theme.palette.error.main,
  };

  // Generate avatars from workflow owners/team
  const generateAvatars = () => {
    const team = workflow.team || workflow.owners || [];
    return team.map((member, index) => {
      const identifier =
        member.name || member.display_name || member.id || `User${index}`;
      const initials =
        member.initials ||
        (member.display_name
          ? member.display_name
              .split(" ")
              .map((x) => x[0].toUpperCase())
              .slice(0, 2)
              .join("")
          : String.fromCharCode(65 + index));
      const avatarUrl = `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
        identifier
      )}&size=32`;

      return {
        id: member.id || index,
        name: member.name || member.display_name || `User${index}`,
        initials: initials,
        avatarUrl: avatarUrl,
      };
    });
  };

  const avatars = generateAvatars();

  const handleMouseDown = () => {
    setIsPressed(true);
  };

  const handleMouseUp = () => {
    setIsPressed(false);
  };

  const handleClick = (e) => {
    setIsPressed(false);
    if (onClick) onClick(e);
  };

  const isActive = selected || isPressed;

  return (
    <Box
      sx={{
        p: "1.5rem",
        borderRadius: "0.75rem",
        bgcolor: isActive ? "action.selected" : "background.elevation1",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        cursor: "pointer",
        transition: "background-color 0.2s ease",
        "&:hover": {
          bgcolor: isActive ? "action.selected" : "action.hover",
        },
        "&:active": {
          bgcolor: "action.selected",
        },
      }}
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <Box sx={{ flex: 1 }}>
        <Typography
          variant="body1"
          fontWeight="600"
          sx={{ mb: 0.5, fontSize: "1rem" }}
        >
          {workflow.name}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: "0.875rem" }}
        >
          Last Updated:{" "}
          {workflow.user_pipeline_version?.version_updated_at
            ? dayjs(workflow.user_pipeline_version.version_updated_at).fromNow()
            : "N/A"}
        </Typography>
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <AvatarGroup
          max={4}
          sx={{
            "& .MuiAvatar-root": {
              width: "1.75rem",
              height: "1.75rem",
              fontSize: "0.75rem",
            },
          }}
        >
          {avatars.map((avatar) => {
            const avatarUrl = `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
              avatar.id
            )}&size=32`;
            return (
              <Avatar
                key={avatar.id}
                src={avatarUrl}
                alt={avatar.name}
                sx={{ width: "1.75rem", height: "1.75rem" }}
              >
                {String.fromCharCode(65 + avatar.id)}
              </Avatar>
            );
          })}
        </AvatarGroup>

        <Chip
          label={workflow.status || "Stopped"}
          color={
            workflow.status === "Running"
              ? "success"
              : workflow.status === "Stopped"
              ? "warning"
              : "error"
          }
          variant="soft"
          size="small"
        />

        <IconButton
          size="small"
          variant="soft"
          sx={{
            width: "1.5rem",
            height: "1.5rem",
            borderRadius: "0.375rem",
            "&:hover": {
              bgcolor: "action.hover",
            },
          }}
        >
          <MoreHorizIcon sx={{ fontSize: "1rem", color: "text.secondary" }} />
        </IconButton>
      </Box>
    </Box>
  );
};

export default RecentWorkflowCard;
