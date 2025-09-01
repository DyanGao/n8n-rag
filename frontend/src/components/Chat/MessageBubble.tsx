import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  IconButton,
  Collapse,
  Chip,
  Divider,
  Button,
  Tooltip,
} from '@mui/material';
import {
  Person as PersonIcon,
  SmartToy as BotIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Download as DownloadIcon,
  ThumbUp,
  ThumbDown,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { Message } from '../../contexts/ChatContext';

interface MessageBubbleProps {
  message: Message;
  onExport?: () => void;
  onFeedback?: (rating: number, comment?: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ 
  message, 
  onExport, 
  onFeedback 
}) => {
  const [showMetadata, setShowMetadata] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isAssistant = message.role === 'assistant';

  const getAvatarIcon = () => {
    if (isUser) return <PersonIcon />;
    if (isSystem) return <InfoIcon />;
    return <BotIcon />;
  };

  const getAvatarColor = () => {
    if (isUser) return 'primary.main';
    if (isSystem) return 'warning.main';
    return 'secondary.main';
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  const handleFeedback = (rating: number) => {
    if (onFeedback) {
      onFeedback(rating);
      setFeedbackGiven(true);
    }
  };

  const renderContent = () => {
    if (isSystem) {
      return (
        <Typography variant="body2" color="warning.main">
          {message.content}
        </Typography>
      );
    }

    // Try to parse as JSON for workflow display
    let parsedWorkflow = null;
    try {
      parsedWorkflow = JSON.parse(message.content);
    } catch {
      // Not JSON, render as markdown
    }

    if (parsedWorkflow && isAssistant) {
      return (
        <Box>
          <Typography variant="body2" gutterBottom>
            I've generated an n8n workflow for you:
          </Typography>
          
          <SyntaxHighlighter
            language="json"
            style={oneDark}
            customStyle={{
              borderRadius: 8,
              fontSize: '0.875rem',
              margin: '8px 0',
            }}
          >
            {JSON.stringify(parsedWorkflow, null, 2)}
          </SyntaxHighlighter>
          
          {onExport && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<DownloadIcon />}
              onClick={onExport}
              sx={{ mt: 1 }}
            >
              Download Workflow
            </Button>
          )}
        </Box>
      );
    }

    return (
      <ReactMarkdown
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = typeof props === 'object' && 'inline' in props ? props.inline : false;
            return !isInline && match ? (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  borderRadius: 8,
                  fontSize: '0.875rem',
                }}
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code
                className={className}
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  padding: '2px 4px',
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {message.content}
      </ReactMarkdown>
    );
  };

  return (
    <Box
      className={`message-bubble ${message.role}`}
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 1,
        mb: 2,
      }}
    >
      {/* Avatar */}
      <Avatar
        sx={{
          width: 36,
          height: 36,
          backgroundColor: getAvatarColor(),
          flexShrink: 0,
        }}
      >
        {getAvatarIcon()}
      </Avatar>

      {/* Message Content */}
      <Box
        sx={{
          maxWidth: '80%',
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
        }}
      >
        <Paper
          elevation={1}
          sx={{
            p: 2,
            backgroundColor: isUser 
              ? 'rgba(255, 107, 107, 0.1)' 
              : isSystem 
                ? 'rgba(255, 193, 7, 0.1)'
                : 'background.paper',
            borderRadius: 2,
            border: isSystem ? '1px solid' : 'none',
            borderColor: isSystem ? 'warning.main' : 'transparent',
          }}
        >
          {/* Message Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {message.role === 'user' ? 'You' : message.role === 'system' ? 'System' : 'Assistant'}
              {' • '}
              {message.timestamp.toLocaleTimeString()}
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Tooltip title="Copy to clipboard">
                <IconButton size="small" onClick={handleCopyToClipboard}>
                  <CopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              
              {message.metadata && Object.keys(message.metadata).length > 0 && (
                <Tooltip title="Show metadata">
                  <IconButton
                    size="small"
                    onClick={() => setShowMetadata(!showMetadata)}
                  >
                    {showMetadata ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>

          {/* Message Content */}
          {renderContent()}

          {/* Feedback Buttons for Assistant Messages */}
          {isAssistant && !feedbackGiven && (
            <Box sx={{ display: 'flex', gap: 1, mt: 2, justifyContent: 'flex-end' }}>
              <Tooltip title="Helpful">
                <IconButton
                  size="small"
                  onClick={() => handleFeedback(5)}
                  sx={{ color: 'success.main' }}
                >
                  <ThumbUp fontSize="small" />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Not helpful">
                <IconButton
                  size="small"
                  onClick={() => handleFeedback(1)}
                  sx={{ color: 'error.main' }}
                >
                  <ThumbDown fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}

          {feedbackGiven && (
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', display: 'block', mt: 1 }}>
              Thank you for your feedback!
            </Typography>
          )}
        </Paper>

        {/* Metadata Collapse */}
        {message.metadata && (
          <Collapse in={showMetadata}>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                backgroundColor: 'background.default',
                borderRadius: 2,
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                Message Metadata
              </Typography>
              
              <Divider sx={{ mb: 1 }} />
              
              {message.metadata.confidence && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="caption">Confidence:</Typography>
                  <Chip
                    label={`${(message.metadata.confidence * 100).toFixed(1)}%`}
                    size="small"
                    color={message.metadata.confidence > 0.7 ? 'success' : message.metadata.confidence > 0.4 ? 'warning' : 'error'}
                  />
                </Box>
              )}
              
              {message.metadata.processingTime && (
                <Typography variant="caption" display="block" gutterBottom>
                  Processing Time: {message.metadata.processingTime.toFixed(2)}s
                </Typography>
              )}
              
              {message.metadata.retrievedDocs && message.metadata.retrievedDocs.length > 0 && (
                <Box>
                  <Typography variant="caption" gutterBottom>
                    Retrieved Documents:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {message.metadata.retrievedDocs.map((doc, index) => (
                      <Chip
                        key={index}
                        label={doc}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Box>
              )}
            </Paper>
          </Collapse>
        )}
      </Box>
    </Box>
  );
};

export default MessageBubble;