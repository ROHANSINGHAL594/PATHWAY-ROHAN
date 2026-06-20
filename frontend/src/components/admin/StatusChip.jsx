import { Chip } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningIcon from "@mui/icons-material/Warning";

export function StatusChip({ status }) {
  const isDone = status === "Done";
  const isActive = status === "Active";
  const isSuccess = isDone || isActive;

  const getChipProps = () => {
    if (isSuccess) {
      return {
        color: 'success',
        variant: 'soft',
        icon: <CheckCircleIcon sx={{ fontSize: '0.875rem' }} />,
      };
    } else if (status === "Overdue" || status === "Suspended") {
      return {
        color: 'warning',
        variant: 'soft',
        icon: <WarningIcon sx={{ fontSize: '0.875rem' }} />,
      };
    } else {
      return {
        color: 'warning',
        variant: 'soft',
        icon: <WarningIcon sx={{ fontSize: '0.875rem' }} />,
      };
    }
  };

  return (
    <Chip
      label={status}
      size="small"
      {...getChipProps()}
      sx={{
        fontSize: '0.75rem',
        fontWeight: 500,
        height: 'auto',
        py: 0.5,
      }}
    />
  );
}

