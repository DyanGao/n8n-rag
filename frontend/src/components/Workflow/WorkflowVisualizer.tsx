import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Paper,
  Alert,
} from '@mui/material';
import {
  PlayArrow as TriggerIcon,
  Transform as TransformIcon,
  Storage as DataIcon,
  Notifications as NotificationIcon,
  Code as CodeIcon,
  Http as HttpIcon,
  Email as EmailIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';

interface WorkflowVisualizerProps {
  workflow: any;
}

interface NodeVisualization {
  id: string;
  name: string;
  type: string;
  category: 'trigger' | 'action' | 'transform' | 'output';
  parameters: any;
  position: { x: number; y: number };
  connections: string[];
}

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({ workflow }) => {
  const visualNodes = useMemo(() => {
    if (!workflow?.nodes) return [];

    return workflow.nodes.map((node: any) => {
      const nodeType = node.type || '';
      let category: NodeVisualization['category'] = 'action';
      
      // Determine category based on node type - improved logic for n8n node classification
      const nodeTypeLower = nodeType.toLowerCase();
      const nodeName = (node.name || '').toLowerCase();
      
      // Check for trigger nodes - multiple ways to identify them
      if (nodeTypeLower.includes('trigger') || 
          nodeTypeLower.includes('webhook') || 
          nodeTypeLower.includes('cron') ||
          nodeTypeLower.includes('schedule') ||
          nodeTypeLower.includes('manual') ||
          nodeTypeLower.includes('start') ||
          nodeTypeLower.includes('emailreadimap') ||
          nodeTypeLower.includes('pollabletrigger') ||
          nodeName.includes('trigger')) {
        category = 'trigger';
      } 
      // Check for transform/processing nodes
      else if (nodeTypeLower.includes('set') || 
               nodeTypeLower.includes('function') || 
               nodeTypeLower.includes('code') ||
               nodeTypeLower.includes('transform') ||
               nodeTypeLower.includes('filter') ||
               nodeTypeLower.includes('switch') ||
               nodeTypeLower.includes('merge') ||
               nodeTypeLower.includes('split') ||
               nodeTypeLower.includes('json') ||
               nodeTypeLower.includes('xml')) {
        category = 'transform';
      } 
      // Check for output/communication nodes
      else if (nodeTypeLower.includes('slack') || 
               nodeTypeLower.includes('email') || 
               nodeTypeLower.includes('telegram') ||
               nodeTypeLower.includes('notification') ||
               nodeTypeLower.includes('discord') ||
               nodeTypeLower.includes('output') ||
               nodeTypeLower.includes('webhook') ||
               nodeTypeLower.includes('smtp')) {
        category = 'output';
      }

      return {
        id: node.id || `node_${Math.random()}`,
        name: node.name || nodeType.split('.').pop() || 'Unknown Node',
        type: nodeType,
        category,
        parameters: node.parameters || {},
        position: node.position || { x: 0, y: 0 },
        connections: [],
      };
    });
  }, [workflow]);

  const connections = useMemo(() => {
    if (!workflow?.connections) return [];
    
    const connectionList = [];
    for (const [sourceId, outputs] of Object.entries(workflow.connections)) {
      if (outputs && typeof outputs === 'object') {
        for (const [outputType, connections] of Object.entries(outputs)) {
          if (Array.isArray(connections)) {
            for (const connectionGroup of connections) {
              if (Array.isArray(connectionGroup)) {
                for (const connection of connectionGroup) {
                  if (connection && connection.node) {
                    connectionList.push({
                      from: sourceId,
                      to: connection.node,
                      type: outputType,
                    });
                  }
                }
              }
            }
          }
        }
      }
    }
    return connectionList;
  }, [workflow]);

  const getNodeIcon = (category: string, type: string) => {
    if (category === 'trigger') return <TriggerIcon />;
    if (type.includes('http')) return <HttpIcon />;
    if (type.includes('email')) return <EmailIcon />;
    if (type.includes('schedule')) return <ScheduleIcon />;
    if (type.includes('code') || type.includes('function')) return <CodeIcon />;
    if (category === 'transform') return <TransformIcon />;
    if (category === 'output') return <NotificationIcon />;
    return <DataIcon />;
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'trigger': return '#4caf50';
      case 'transform': return '#ff9800';
      case 'output': return '#2196f3';
      default: return '#9c27b0';
    }
  };

  const getNodeDescription = (node: NodeVisualization) => {
    const params = node.parameters;
    const descriptions = [];
    
    if (params.url) descriptions.push(`URL: ${params.url}`);
    if (params.method) descriptions.push(`Method: ${params.method}`);
    if (params.channel) descriptions.push(`Channel: ${params.channel}`);
    if (params.toEmail) descriptions.push(`To: ${params.toEmail}`);
    if (params.operation) descriptions.push(`Operation: ${params.operation}`);
    
    return descriptions.join(', ') || 'No configuration details';
  };

  if (!visualNodes.length) {
    return (
      <Alert severity="warning">
        No nodes found in the workflow. The workflow might be empty or have an invalid format.
      </Alert>
    );
  }

  // Simple layout: arrange nodes in a grid
  const arrangedNodes = visualNodes.map((node: any, index: number) => ({
    ...node,
    layoutPosition: {
      x: 50 + (index % 3) * 300,
      y: 50 + Math.floor(index / 3) * 200,
    },
  }));

  // Calculate the required container height based on node positions
  // This ensures all nodes are visible by dynamically setting container height
  const maxY = arrangedNodes.reduce((max: number, node: any) => 
    Math.max(max, node.layoutPosition.y + 200), 400); // 200 is approximate node height + margin
  const containerHeight = Math.max(maxY, 400);

  return (
    <Box sx={{ height: '100%', overflow: 'auto', position: 'relative', p: 2 }}>
      {/* Workflow Info */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Workflow Structure
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip label={`${visualNodes.length} nodes`} size="small" />
          <Chip label={`${connections.length} connections`} size="small" />
        </Box>
      </Box>

      {/* Node Flow Visualization */}
      <Paper
        sx={{
          height: containerHeight,
          position: 'relative',
          backgroundColor: 'background.default',
          backgroundImage: 'radial-gradient(circle, #333 1px, transparent 1px)',
          backgroundSize: '20px 20px',
          overflow: 'visible',
        }}
      >
        {/* Connection Lines */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: containerHeight,
            pointerEvents: 'none',
            zIndex: 1,
          }}
        >
          {connections.map((connection, index) => {
            const fromNode = arrangedNodes.find((n: any) => n.name === connection.from);
            const toNode = arrangedNodes.find((n: any) => n.name === connection.to);
            
            if (!fromNode || !toNode) return null;
            
            const x1 = fromNode.layoutPosition.x + 150; // Center of source node
            const y1 = fromNode.layoutPosition.y + 80;
            const x2 = toNode.layoutPosition.x + 150; // Center of target node
            const y2 = toNode.layoutPosition.y + 80;
            
            return (
              <line
                key={index}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#4ecdc4"
                strokeWidth="2"
                strokeDasharray="4,4"
                opacity="0.7"
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {arrangedNodes.map((node: any) => (
          <Card
            key={node.id}
            sx={{
              position: 'absolute',
              left: node.layoutPosition.x,
              top: node.layoutPosition.y,
              width: 280,
              zIndex: 2,
              border: `2px solid ${getCategoryColor(node.category)}`,
              '&:hover': {
                transform: 'scale(1.02)',
                boxShadow: 4,
              },
              transition: 'all 0.2s ease-in-out',
            }}
          >
            <CardContent>
              {/* Node Header */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Box sx={{ color: getCategoryColor(node.category) }}>
                  {getNodeIcon(node.category, node.type)}
                </Box>
                <Typography variant="h6" noWrap>
                  {node.name}
                </Typography>
                <Chip 
                  label={node.category} 
                  size="small" 
                  sx={{ 
                    ml: 'auto',
                    backgroundColor: getCategoryColor(node.category),
                    color: 'white',
                  }} 
                />
              </Box>

              {/* Node Type */}
              <Typography variant="caption" color="text.secondary" gutterBottom>
                {node.type}
              </Typography>

              {/* Node Description */}
              <Typography variant="body2" sx={{ mt: 1, fontSize: '0.85rem' }}>
                {getNodeDescription(node)}
              </Typography>

              {/* Parameters Preview */}
              {Object.keys(node.parameters).length > 0 && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {Object.keys(node.parameters).length} parameter(s) configured
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Paper>

      {/* Legend */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Node Types:
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {[
            { category: 'trigger', label: 'Triggers', color: '#4caf50' },
            { category: 'action', label: 'Actions', color: '#9c27b0' },
            { category: 'transform', label: 'Transform', color: '#ff9800' },
            { category: 'output', label: 'Output', color: '#2196f3' },
          ].map(({ category, label, color }) => (
            <Chip
              key={category}
              label={label}
              size="small"
              sx={{
                backgroundColor: color,
                color: 'white',
              }}
            />
          ))}
        </Box>
      </Box>

      {/* Connections Summary */}
      {connections.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Connections:
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {connections.map((connection, index) => {
              const fromNode = visualNodes.find((n: any) => n.name === connection.from);
              const toNode = visualNodes.find((n: any) => n.name === connection.to);
              
              if (!fromNode || !toNode) return null;
              
              return (
                <Typography key={index} variant="caption" color="text.secondary">
                  {fromNode.name} → {toNode.name} ({connection.type})
                </Typography>
              );
            })}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default WorkflowVisualizer;