import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const KPICard = ({ title, value, subtitle, icon: Icon, iconColor }) => {
  return (
    <Paper
      sx={{
        p: '1.5rem',
        borderRadius: 0,
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: 'none',
        boxShadow: 'none',
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '9.375rem',
        bgcolor: 'background.paper',
      }}
    >
      <Box 
        sx={{ 
          textAlign: 'left', 
          width: '100%', 
          maxWidth: '12rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}
      >
        <Typography 
          variant="body2" 
          color="text.primary" 
          fontWeight="600"
          sx={{ 
            fontSize: '1rem',
            lineHeight: 1.3,
            minHeight: 'auto',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {title}
        </Typography>
        {Icon && (
          <Icon sx={{ fontSize: '3rem', color: iconColor || 'text.secondary' }} />
        )}
        <Typography variant="h4" fontWeight="400" sx={{ fontSize: { xs: '2rem', md: '2.5rem' }, lineHeight: 1 }}>
          {value}
        </Typography>
        <Typography 
          variant="caption" 
          color="text.secondary"
          sx={{
            fontSize: '0.8rem',
            display: '-webkit-box',
            WebkitLineClamp: 1,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {subtitle}
        </Typography>
      </Box>
    </Paper>
  );
};

export default KPICard;

