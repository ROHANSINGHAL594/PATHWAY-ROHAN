import { useState, useContext, useEffect } from "react";
import {
  AppBar,
  Toolbar,
  Box,
  IconButton,
  Typography,
  Button,
  Menu,
  MenuItem,
  CircularProgress,
  Tooltip,
  Avatar,
  Badge,
  ListItemIcon,
  ListItemText,
  Divider,
  Switch,
  styled,
} from "@mui/material";
import {
  ArrowBack as ArrowBackIcon,
  Share as ShareIcon,
  Fullscreen as FullscreenIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
  Logout as LogoutIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";
import { useTheme, useColorScheme } from "@mui/material/styles";
import { AuthContext } from "../../context/AuthContext";
import ShareDialog from "./ShareDialog";

const StyledBadge = styled(Badge)(({ theme }) => ({
  "& .MuiBadge-badge": {
    backgroundColor: "#44b700",
    color: "#44b700",
    boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
    "&::after": {
      position: "absolute",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      borderRadius: "50%",
      animation: "ripple 1.2s infinite ease-in-out",
      border: "1px solid currentColor",
      content: '""',
    },
  },
  "@keyframes ripple": {
    "0%": {
      transform: "scale(.8)",
      opacity: 1,
    },
    "100%": {
      transform: "scale(2.4)",
      opacity: 0,
    },
  },
}));

const PipelineNavBar = ({
  onBackClick,
  pipelineName = "Pipeline A",
  loading,
  shareAnchorEl,
  onShareClick,
  onShareClose,
  onSave,
  onSpinup,
  onSpindown,
  onToggleStatus,
  currentPipelineStatus,
  currentPipelineId,
  containerId,
  onFullscreenClick,
  onFitScreenClick,
  onRunBook,
  userAvatar,
  onExportJSON,
  pipelineId,
  autoSaveStatus, // 'saving', 'saved', or null
}) => {
  const theme = useTheme();
  const { mode, setMode } = useColorScheme();
  const { logout: authLogout, user } = useContext(AuthContext);
  const [avatarAnchorEl, setAvatarAnchorEl] = useState(null);
  const avatarOpen = Boolean(avatarAnchorEl);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(false);

  // Generate avatar URL from the service
  const getAvatarUrl = () => {
    // Always use avatar service with a unique identifier (user ID or name)
    const identifier = user?.id || user?.name || userAvatar || "default";
    return `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
      identifier
    )}&size=32`;
  };

  // Fetch current user details when menu opens
  useEffect(() => {
    if (avatarOpen && !currentUser && !loadingUser) {
      const fetchUser = async () => {
        setLoadingUser(true);
        try {
          const response = await fetch(
            `${import.meta.env.VITE_API_SERVER}/auth/me`,
            { credentials: "include" }
          );
          if (response.ok) {
            const userData = await response.json();
            setCurrentUser(userData);
          }
        } catch (error) {
          console.error("Error fetching user details:", error);
        } finally {
          setLoadingUser(false);
        }
      };
      fetchUser();
    }
  }, [avatarOpen, currentUser, loadingUser]);

  const handleAvatarClick = (event) => {
    setAvatarAnchorEl(event.currentTarget);
  };

  const handleAvatarClose = () => {
    setAvatarAnchorEl(null);
  };

  const handleThemeToggle = () => {
    setMode(mode === "dark" ? "light" : "dark");
  };

  const handleLogout = () => {
    handleAvatarClose();
    if (authLogout) {
      authLogout();
    }
  };

  return (
    <AppBar
      position="static"
      color="inherit"
      elevation={0}
      sx={{
        borderBottom: "1px solid",
        padding: { xs: "8px 0", md: "8px 0" },
        borderColor: "divider",
        bgcolor: "background.elevation1",
        zIndex: 10,
        position: "relative",
      }}
    >
      <Toolbar
        sx={{
          display: "flex",
          height: "48px",
          justifyContent: "space-between",
          px: 3,
          minHeight: "48px !important",
        }}
      >
        {/* Left Section - Logo and Pipeline Name */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton
            onClick={onBackClick}
            sx={{
              color: "text.primary",
              "&:hover": { bgcolor: "action.hover" },
              padding: "6px",
            }}
          >
            <ArrowBackIcon sx={{ fontSize: 20 }} />
          </IconButton>

          <Typography
            variant="body1"
            sx={{
              color: "text.primary",
              fontWeight: 700,
              fontSize: "0.875rem",
              ml: 1,
            }}
          >
            {pipelineName}
          </Typography>

          {/* Auto-save Status Indicator */}
          {autoSaveStatus && (
            <Typography
              variant="caption"
              sx={{
                color: autoSaveStatus === 'saving' ? 'text.secondary' : 'success.main',
                fontSize: '0.7rem',
                ml: 1,
                fontStyle: 'italic',
              }}
            >
              {autoSaveStatus === 'saving' ? 'Saving...' : 'Saved'}
            </Typography>
          )}
        </Box>

        {/* Right Section - Action Buttons */}
        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            alignItems: "center",
          }}
        >
          {loading && <CircularProgress size={18} />}

          {/* Fullscreen Button */}
          {onFullscreenClick && (
            <Tooltip title="Fullscreen (Press F)" arrow>
              <IconButton
                onClick={onFullscreenClick}
                sx={{
                  bgcolor: "background.elevation1",
                  color: "text.primary",
                  "&:hover": { bgcolor: "action.hover" },
                  width: 32,
                  height: 32,
                  borderRadius: "6px",
                }}
              >
                <FullscreenIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          )}

          {/* Share Button with Dropdown */}
          <Button
            variant="contained"
            onClick={onShareClick}
            endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 16 }} />}
            sx={{
              bgcolor: "background.elevation1",
              color: "text.primary",
              textTransform: "none",
              fontWeight: 700,
              fontSize: "0.75rem",
              px: 2,
              py: 0.75,
              minHeight: "32px",
              borderRadius: "6px",
              boxShadow: "none",
              "&:hover": {
                bgcolor: "action.hover",
                boxShadow: "none",
              },
            }}
          >
            Share
          </Button>

          <Menu
            anchorEl={shareAnchorEl}
            open={Boolean(shareAnchorEl)}
            onClose={onShareClose}
            transformOrigin={{ horizontal: "right", vertical: "top" }}
            anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
            slotProps={{
              paper: {
                elevation: 3,
                sx: {
                  mt: 1,
                  minWidth: 180,
                  borderRadius: 2,
                  "& .MuiMenuItem-root": {
                    px: 2,
                    py: 1.5,
                    borderRadius: 1,
                    mx: 1,
                    my: 0.5,
                  },
                },
              },
            }}
          >
            <MenuItem
              onClick={() => {
                setShareDialogOpen(true);
                onShareClose();
              }}
            >
              Share Link
            </MenuItem>
            <MenuItem
              onClick={() => {
                if (onExportJSON) {
                  onExportJSON();
                }
                onShareClose();
              }}
            >
              Export as JSON
            </MenuItem>
          </Menu>

          {/* Share Dialog */}
          <ShareDialog
            open={shareDialogOpen}
            onClose={() => setShareDialogOpen(false)}
            pipelineLink={`${window.location.origin}/workflows/${
              pipelineId || currentPipelineId || "a"
            }`}
            pipelineName={pipelineName}
          />

          {/* Commit Version Button */}
          <Button
            variant="contained"
            onClick={onSave}
            disabled={loading}
            sx={{
              bgcolor: "background.elevation1",
              color: "text.primary",
              textTransform: "none",
              fontWeight: 700,
              fontSize: "0.75rem",
              px: 2,
              py: 0.75,
              minHeight: "32px",
              borderRadius: "6px",
              boxShadow: "none",
              "&:hover": {
                bgcolor: "action.hover",
                boxShadow: "none",
              },
              "&.Mui-disabled": {
                bgcolor: "action.disabledBackground",
                color: "text.disabled",
              },
            }}
          >
            Commit Version
          </Button>

          {/* Activate Button */}
          <Button
            variant="contained"
            onClick={onSpinup}
            disabled={loading || !currentPipelineId || !!containerId}
            sx={{
              bgcolor: "background.elevation1",
              color: "text.primary",
              textTransform: "none",
              fontWeight: 700,
              fontSize: "0.75rem",
              px: 2,
              py: 0.75,
              minHeight: "32px",
              borderRadius: "6px",
              boxShadow: "none",
              "&:hover": {
                bgcolor: "action.hover",
                boxShadow: "none",
              },
              "&.Mui-disabled": {
                bgcolor: "action.disabledBackground",
                color: "text.disabled",
              },
            }}
          >
            Activate
          </Button>

          {/* Deactivate Button */}
          <Button
            variant="contained"
            onClick={onSpindown}
            disabled={loading || !currentPipelineId || !containerId}
            sx={{
              bgcolor: "background.elevation1",
              color: "text.primary",
              textTransform: "none",
              fontWeight: 700,
              fontSize: "0.75rem",
              px: 2,
              py: 0.75,
              minHeight: "32px",
              borderRadius: "6px",
              boxShadow: "none",
              "&:hover": {
                bgcolor: "action.hover",
                boxShadow: "none",
              },
              "&.Mui-disabled": {
                bgcolor: "action.disabledBackground",
                color: "text.disabled",
              },
            }}
          >
            Deactivate
          </Button>

          {/* Run/Stop Button */}
          <Tooltip
            title={
              currentPipelineStatus === "Broken" ? "Pipeline is broken" : ""
            }
          >
            <span>
              <Button
                variant="contained"
                onClick={onToggleStatus}
                disabled={
                  loading ||
                  !currentPipelineId ||
                  !containerId ||
                  currentPipelineStatus === "Broken"
                }
                startIcon={
                  currentPipelineStatus === "Broken" ? (
                    <ErrorIcon color="error" />
                  ) : null
                }
                sx={{
                  bgcolor:
                    currentPipelineStatus === "Broken"
                      ? "error.light"
                      : "background.elevation1",
                  color:
                    currentPipelineStatus === "Broken"
                      ? "error.contrastText"
                      : "text.primary",
                  textTransform: "none",
                  fontWeight: 700,
                  fontSize: "0.75rem",
                  px: 2,
                  py: 0.75,
                  minHeight: "32px",
                  borderRadius: "6px",
                  boxShadow: "none",
                  "&:hover": {
                    bgcolor:
                      currentPipelineStatus === "Broken"
                        ? "error.main"
                        : "action.hover",
                    boxShadow: "none",
                  },
                  "&.Mui-disabled": {
                    bgcolor:
                      currentPipelineStatus === "Broken"
                        ? "error.light"
                        : "action.disabledBackground",
                    color:
                      currentPipelineStatus === "Broken"
                        ? "error.contrastText"
                        : "text.disabled",
                  },
                }}
              >
                {currentPipelineStatus === "Broken"
                  ? "Broken"
                  : currentPipelineStatus === "Running"
                  ? "Stop"
                  : "Run"}
              </Button>
            </span>
          </Tooltip>

          {/* Run Book Button - only enabled when container is active */}
          {onRunBook && (
            <Tooltip
              title={!containerId ? "Spin up the container first to access Run Book" : ""}
              arrow
              placement="bottom"
            >
              <span>
                <Button
                  variant="contained"
                  onClick={onRunBook}
                  disabled={!containerId}
                  sx={{
                    bgcolor: "background.elevation1",
                    color: "text.primary",
                    textTransform: "none",
                    fontWeight: 700,
                    fontSize: "0.75rem",
                    px: 2,
                    py: 0.75,
                    minHeight: "32px",
                    borderRadius: "6px",
                    boxShadow: "none",
                    "&:hover": {
                      bgcolor: "action.hover",
                      boxShadow: "none",
                    },
                    "&.Mui-disabled": {
                      bgcolor: "action.disabledBackground",
                      color: "text.disabled",
                    },
                  }}
                >
                  Run Book
                </Button>
              </span>
            </Tooltip>
          )}

          {/* Avatar with Dropdown */}
          <StyledBadge
            overlap="circular"
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            variant="dot"
          >
            <Avatar
              src={getAvatarUrl()}
              alt={user?.name || "User"}
              onClick={handleAvatarClick}
              sx={{
                width: 28,
                height: 28,
                bgcolor: "primary.main",
                cursor: "pointer",
                fontSize: "0.75rem",
                transition: "transform 0.2s ease, box-shadow 0.2s ease",
                "&:hover": {
                  transform: "scale(1.05)",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                },
              }}
              aria-controls={avatarOpen ? "avatar-menu" : undefined}
              aria-haspopup="true"
              aria-expanded={avatarOpen ? "true" : undefined}
            >
              {!userAvatar &&
                !user?.avatar &&
                !user?.id &&
                !user?.name &&
                (user?.name?.[0]?.toUpperCase() || "U")}
            </Avatar>
          </StyledBadge>

          <Menu
            id="avatar-menu"
            anchorEl={avatarAnchorEl}
            open={avatarOpen}
            onClose={handleAvatarClose}
            transformOrigin={{ horizontal: "right", vertical: "top" }}
            anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
            slotProps={{
              paper: {
                elevation: 3,
                sx: {
                  mt: 1,
                  minWidth: 180,
                  borderRadius: 2,
                  "& .MuiMenuItem-root": {
                    px: 2,
                    py: 1.5,
                    borderRadius: 1,
                    mx: 1,
                    my: 0.5,
                  },
                },
              },
            }}
          >
            {/* User Info Section */}
            <Box
              sx={{
                px: 2,
                py: 2,
                mx: 1,
                my: 0.5,
                borderRadius: 1,
                bgcolor: "action.hover",
              }}
            >
              {loadingUser ? (
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  Loading...
                </Typography>
              ) : currentUser ? (
                <Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: "text.primary",
                      mb: 0.5,
                    }}
                  >
                    {currentUser.full_name || "User"}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: "0.75rem",
                    }}
                  >
                    {currentUser.email || ""}
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: "text.primary",
                      mb: 0.5,
                    }}
                  >
                    {user?.name || user?.full_name || "User"}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: "0.75rem",
                    }}
                  >
                    {user?.email || ""}
                  </Typography>
                </Box>
              )}
            </Box>
            <Divider sx={{ my: 0.5 }} />

            {/* Dark Mode Toggle */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                px: 2,
                py: 1.5,
                mx: 1,
                my: 0.5,
                borderRadius: 1,
                minWidth: 200,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                {mode === "dark" ? (
                  <DarkModeIcon
                    fontSize="small"
                    sx={{ color: "text.secondary" }}
                  />
                ) : (
                  <LightModeIcon
                    fontSize="small"
                    sx={{ color: "text.secondary" }}
                  />
                )}
                <Typography variant="body2" sx={{ color: "text.primary" }}>
                  Dark Mode
                </Typography>
              </Box>
              <Switch
                checked={mode === "dark"}
                onChange={handleThemeToggle}
                size="small"
                sx={{
                  ml: 3,
                  "& .MuiSwitch-switchBase.Mui-checked": {
                    color: "primary.main",
                  },
                  "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                    backgroundColor: "primary.main",
                  },
                }}
              />
            </Box>
            <Divider sx={{ my: 0.5 }} />
            <MenuItem onClick={handleLogout} sx={{ color: "error.main" }}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" sx={{ color: "error.main" }} />
              </ListItemIcon>
              <ListItemText>Logout</ListItemText>
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default PipelineNavBar;
