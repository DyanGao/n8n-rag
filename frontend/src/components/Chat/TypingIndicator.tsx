import React from 'react';
import { Box, Avatar, Paper, Typography } from '@mui/material';
import { SmartToy as BotIcon } from '@mui/icons-material';

const TypingIndicator: React.FC = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1,
        mb: 2,
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      {/* Avatar */}
      <Avatar
        sx={{
          width: 36,
          height: 36,
          backgroundColor: 'secondary.main',
          flexShrink: 0,
        }}
      >
        <BotIcon />
      </Avatar>

      {/* Typing Bubble */}
      <Paper
        elevation={1}
        sx={{
          p: 2,
          backgroundColor: 'background.paper',
          borderRadius: 2,
          minWidth: 80,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box className="typing-indicator">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </Box>
          
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            AI is thinking...
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default TypingIndicator;