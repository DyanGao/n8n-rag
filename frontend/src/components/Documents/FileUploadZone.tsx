import React, { useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as FileIcon,
  Code as CodeIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

import { useDocuments } from '../../contexts/DocumentContext';

interface FileUploadZoneProps {
  onClose?: () => void;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({ onClose }) => {
  const { uploadDocument } = useDocuments();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      try {
        await uploadDocument(file);
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }
    
    if (onClose) {
      onClose();
    }
  }, [uploadDocument, onClose]);

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
    acceptedFiles,
    fileRejections,
  } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const getDragClass = () => {
    if (isDragReject) return 'drag-reject';
    if (isDragAccept) return 'drag-accept';
    if (isDragActive) return 'drag-active';
    return '';
  };

  const getFileIcon = (file: File) => {
    const type = file.type;
    if (type.includes('json')) return <CodeIcon color="secondary" />;
    if (type.includes('pdf')) return <PdfIcon color="error" />;
    if (type.includes('image')) return <ImageIcon color="info" />;
    return <FileIcon color="primary" />;
  };

  return (
    <Box sx={{ mt: 2 }}>
      {/* Drop Zone */}
      <Paper
        {...getRootProps()}
        className={getDragClass()}
        sx={{
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          backgroundColor: isDragActive ? 'action.hover' : 'background.default',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover',
          },
        }}
      >
        <input {...getInputProps()} />
        
        <CloudUploadIcon
          sx={{
            fontSize: 48,
            color: isDragActive ? 'primary.main' : 'text.secondary',
            mb: 2,
          }}
        />
        
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </Typography>
        
        <Typography variant="body2" color="text.secondary" gutterBottom>
          or click to browse files
        </Typography>
        
        <Typography variant="caption" color="text.secondary">
          Supported formats: JSON, PDF, TXT, MD, DOCX • Max 10MB per file
        </Typography>
      </Paper>

      {/* File Previews */}
      {acceptedFiles.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Files to Upload:
          </Typography>
          <List dense>
            {acceptedFiles.map((file) => (
              <ListItem key={file.name}>
                <ListItemIcon>
                  {getFileIcon(file)}
                </ListItemIcon>
                <ListItemText
                  primary={file.name}
                  secondary={`${(file.size / 1024).toFixed(1)} KB • ${file.type}`}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Rejected Files */}
      {fileRejections.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="body2" gutterBottom>
            Some files were rejected:
          </Typography>
          {fileRejections.map(({ file, errors }) => (
            <Typography key={file.name} variant="caption" display="block">
              • {file.name}: {errors.map((e: any) => e.message).join(', ')}
            </Typography>
          ))}
        </Alert>
      )}

      {/* Supported Formats Info */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Supported Document Types:
        </Typography>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CodeIcon color="secondary" fontSize="small" />
            <Typography variant="body2">JSON workflows</Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PdfIcon color="error" fontSize="small" />
            <Typography variant="body2">PDF documents</Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FileIcon color="primary" fontSize="small" />
            <Typography variant="body2">Text files</Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FileIcon color="info" fontSize="small" />
            <Typography variant="body2">Markdown files</Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default FileUploadZone;