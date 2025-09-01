import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Chip,
  Avatar,
  Button,
  LinearProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Download as DownloadIcon,
  ThumbUp,
  ThumbDown,
} from '@mui/icons-material';

import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { useChat } from '../../contexts/ChatContext';
import { useWebSocket } from '../../hooks/useWebSocket';

interface ChatInterfaceProps {
  onWorkflowGenerated?: (workflow: any) => void;
  isConnected?: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  onWorkflowGenerated, 
  isConnected = false 
}) => {
  const { state, createNewSession, addMessage, getActiveSession, updateSessionWorkflow } = useChat();
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const creatingSessionRef = useRef(false);
  const sessionCreationTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const { sendChatMessage, lastMessage } = useWebSocket({
    onMessage: handleWebSocketMessage,
    autoConnect: false, // Don't auto-connect, let App.tsx handle the main connection
  });

  const activeSession = getActiveSession();

  function handleWebSocketMessage(message: any) {
    if (!activeSession) return;

    switch (message.type) {
      case 'progress':
        // Show progress in UI
        setIsGenerating(true);
        break;
      
      case 'complete':
        // Add assistant response
        addMessage(
          activeSession.id,
          JSON.stringify(message.content, null, 2),
          'assistant',
          {
            workflow: message.content,
            confidence: message.metadata?.confidence,
            retrievedDocs: message.metadata?.retrieved_docs,
          }
        );
        setIsGenerating(false);
        
        // Save workflow to session and notify parent component
        if (message.content && activeSession) {
          updateSessionWorkflow(activeSession.id, message.content);
          if (onWorkflowGenerated) {
            onWorkflowGenerated(message.content);
          }
        }
        break;
      
      case 'error':
        addMessage(activeSession.id, `Error: ${message.content}`, 'system');
        setIsGenerating(false);
        break;
    }
  }

  useEffect(() => {
    scrollToBottom();
  }, [activeSession?.messages]);

  useEffect(() => {
    // Clear existing timeout
    if (sessionCreationTimeoutRef.current) {
      clearTimeout(sessionCreationTimeoutRef.current);
    }
    
    // Only create session if no sessions exist and we're not already creating one
    if (state.sessions.length === 0 && !creatingSessionRef.current) {
      // Debounce session creation to prevent duplicates
      sessionCreationTimeoutRef.current = setTimeout(() => {
        if (state.sessions.length === 0 && !creatingSessionRef.current) {
          creatingSessionRef.current = true;
          const sessionId = createNewSession('New Workflow Chat');
          console.log('Created new session:', sessionId);
          
          // Reset flag after creation
          setTimeout(() => {
            creatingSessionRef.current = false;
          }, 1000);
        }
      }, 50); // Small delay to debounce multiple rapid calls
    }
    
    // Cleanup timeout on unmount
    return () => {
      if (sessionCreationTimeoutRef.current) {
        clearTimeout(sessionCreationTimeoutRef.current);
      }
    };
  }, [state.sessions.length, createNewSession]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !activeSession) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    
    // Add user message
    addMessage(activeSession.id, userMessage, 'user');
    
    // Send via WebSocket if connected, otherwise use HTTP
    if (isConnected) {
      sendChatMessage(userMessage, activeSession.id);
      setIsGenerating(true);
    } else {
      // Fallback to HTTP API
      try {
        setIsGenerating(true);
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: userMessage,
            session_id: activeSession.id,
            use_knowledge_base: state.useKnowledgeBase,
          }),
        });

        const data = await response.json();
        
        addMessage(
          activeSession.id,
          JSON.stringify(data.response, null, 2),
          'assistant',
          {
            workflow: data.response,
            confidence: data.metadata?.confidence,
            retrievedDocs: data.metadata?.retrieved_documents,
            processingTime: data.metadata?.processing_time,
          }
        );

        // Save workflow to session and notify parent component
        if (data.response && activeSession) {
          updateSessionWorkflow(activeSession.id, data.response);
          if (onWorkflowGenerated) {
            onWorkflowGenerated(data.response);
          }
        }
      } catch (error) {
        addMessage(activeSession.id, `Error: ${error}`, 'system');
      } finally {
        setIsGenerating(false);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleExportWorkflow = (workflow: any) => {
    const dataStr = JSON.stringify(workflow, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `n8n_workflow_${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  if (!activeSession) {
    return (
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        flexDirection: 'column',
        gap: 2 
      }}>
        <Typography variant="h6" color="text.secondary">
          No active chat session
        </Typography>
        <Button
          variant="contained"
          onClick={() => createNewSession('New Workflow Chat')}
        >
          Start New Chat
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      backgroundColor: 'background.default',
    }}>
      {/* Chat Header */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderBottom: '1px solid',
          borderBottomColor: 'divider',
          backgroundColor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6">{activeSession.title}</Typography>
            <Typography variant="caption" color="text.secondary">
              {activeSession.messages.length} messages
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={state.useKnowledgeBase}
                  onChange={(e) => {
                    // Update knowledge base usage
                  }}
                  size="small"
                />
              }
              label={
                <Typography variant="caption">
                  Use Knowledge Base
                </Typography>
              }
            />
            
            <Chip
              icon={isConnected ? <BotIcon /> : <PersonIcon />}
              label={isConnected ? 'AI Connected' : 'Offline Mode'}
              size="small"
              color={isConnected ? 'success' : 'default'}
              variant="outlined"
            />
          </Box>
        </Box>
        
        {isGenerating && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress 
              sx={{ 
                height: 2,
                borderRadius: 1,
                '& .MuiLinearProgress-bar': {
                  background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
                },
              }} 
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Generating workflow...
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Messages Area */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box
          sx={{
            flexGrow: 1,
            overflowY: 'auto',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          {activeSession.messages.length === 0 ? (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                gap: 2,
                textAlign: 'center',
              }}
            >
              <Avatar
                sx={{
                  width: 80,
                  height: 80,
                  background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
                  mb: 2,
                }}
              >
                <BotIcon sx={{ fontSize: 40 }} />
              </Avatar>
              
              <Typography variant="h5" className="gradient-text" gutterBottom>
                Welcome to n8n RAG Studio
              </Typography>
              
              <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 500 }}>
                I can help you generate n8n workflows based on your requirements. 
                Just describe what you want to automate, and I'll create a workflow for you.
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
                {[
                  'Create a webhook to Slack notification',
                  'Build an API data sync workflow',
                  'Set up email automation',
                  'Generate a database backup workflow'
                ].map((suggestion) => (
                  <Chip
                    key={suggestion}
                    label={suggestion}
                    onClick={() => setInputValue(suggestion)}
                    sx={{
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: 'action.hover',
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          ) : (
            <>
              {activeSession.messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onExport={message.metadata?.workflow ? () => handleExportWorkflow(message.metadata!.workflow) : undefined}
                />
              ))}
              
              {isGenerating && <TypingIndicator />}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </Box>
      </Box>

      {/* Input Area */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderTop: '1px solid',
          borderTopColor: 'divider',
          backgroundColor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Describe the workflow you want to create..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isGenerating}
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'background.default',
              },
            }}
          />
          
          <IconButton
            color="primary"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isGenerating}
            sx={{
              width: 48,
              height: 48,
              background: inputValue.trim() && !isGenerating 
                ? 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)' 
                : undefined,
              color: inputValue.trim() && !isGenerating ? 'white' : undefined,
              '&:hover': {
                background: inputValue.trim() && !isGenerating
                  ? 'linear-gradient(135deg, #e55353 0%, #26a69a 100%)'
                  : undefined,
              },
            }}
          >
            <SendIcon />
          </IconButton>
        </Box>
        
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', textAlign: 'center', mt: 1 }}
        >
          Press Enter to send • Shift+Enter for new line
        </Typography>
      </Paper>
    </Box>
  );
};

export default ChatInterface;