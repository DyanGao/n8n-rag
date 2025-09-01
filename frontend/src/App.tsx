import React, { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Close as CloseIcon,
  Brightness4,
  Brightness7,
} from '@mui/icons-material';

// Components
import Sidebar from './components/Sidebar/Sidebar';
import ChatInterface from './components/Chat/ChatInterface';
import DocumentManager from './components/Documents/DocumentManager';
import WorkflowPreview from './components/Workflow/WorkflowPreview';

// Hooks and Utils
import { useWebSocket } from './hooks/useWebSocket';
import { ChatProvider, useChat } from './contexts/ChatContext';
import { DocumentProvider } from './contexts/DocumentContext';

const DRAWER_WIDTH = 280;

type ActiveView = 'chat' | 'documents' | 'workflow';

// Inner component that uses ChatContext
function AppContent() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { getActiveSession, updateSessionWorkflow } = useChat();
  
  // State
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [activeView, setActiveView] = useState<ActiveView>('chat');
  
  // WebSocket connection - only for status display
  const { isConnected, sendMessage } = useWebSocket({ 
    autoConnect: true // Enable only for main app status
  });

  // Get current workflow from active session
  const activeSession = getActiveSession();
  const currentWorkflow = activeSession?.currentWorkflow || null;

  // If in workflow view but no workflow, switch to chat
  useEffect(() => {
    if (activeView === 'workflow' && !currentWorkflow) {
      setActiveView('chat');
    }
  }, [activeView, currentWorkflow]);

  useEffect(() => {
    // Close sidebar on mobile by default
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  const handleDrawerToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const handleViewChange = (view: ActiveView) => {
    setActiveView(view);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleWorkflowGenerated = (workflow: any) => {
    if (activeSession) {
      updateSessionWorkflow(activeSession.id, workflow);
    }
    setActiveView('workflow');
  };

  const renderActiveView = () => {
    switch (activeView) {
      case 'chat':
        return (
          <ChatInterface 
            onWorkflowGenerated={handleWorkflowGenerated}
            isConnected={isConnected}
          />
        );
      case 'documents':
        return <DocumentManager />;
      case 'workflow':
        return (
          <WorkflowPreview 
            workflow={currentWorkflow}
            onBack={() => setActiveView('chat')}
          />
        );
      default:
        return (
          <ChatInterface 
            onWorkflowGenerated={handleWorkflowGenerated}
            isConnected={isConnected}
          />
        );
    }
  };

  const drawer = (
    <Sidebar
      activeView={activeView}
      onViewChange={handleViewChange}
      isConnected={isConnected}
    />
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
          {/* App Bar */}
          <AppBar
            position="fixed"
            sx={{
              width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%' },
              ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
              zIndex: theme.zIndex.drawer + 1,
              backgroundColor: 'background.paper',
              borderBottom: '1px solid',
              borderBottomColor: 'divider',
              boxShadow: 'none',
            }}
          >
            <Toolbar>
              <IconButton
                color="inherit"
                aria-label="open drawer"
                onClick={handleDrawerToggle}
                edge="start"
                sx={{ mr: 2 }}
              >
                {sidebarOpen ? <CloseIcon /> : <MenuIcon />}
              </IconButton>
              
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                <span className="gradient-text">n8n RAG Studio</span>
              </Typography>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {/* Connection status indicator */}
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: isConnected ? 'success.main' : 'error.main',
                    mr: 1,
                  }}
                />
                <Typography variant="caption" color="text.secondary">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </Typography>
              </Box>
            </Toolbar>
          </AppBar>

          {/* Mobile Drawer */}
          <Box
            component="nav"
            sx={{ width: { md: sidebarOpen ? DRAWER_WIDTH : 0 }, flexShrink: { md: 0 } }}
          >
            {isMobile ? (
              <Drawer
                variant="temporary"
                open={sidebarOpen}
                onClose={handleDrawerToggle}
                ModalProps={{
                  keepMounted: true,
                }}
                sx={{
                  display: { xs: 'block', md: 'none' },
                  '& .MuiDrawer-paper': {
                    boxSizing: 'border-box',
                    width: DRAWER_WIDTH,
                  },
                }}
              >
                {drawer}
              </Drawer>
            ) : (
              <Drawer
                variant="persistent"
                sx={{
                  display: { xs: 'none', md: 'block' },
                  '& .MuiDrawer-paper': {
                    boxSizing: 'border-box',
                    width: DRAWER_WIDTH,
                  },
                }}
                open={sidebarOpen}
              >
                {drawer}
              </Drawer>
            )}
          </Box>

          {/* Main Content */}
          <Box
            component="main"
            sx={{
              flexGrow: 1,
              height: '100vh',
              overflow: 'hidden',
              transition: theme.transitions.create(['margin', 'width'], {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.leavingScreen,
              }),
            }}
          >
            <Toolbar /> {/* Spacer for fixed AppBar */}
            <Box
              sx={{
                height: 'calc(100vh - 64px)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {renderActiveView()}
            </Box>
          </Box>
    </Box>
  );
}

// Main App component that provides contexts
function App() {
  return (
    <ChatProvider>
      <DocumentProvider>
        <AppContent />
      </DocumentProvider>
    </ChatProvider>
  );
}

export default App;