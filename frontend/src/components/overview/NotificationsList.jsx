import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  Divider,
  Typography,
  Box,
} from '@mui/material';

const NotificationsList = ({ notifications }) => {
  if (!notifications || notifications.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">No new notifications.</Typography>
      </Box>
    );
  }

  return (
    <List sx={{ width: '100%', bgcolor: 'transparent' }}>
      {notifications.map((notification, index) => (
        <React.Fragment key={notification.id || notification._id || index}>
          <ListItem alignItems="flex-start">
            <ListItemText
              primary={notification.title || notification.message || "Notification"}
              secondary={
                <>
                  {notification.desc && (
                    <Typography
                      sx={{ display: 'block' }}
                      component="span"
                      variant="body2"
                      color="text.secondary"
                    >
                      {notification.desc}
                    </Typography>
                  )}
                  <Typography
                    sx={{ display: 'inline' }}
                    component="span"
                    variant="caption"
                    color="text.disabled"
                  >
                    {notification.timestamp}
                  </Typography>
                </>
              }
            />
          </ListItem>
          {index < notifications.length - 1 && <Divider variant="inset" component="li" />}
        </React.Fragment>
      ))}
    </List>
  );
};

export default NotificationsList;
