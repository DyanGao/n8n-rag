import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Chip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Fab,
  Pagination,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Search as SearchIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  CloudUpload as CloudUploadIcon,
  Description as FileIcon,
  Code as CodeIcon,
  Image as ImageIcon,
  PictureAsPdf as PdfIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

import { useDocuments } from '../../contexts/DocumentContext';
import FileUploadZone from './FileUploadZone';

const DocumentManager: React.FC = () => {
  const {
    state,
    dispatch,
    refreshDocuments,
    deleteDocument,
    getFilteredDocuments,
    setPage,
    setItemsPerPage,
  } = useDocuments();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<string | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);


  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch({ type: 'SET_SEARCH_QUERY', payload: event.target.value });
  };

  const handleDeleteClick = (fileId: string) => {
    setDocumentToDelete(fileId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (documentToDelete) {
      try {
        await deleteDocument(documentToDelete);
        setDeleteDialogOpen(false);
        setDocumentToDelete(null);
      } catch (error) {
        console.error('Failed to delete document:', error);
      }
    }
  };

  const handleDeleteAll = async () => {
    if (window.confirm('Are you sure you want to delete ALL documents? This cannot be undone.')) {
      try {
        const response = await fetch('/api/documents', { method: 'DELETE' });
        if (response.ok) {
          // Clear local state and refresh
          dispatch({ type: 'SET_DOCUMENTS', payload: { documents: [], pagination: { ...state.pagination, totalItems: 0, totalPages: 0 } } });
          await refreshDocuments();
        }
      } catch (error) {
        console.error('Failed to delete all documents:', error);
      }
    }
  };

  const getFileTypeIcon = (contentType: string) => {
    if (!contentType) return <FileIcon />;
    const type = contentType.toLowerCase();
    if (type.includes('json')) return <CodeIcon />;
    if (type.includes('pdf')) return <PdfIcon />;
    if (type.includes('image')) return <ImageIcon />;
    return <FileIcon />;
  };

  const getFileTypeColor = (contentType: string) => {
    if (!contentType) return 'default';
    const type = contentType.toLowerCase();
    if (type.includes('json')) return 'secondary';
    if (type.includes('pdf')) return 'error';
    if (type.includes('image')) return 'info';
    return 'default';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredDocuments = getFilteredDocuments();
  console.log('DocumentManager - filteredDocuments:', filteredDocuments);
  console.log('DocumentManager - filteredDocuments length:', filteredDocuments.length);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 3, borderBottom: '1px solid', borderBottomColor: 'divider' }}>
        <Typography variant="h4" className="gradient-text" gutterBottom>
          Knowledge Base
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          Upload documents to enhance workflow generation with your custom knowledge
        </Typography>

        {/* Search and Actions */}
        <Box sx={{ display: 'flex', gap: 2, mt: 3, alignItems: 'center' }}>
          <TextField
            placeholder="Search documents..."
            value={state.searchQuery}
            onChange={handleSearchChange}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1 }}
          />
          
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
            sx={{
              background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #e55353 0%, #26a69a 100%)',
              },
            }}
          >
            Upload
          </Button>
          
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => handleDeleteAll()}
            disabled={state.isLoading || filteredDocuments.length === 0}
          >
            Delete All
          </Button>
          
          <IconButton onClick={refreshDocuments} disabled={state.isLoading}>
            <RefreshIcon />
          </IconButton>
        </Box>

        {/* Upload Progress */}
        {Object.keys(state.uploadProgress).length > 0 && (
          <Box sx={{ mt: 2 }}>
            {Object.values(state.uploadProgress).map((progress) => (
              <Box key={progress.fileId} sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">{progress.filename}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {progress.status === 'uploading' && `${progress.progress}%`}
                    {progress.status === 'processing' && 'Processing...'}
                    {progress.status === 'completed' && 'Completed'}
                    {progress.status === 'error' && 'Error'}
                  </Typography>
                </Box>
                <LinearProgress
                  variant={progress.status === 'processing' ? 'indeterminate' : 'determinate'}
                  value={progress.progress}
                  color={progress.status === 'error' ? 'error' : 'primary'}
                />
                {progress.error && (
                  <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                    {progress.error}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        )}
      </Box>

      {/* Documents Grid */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 3 }}>
        {state.isLoading ? (
          <LinearProgress />
        ) : filteredDocuments.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '60%',
              gap: 2,
              textAlign: 'center',
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 80, color: 'text.secondary' }} />
            <Typography variant="h6" color="text.secondary">
              {state.searchQuery ? 'No documents match your search' : 'No documents uploaded yet'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {state.searchQuery 
                ? 'Try adjusting your search terms'
                : 'Upload documents to build your knowledge base for better workflow generation'
              }
            </Typography>
            {!state.searchQuery && (
              <Button
                variant="outlined"
                startIcon={<UploadIcon />}
                onClick={() => setUploadDialogOpen(true)}
              >
                Upload Your First Document
              </Button>
            )}
          </Box>
        ) : (
          <Grid container spacing={2}>
            {filteredDocuments.map((document) => {
              console.log('🎨 [UI] DocumentManager - processing document:', document);
              console.log('🎨 [UI] Document processingStatus:', document.processingStatus);
              if (!document || !document.fileId) {
                console.log('🎨 [UI] DocumentManager - document filtered out:', document);
                return null;
              }
              return (
              <Grid item xs={12} sm={6} md={4} key={document.fileId}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 4,
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      {getFileTypeIcon(document.contentType)}
                      <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
                        {document.filename}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                      <Chip
                        label={document.contentType?.split('/')[1]?.toUpperCase() || 'FILE'}
                        size="small"
                        color={getFileTypeColor(document.contentType || '') as any}
                        variant="outlined"
                      />
                      <Chip
                        label={`${document.chunksCreated} chunks`}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={(() => {
                          console.log('🏷️ [CHIP] Rendering status chip with value:', document.processingStatus);
                          return document.processingStatus;
                        })()}
                        size="small"
                        color={
                          document.processingStatus === 'completed' ? 'success' :
                          document.processingStatus === 'error' ? 'error' : 'warning'
                        }
                      />
                    </Box>

                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Size: {formatFileSize(document.size)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Uploaded: {formatDate(document.uploadDate)}
                    </Typography>
                  </CardContent>

                  <CardActions>
                    <IconButton
                      color="error"
                      onClick={() => handleDeleteClick(document.fileId)}
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
              )
            }).filter(Boolean)}
          </Grid>
        )}

        {/* Pagination Controls */}
        {filteredDocuments.length > 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3, gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Items per page</InputLabel>
              <Select
                value={state.pagination.itemsPerPage}
                label="Items per page"
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
              >
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={25}>25</MenuItem>
                <MenuItem value={50}>50</MenuItem>
                <MenuItem value={100}>100</MenuItem>
              </Select>
            </FormControl>
            
            <Typography variant="body2" color="text.secondary">
              {state.pagination.totalItems > 0 
                ? `${((state.pagination.currentPage - 1) * state.pagination.itemsPerPage) + 1}-${Math.min(state.pagination.currentPage * state.pagination.itemsPerPage, state.pagination.totalItems)} of ${state.pagination.totalItems} documents`
                : 'No documents'
              }
            </Typography>
            
            <Pagination
              count={state.pagination.totalPages}
              page={state.pagination.currentPage}
              onChange={(event, page) => setPage(page)}
              color="primary"
              shape="rounded"
              showFirstButton
              showLastButton
            />
          </Box>
        )}
      </Box>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          background: 'linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #e55353 0%, #26a69a 100%)',
          },
        }}
        onClick={() => setUploadDialogOpen(true)}
      >
        <UploadIcon />
      </Fab>

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload Documents</DialogTitle>
        <DialogContent>
          <FileUploadZone onClose={() => setUploadDialogOpen(false)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this document? This will remove it from your knowledge base and cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentManager;