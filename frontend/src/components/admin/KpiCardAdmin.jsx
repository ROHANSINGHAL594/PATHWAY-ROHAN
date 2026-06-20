import { useState } from "react";
import { Typography, Box } from "@mui/material";

export function KpiCard({ title, value, description, icon: Icon, iconClass, cardClass, onClick, isSelected }) {
  const [isPressed, setIsPressed] = useState(false);

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

  const isActive = isSelected || isPressed;

  return (
    <Box
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      sx={{
        p: 2.5,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        borderRadius: '0.75rem',
        bgcolor: isActive ? 'action.selected' : 'background.elevation1',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background-color 0.2s ease',
        '&:hover': {
          bgcolor: isActive ? 'action.selected' : 'action.hover',
        },
        '&:active': {
          bgcolor: 'action.selected',
        },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <Typography
          variant="body2"
          sx={{
            fontSize: '0.9375rem',
            fontWeight: 500,
            color: 'text.primary',
          }}
        >
          {title}
        </Typography>
        <Box
          sx={{
            width: '2.5rem',
            height: '2.5rem',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'primary.lighter',
            color: 'primary.main',
          }}
        >
          <Icon sx={{ fontSize: "1.25rem" }} />
        </Box>
      </Box>
      <Typography
        variant="h3"
        sx={{
          fontSize: '2.25rem',
          fontWeight: 400,
          color: 'text.primary',
          lineHeight: 1.2,
          mt: 0.5,
        }}
      >
        {value}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontSize: '0.8125rem',
          color: 'text.secondary',
          mt: 0.25,
        }}
      >
        {description}
      </Typography>
    </Box>
  );
}

