import TimelineIcon from "@mui/icons-material/Timeline";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import SpeedIcon from "@mui/icons-material/Speed";

const iconMap = {
  timeline: TimelineIcon,
  "access-time": AccessTimeIcon,
  "error-outline": ErrorOutlineIcon,
  speed: SpeedIcon,
};

export const getIconComponent = (iconType) => {
  return iconMap[iconType] || TimelineIcon;
};
