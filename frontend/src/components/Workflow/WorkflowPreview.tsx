import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  IconButton,
  Tabs,
  Tab,
  Alert,
  Chip,
  Divider,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Download as DownloadIcon,
  Code as CodeIcon,
  Visibility as PreviewIcon,
  Share as ShareIcon,
  ContentCopy as CopyIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import WorkflowVisualizer from './WorkflowVisualizer';

interface WorkflowPreviewProps {
  workflow: any;
  onBack?: () => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`workflow-tabpanel-${index}`}
      aria-labelledby={`workflow-tab-${index}`}
      {...other}
      style={{ height: '100%', overflow: 'hidden' }}
    >
      {value === index && (
        <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const WorkflowPreview: React.FC<WorkflowPreviewProps> = ({ workflow, onBack }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState('');

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleDownload = () => {
    const dataStr = JSON.stringify(workflow, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `n8n_workflow_${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(workflow, null, 2));
  };

  const handleImportToN8n = () => {
    // This would open n8n with the workflow data
    // For now, we'll just show instructions
    alert('Copy the JSON and paste it into n8n using the "Import from Clipboard" option in the workflow menu.');
  };

  const getWorkflowStats = () => {
    if (!workflow || !workflow.nodes) return null;
    
    const nodes = workflow.nodes;
    const nodeTypes = [...new Set(nodes.map((n: any) => n.type))];
    const triggerNodes = nodes.filter((n: any) => 
      n.type?.includes('trigger') || n.type?.includes('webhook')
    );
    
    return {
      totalNodes: nodes.length,
      nodeTypes: nodeTypes.length,
      triggerNodes: triggerNodes.length,
      uniqueTypes: nodeTypes,
    };
  };

  const workflowStats = getWorkflowStats();

  if (!workflow) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: 2,
        }}
      >
        <Typography variant="h6" color="text.secondary">
          No workflow to preview
        </Typography>
        <Button variant="outlined" onClick={onBack}>
          Go Back to Chat
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderBottom: '1px solid',
          borderBottomColor: 'divider',
          backgroundColor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <IconButton onClick={onBack}>
              <BackIcon />
            </IconButton>
            <Typography variant="h5" className="gradient-text">
              Workflow Preview
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Copy to Clipboard">
              <IconButton onClick={handleCopyToClipboard}>
                <CopyIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Download JSON">
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownload}
                size="small"
              >
                Download
              </Button>
            </Tooltip>
            
            <Tooltip title="Import to n8n">
              <Button
                variant="contained"
                startIcon={<LaunchIcon />}
                onClick={handleImportToN8n}
                size="small"
                sx={{
                  background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #e55353 0%, #26a69a 100%)',
                  },
                }}
              >
                Import to n8n
              </Button>
            </Tooltip>
          </Box>
        </Box>

        {/* Workflow Stats */}
        {workflowStats && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`${workflowStats.totalNodes} nodes`} size="small" />
            <Chip label={`${workflowStats.nodeTypes} types`} size="small" />
            <Chip label={`${workflowStats.triggerNodes} triggers`} size="small" />
            {workflowStats.uniqueTypes.slice(0, 3).map((type: any, index: number) => (
              <Chip key={index} label={String(type).split('.').pop()} size="small" variant="outlined" />
            ))}
            {workflowStats.uniqueTypes.length > 3 && (
              <Chip label={`+${workflowStats.uniqueTypes.length - 3} more`} size="small" variant="outlined" />
            )}
          </Box>
        )}
      </Paper>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Visual Preview" icon={<PreviewIcon />} />
          <Tab label="JSON Code" icon={<CodeIcon />} />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {workflow.nodes && workflow.nodes.length > 0 ? (
              <WorkflowVisualizer workflow={workflow} />
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  gap: 2,
                }}
              >
                <Typography variant="h6" color="text.secondary">
                  No nodes found in workflow
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  The workflow appears to be empty or invalid
                </Typography>
              </Box>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              This is the complete n8n workflow JSON. You can copy this and import it directly into n8n.
            </Alert>
            
            <SyntaxHighlighter
              language="json"
              style={oneDark}
              customStyle={{
                margin: 0,
                borderRadius: 8,
                fontSize: '0.875rem',
              }}
              showLineNumbers
              wrapLines
            >
              {JSON.stringify(workflow, null, 2)}
            </SyntaxHighlighter>
          </Box>
        </TabPanel>
      </Box>

      {/* Share Dialog */}
      <Dialog open={shareDialogOpen} onClose={() => setShareDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Share Workflow</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Share this workflow with others by providing them with this URL:
          </Typography>
          <TextField
            fullWidth
            value={shareUrl}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <IconButton onClick={() => navigator.clipboard.writeText(shareUrl)}>
                  <CopyIcon />
                </IconButton>
              ),
            }}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShareDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkflowPreview;