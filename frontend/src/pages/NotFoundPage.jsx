import React from 'react';
import { Box, Button, Typography, useTheme } from '@mui/material';
import { useColorScheme } from '@mui/material/styles';
import { Link } from 'react-router-dom';
import notfounddark from '../assets/404dark.svg';
import notfoundlight from '../assets/404light.svg';

const NotFoundPage = () => {
  const theme = useTheme();
  const { mode, systemMode } = useColorScheme();
  const resolvedMode = (mode === 'system' ? systemMode : mode) || theme.palette.mode;
  const isDark = resolvedMode === 'dark';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        textAlign: 'center',
        bgcolor: 'background.default',
        gap: 2,
      }}
    >
      <Box
        component="img"
        src={isDark ? notfounddark : notfoundlight}
        alt="404 Not Found"
        sx={{
          maxWidth: { xs: '80%', sm: '60%', md: '500px' },
          height: 'auto',
          mb: 2,
        }}
      />
      
      <Typography variant="h5" component="h2" sx={{ color: 'text.primary', fontWeight: 600 }}>
        Page Not Found
      </Typography>
      <Typography variant="body1" sx={{ color: 'text.secondary', maxWidth: '500px', px: 2 }}>
        The page you are looking for does not exist.
      </Typography>
      <Button
        component={Link}
        to="/overview"
        variant="contained"
        sx={{ mt: 2 }}
      >
        Go to Homepage
      </Button>
    </Box>
  );
};

export default NotFoundPage;
