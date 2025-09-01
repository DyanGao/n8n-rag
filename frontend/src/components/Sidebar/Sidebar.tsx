import React, { useState } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Button,
  Chip,
  Tooltip,
  IconButton,
  TextField,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Folder as FolderIcon,
  Code as WorkflowIcon,
  Add as AddIcon,
  History as HistoryIcon,
  CloudCircle as CloudIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Close as CancelIcon,
} from '@mui/icons-material';

import { useChat } from '../../contexts/ChatContext';

interface SidebarProps {
  activeView: 'chat' | 'documents' | 'workflow';
  onViewChange: (view: 'chat' | 'documents' | 'workflow') => void;
  isConnected: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange, isConnected }) => {
  const { state, createNewSession, setActiveSession, deleteSession, updateSessionTitle } = useChat();
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const menuItems = [
    {
      id: 'chat',
      label: 'Chat',
      icon: <ChatIcon />,
      view: 'chat' as const,
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: <FolderIcon />,
      view: 'documents' as const,
    },
    {
      id: 'workflow',
      label: 'Workflow Preview',
      icon: <WorkflowIcon />,
      view: 'workflow' as const,
    },
  ];

  const handleNewChat = () => {
    const sessionId = createNewSession();
    onViewChange('chat');
  };

  const handleSessionSelect = (sessionId: string) => {
    setActiveSession(sessionId);
    // If the session has a workflow and user is in workflow view, stay in workflow view
    const session = state.sessions.find(s => s.id === sessionId);
    if (session?.currentWorkflow && activeView === 'workflow') {
      // Stay in workflow view
      return;
    }
    onViewChange('chat');
  };

  const handleDeleteSession = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent session selection
    deleteSession(sessionId);
  };

  const handleEditSession = (sessionId: string, currentTitle: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent session selection
    setEditingSessionId(sessionId);
    setEditTitle(currentTitle);
  };

  const handleSaveEdit = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (editTitle.trim()) {
      updateSessionTitle(sessionId, editTitle.trim());
    }
    setEditingSessionId(null);
    setEditTitle('');
  };

  const handleCancelEdit = (event: React.MouseEvent) => {
    event.stopPropagation();
    setEditingSessionId(null);
    setEditTitle('');
  };

  const handleTitleKeyPress = (event: React.KeyboardEvent, sessionId: string) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSaveEdit(sessionId, event as any);
    } else if (event.key === 'Escape') {
      handleCancelEdit(event as any);
    }
  };

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'background.paper',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid', borderBottomColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="h6" className="gradient-text">
            RAG Studio
          </Typography>
          <Chip
            icon={<CloudIcon />}
            label={isConnected ? 'Online' : 'Offline'}
            size="small"
            color={isConnected ? 'success' : 'error'}
            variant="outlined"
          />
        </Box>
        
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleNewChat}
          sx={{
            background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
            color: 'white',
            '&:hover': {
              background: 'linear-gradient(135deg, #e55353 0%, #26a69a 100%)',
            },
          }}
        >
          New Chat
        </Button>
      </Box>

      {/* Navigation Menu */}
      <Box sx={{ px: 1, py: 2 }}>
        <List dense>
          {menuItems.map((item) => (
            <ListItem key={item.id} disablePadding>
              <ListItemButton
                selected={activeView === item.view}
                onClick={() => onViewChange(item.view)}
                sx={{
                  borderRadius: 1,
                  mb: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 107, 107, 0.15)',
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>

      <Divider />

      {/* Chat Sessions */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Recent Chats
          </Typography>
        </Box>
        
        <Box sx={{ px: 1, maxHeight: '300px', overflowY: 'auto' }}>
          <List dense>
            {state.sessions.slice(0, 10).map((session) => (
              <ListItem key={session.id} disablePadding>
                <ListItemButton
                  selected={state.activeSessionId === session.id}
                  onClick={() => handleSessionSelect(session.id)}
                  sx={{
                    borderRadius: 1,
                    mb: 0.5,
                    pr: 1,
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(78, 205, 196, 0.1)',
                      '&:hover': {
                        backgroundColor: 'rgba(78, 205, 196, 0.15)',
                      },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <HistoryIcon fontSize="small" />
                  </ListItemIcon>
                  {editingSessionId === session.id ? (
                    <TextField
                      size="small"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => handleTitleKeyPress(e, session.id)}
                      onClick={(e) => e.stopPropagation()}
                      sx={{
                        flex: 1,
                        '& .MuiInputBase-input': {
                          fontSize: '0.875rem',
                        },
                      }}
                      autoFocus
                    />
                  ) : (
                    <ListItemText
                      primary={
                        <Tooltip title={session.title}>
                          <Typography
                            variant="body2"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '120px',
                            }}
                          >
                            {session.title}
                          </Typography>
                        </Tooltip>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {session.messages.length} messages
                        </Typography>
                      }
                    />
                  )}

                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {editingSessionId === session.id ? (
                      <>
                        <Tooltip title="Save">
                          <IconButton
                            size="small"
                            onClick={(e) => handleSaveEdit(session.id, e)}
                            sx={{
                              opacity: 0.6,
                              '&:hover': {
                                opacity: 1,
                                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                              },
                            }}
                          >
                            <CheckIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Cancel">
                          <IconButton
                            size="small"
                            onClick={handleCancelEdit}
                            sx={{
                              opacity: 0.6,
                              '&:hover': {
                                opacity: 1,
                                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                              },
                            }}
                          >
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    ) : (
                      <>
                        <Tooltip title="Edit chat name">
                          <IconButton
                            size="small"
                            onClick={(e) => handleEditSession(session.id, session.title, e)}
                            sx={{
                              opacity: 0.6,
                              '&:hover': {
                                opacity: 1,
                                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                              },
                            }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete chat">
                          <IconButton
                            size="small"
                            onClick={(e) => handleDeleteSession(session.id, e)}
                            sx={{
                              opacity: 0.6,
                              '&:hover': {
                                opacity: 1,
                                backgroundColor: 'rgba(255, 107, 107, 0.1)',
                              },
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </Box>
                </ListItemButton>
              </ListItem>
            ))}
            {state.sessions.length === 0 && (
              <ListItem>
                <ListItemText
                  primary={
                    <Typography variant="body2" color="text.secondary" textAlign="center">
                      No recent chats
                    </Typography>
                  }
                />
              </ListItem>
            )}
          </List>
        </Box>
      </Box>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: '1px solid', borderTopColor: 'divider' }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', textAlign: 'center' }}
        >
          n8n RAG Studio v1.0
        </Typography>
      </Box>
    </Box>
  );
};

export default Sidebar;