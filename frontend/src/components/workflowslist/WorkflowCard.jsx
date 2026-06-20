import { Card, CardContent, Box, Typography, AvatarGroup, Avatar, IconButton, Chip } from "@mui/material";
import { MoreHoriz as MoreHorizIcon } from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";

const WorkflowCard = ({ workflow, isSelected, onClick }) => {
  const theme = useTheme();

  // Generate avatar URL using the same service as WorkflowDetails
  const getAvatarUrl = (member, index) => {
    return `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(member.name || member.display_name || member.id || `user${index}`)}&size=24`;
  };

  return (
    <Card
      onClick={onClick}
      sx={{
        cursor: "pointer",
        borderRadius: '0.75rem',
        bgcolor: isSelected ? 'action.selected' : 'background.elevation1',
        boxShadow: "none",
        outline: "none",
        transition: 'background-color 0.2s ease',
        width: "100%",
        maxWidth: "492px",
        minHeight: "139px",
        "&:hover": {
          bgcolor: isSelected ? 'action.selected' : 'action.hover',
        },
        "&:active": {
          bgcolor: 'action.selected',
        },
      }}
    >
      <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, fontSize: "0.9375rem", mb: 0.5, color: "text.primary" }}>
              {workflow.name}
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.8125rem", mb: 1 }}>
              {workflow.category}
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.75rem", display: "block", mb: 2 }}>
              Last updated: {workflow.location || "N/A"}
            </Typography>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1 }}>
              <AvatarGroup max={5} sx={{ "& .MuiAvatar-root": { width: 24, height: 24, fontSize: "0.625rem", border: `2px solid ${theme.palette.background.paper}` } }}>
                {workflow.team.map((member, index) => {
                  const avatarUrl = getAvatarUrl(member, index);
                  return (
                    <Avatar 
                      key={member.id || index}
                      src={avatarUrl}
                      alt={member.name || member.display_name}
                      sx={{ 
                        width: 24, 
                        height: 24,
                      }}
                      title={member.name || member.display_name}
                    />
                  );
                })}
              </AvatarGroup>
              <Chip
                label={workflow.status}
                size="small"
                color={
                  workflow.status === "Running"
                    ? "success"
                    : workflow.status === "Broken"
                    ? "error"
                    : "info"
                }
                variant="soft"
                sx={{
                  fontWeight: 500,
                  fontSize: "0.6875rem",
                  height: "22px",
                  borderRadius: "12px",
                }}
              />
            </Box>
          </Box>
          <IconButton size="small" sx={{ color: "text.secondary", ml: 1 }}>
            <MoreHorizIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );
};

export default WorkflowCard;

