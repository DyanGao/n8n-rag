import React, { createContext, useContext, useReducer, useEffect, useCallback, useRef, ReactNode } from 'react';

// Types
export interface DocumentMetadata {
  fileId: string;
  filename: string;
  uploadDate: string;
  size: number;
  contentType: string;
  chunksCreated: number;
  processingStatus: 'processing' | 'completed' | 'error';
}

export interface UploadProgress {
  fileId: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
}

interface DocumentState {
  documents: DocumentMetadata[];
  uploadProgress: { [key: string]: UploadProgress };
  selectedDocuments: string[];
  searchQuery: string;
  isLoading: boolean;
  pagination: {
    currentPage: number;
    itemsPerPage: number;
    totalItems: number;
    totalPages: number;
  };
}

// Actions
type DocumentAction =
  | { type: 'SET_DOCUMENTS'; payload: { documents: DocumentMetadata[]; pagination: any } }
  | { type: 'ADD_DOCUMENT'; payload: DocumentMetadata }
  | { type: 'UPDATE_DOCUMENT'; payload: { fileId: string; updates: Partial<DocumentMetadata> } }
  | { type: 'DELETE_DOCUMENT'; payload: string }
  | { type: 'SET_UPLOAD_PROGRESS'; payload: UploadProgress }
  | { type: 'REMOVE_UPLOAD_PROGRESS'; payload: string }
  | { type: 'SET_SELECTED_DOCUMENTS'; payload: string[] }
  | { type: 'TOGGLE_DOCUMENT_SELECTION'; payload: string }
  | { type: 'SET_SEARCH_QUERY'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_PAGE'; payload: number }
  | { type: 'SET_ITEMS_PER_PAGE'; payload: number };

// Initial state
const initialState: DocumentState = {
  documents: [],
  uploadProgress: {},
  selectedDocuments: [],
  searchQuery: '',
  isLoading: false,
  pagination: {
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0,
    totalPages: 1,
  },
};

// Reducer
const documentReducer = (state: DocumentState, action: DocumentAction): DocumentState => {
  switch (action.type) {
    case 'SET_DOCUMENTS':
      return {
        ...state,
        documents: action.payload.documents,
        pagination: {
          ...state.pagination,
          ...action.payload.pagination,
        },
      };

    case 'ADD_DOCUMENT':
      const newDocuments = [action.payload, ...state.documents];
      const addedTotalItems = state.pagination.totalItems + 1;
      const addedTotalPages = Math.ceil(addedTotalItems / state.pagination.itemsPerPage);
      
      return {
        ...state,
        documents: newDocuments,
        pagination: {
          ...state.pagination,
          totalItems: addedTotalItems,
          totalPages: addedTotalPages,
        },
      };

    case 'UPDATE_DOCUMENT':
      return {
        ...state,
        documents: state.documents.map(doc =>
          doc.fileId === action.payload.fileId
            ? { ...doc, ...action.payload.updates }
            : doc
        ),
      };

    case 'DELETE_DOCUMENT':
      const filteredDocuments = state.documents.filter(doc => doc.fileId !== action.payload);
      const deletedTotalItems = state.pagination.totalItems - 1;
      const deletedTotalPages = Math.max(1, Math.ceil(deletedTotalItems / state.pagination.itemsPerPage));
      
      return {
        ...state,
        documents: filteredDocuments,
        selectedDocuments: state.selectedDocuments.filter(id => id !== action.payload),
        pagination: {
          ...state.pagination,
          totalItems: deletedTotalItems,
          totalPages: deletedTotalPages,
        },
      };

    case 'SET_UPLOAD_PROGRESS':
      return {
        ...state,
        uploadProgress: {
          ...state.uploadProgress,
          [action.payload.fileId]: action.payload,
        },
      };

    case 'REMOVE_UPLOAD_PROGRESS':
      const newProgress = { ...state.uploadProgress };
      delete newProgress[action.payload];
      return {
        ...state,
        uploadProgress: newProgress,
      };

    case 'SET_SELECTED_DOCUMENTS':
      return {
        ...state,
        selectedDocuments: action.payload,
      };

    case 'TOGGLE_DOCUMENT_SELECTION':
      const isSelected = state.selectedDocuments.includes(action.payload);
      return {
        ...state,
        selectedDocuments: isSelected
          ? state.selectedDocuments.filter(id => id !== action.payload)
          : [...state.selectedDocuments, action.payload],
      };

    case 'SET_SEARCH_QUERY':
      return {
        ...state,
        searchQuery: action.payload,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'SET_PAGE':
      return {
        ...state,
        pagination: {
          ...state.pagination,
          currentPage: action.payload,
        },
      };

    case 'SET_ITEMS_PER_PAGE':
      return {
        ...state,
        pagination: {
          ...state.pagination,
          itemsPerPage: action.payload,
          currentPage: 1, // Reset to first page
        },
      };

    default:
      return state;
  }
};

// Context
interface DocumentContextValue {
  state: DocumentState;
  dispatch: React.Dispatch<DocumentAction>;

  // Helper functions
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (fileId: string) => Promise<void>;
  refreshDocuments: () => Promise<void>;
  getFilteredDocuments: () => DocumentMetadata[];
  selectAllDocuments: () => void;
  clearSelection: () => void;
  setPage: (page: number) => void;
  setItemsPerPage: (itemsPerPage: number) => void;
}

const DocumentContext = createContext<DocumentContextValue | undefined>(undefined);

// Provider
interface DocumentProviderProps {
  children: ReactNode;
}

export const DocumentProvider: React.FC<DocumentProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(documentReducer, initialState);
  const hasLoadedInitially = useRef(false);

  // Helper function to transform API response to frontend format
  const transformDocumentFromAPI = (apiDoc: any): DocumentMetadata => {
    console.log('🔄 [TRANSFORM] Transforming API doc:', apiDoc);
    console.log('🔄 [TRANSFORM] API doc status field:', apiDoc.status);
    console.log('🔄 [TRANSFORM] API doc processing_status field:', apiDoc.processing_status);
    
    if (!apiDoc || (!apiDoc.fileId && !apiDoc.file_id)) {
      console.error('❌ [TRANSFORM] API doc is null, undefined, or missing fileId/file_id:', apiDoc);
      // Skip invalid documents instead of creating placeholder
      return null as any;
    }
    
    let processingStatus: 'processing' | 'completed' | 'error';
    if (apiDoc.status === 'processed' || apiDoc.status === 'success' || apiDoc.processing_status === 'completed') {
      processingStatus = 'completed';
      console.log('✅ [TRANSFORM] Status set to completed');
    } else if (apiDoc.status === 'processing' || apiDoc.processing_status === 'processing') {
      processingStatus = 'processing';
      console.log('⏳ [TRANSFORM] Status set to processing');
    } else if (apiDoc.status === 'error' || apiDoc.processing_status === 'error') {
      processingStatus = 'error';
      console.log('❌ [TRANSFORM] Status set to error');
    } else {
      // Default to completed for workflow templates that are successfully uploaded
      processingStatus = 'completed';
      console.log('✅ [TRANSFORM] Status defaulted to completed');
    }
    
    const transformed: DocumentMetadata = {
      fileId: apiDoc.fileId || apiDoc.id || apiDoc.file_id,
      filename: apiDoc.filename || 'Unknown File',
      uploadDate: apiDoc.uploadDate || apiDoc.uploaded_at || apiDoc.upload_date || new Date().toISOString(),
      size: apiDoc.size || 0,
      contentType: apiDoc.contentType || apiDoc.type || apiDoc.file_type || 'application/json',
      chunksCreated: apiDoc.chunksCreated || apiDoc.chunks_created || apiDoc.nodes_count || 0,
      processingStatus: processingStatus,
    };
    
    console.log('✅ [TRANSFORM] Final transformed doc:', transformed);
    console.log('✅ [TRANSFORM] Final processingStatus:', transformed.processingStatus);
    return transformed;
  };


  const uploadDocument = async (file: File): Promise<void> => {
    const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Set initial progress
    dispatch({
      type: 'SET_UPLOAD_PROGRESS',
      payload: {
        fileId,
        filename: file.name,
        progress: 0,
        status: 'uploading',
      },
    });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();

      // Update progress to processing
      dispatch({
        type: 'SET_UPLOAD_PROGRESS',
        payload: {
          fileId,
          filename: file.name,
          progress: 50,
          status: 'processing',
        },
      });

      // Add document to list with safe defaults
      const document: DocumentMetadata = {
        fileId: result.file_id || fileId,
        filename: result.filename || file.name,
        uploadDate: result.upload_time || new Date().toISOString(),
        size: result.size || file.size,
        contentType: result.type || file.type || 'application/octet-stream',
        chunksCreated: result.chunks_created || 0,
        processingStatus: result.processing_status === 'success' ? 'completed' : 'error',
      };

      dispatch({ type: 'ADD_DOCUMENT', payload: document });

      // Complete progress
      dispatch({
        type: 'SET_UPLOAD_PROGRESS',
        payload: {
          fileId,
          filename: file.name,
          progress: 100,
          status: 'completed',
        },
      });

      // Remove progress after delay
      setTimeout(() => {
        dispatch({ type: 'REMOVE_UPLOAD_PROGRESS', payload: fileId });
      }, 3000);

    } catch (error) {
      dispatch({
        type: 'SET_UPLOAD_PROGRESS',
        payload: {
          fileId,
          filename: file.name,
          progress: 0,
          status: 'error',
          error: error instanceof Error ? error.message : 'Upload failed',
        },
      });

      // Remove progress after delay
      setTimeout(() => {
        dispatch({ type: 'REMOVE_UPLOAD_PROGRESS', payload: fileId });
      }, 5000);
    }
  };

  const deleteDocument = async (fileId: string): Promise<void> => {
    try {
      console.log('Attempting to delete document with fileId:', fileId);
      
      const response = await fetch(`/api/documents/${fileId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Delete failed with response:', errorText);
        throw new Error(`Delete failed: ${errorText}`);
      }

      const result = await response.json();
      console.log('Delete response:', result);

      // Remove from local state immediately
      dispatch({ type: 'DELETE_DOCUMENT', payload: fileId });
    } catch (error) {
      console.error('Failed to delete document:', error);
      throw error;
    }
  };

  const refreshDocuments = useCallback(async (): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      
      const params = new URLSearchParams({
        page: state.pagination.currentPage.toString(),
        per_page: state.pagination.itemsPerPage.toString(),
        ...(state.searchQuery && { search: state.searchQuery }),
      });
      
      const response = await fetch(`/api/documents?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      console.log('Raw API response:', data);
      console.log('Documents array:', data.documents);
      console.log('Documents array length:', data.documents?.length);
      
      const transformedData = {
        documents: data.documents.map(transformDocumentFromAPI).filter((doc: any) => doc !== null),
        pagination: {
          currentPage: data.pagination?.page || data.page || 1,
          itemsPerPage: data.pagination?.per_page || data.per_page || 10,
          totalItems: data.pagination?.total || data.total || 0,
          totalPages: data.pagination?.total_pages || data.total_pages || 1,
        }
      };
      console.log('📊 [PAGINATION] Raw API data pagination (nested):', data.pagination);
      console.log('📊 [PAGINATION] Raw API data pagination (root):', {page: data.page, per_page: data.per_page, total: data.total, total_pages: data.total_pages});
      console.log('📊 [PAGINATION] Transformed pagination:', transformedData.pagination);
      console.log('📄 [DOCUMENTS] Transformed data:', transformedData);
      console.log('📄 [DOCUMENTS] Transformed documents count:', transformedData.documents.length);
      
      dispatch({ type: 'SET_DOCUMENTS', payload: transformedData });
    } catch (error) {
      console.error('Failed to refresh documents:', error);
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.pagination.currentPage, state.pagination.itemsPerPage, state.searchQuery]);

  // Initial load on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        const params = new URLSearchParams({
          page: '1',
          per_page: '10',
        });
        
        const response = await fetch(`/api/documents?${params}`);
        if (!response.ok) {
          throw new Error('Failed to fetch documents');
        }

        const data = await response.json();
        console.log('Initial load - Raw API response:', data);
        console.log('Initial load - Documents array:', data.documents);
        console.log('Initial load - Documents array length:', data.documents?.length);
        
        const transformedData = {
          documents: data.documents.map(transformDocumentFromAPI).filter((doc: any) => doc !== null),
          pagination: {
            currentPage: data.pagination?.page || data.page || 1,
            itemsPerPage: data.pagination?.per_page || data.per_page || 10,
            totalItems: data.pagination?.total || data.total || 0,
            totalPages: data.pagination?.total_pages || data.total_pages || 1,
          }
        };
        console.log('📊 [INITIAL] Raw API data pagination:', {page: data.pagination?.page || data.page, per_page: data.pagination?.per_page || data.per_page, total: data.pagination?.total || data.total, total_pages: data.pagination?.total_pages || data.total_pages});
        console.log('📊 [INITIAL] Transformed pagination:', transformedData.pagination);
        console.log('📄 [INITIAL] Transformed documents count:', transformedData.documents.length);
        
        dispatch({ type: 'SET_DOCUMENTS', payload: transformedData });
        hasLoadedInitially.current = true;
      } catch (error) {
        console.error('Failed to load initial documents:', error);
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };
    
    fetchData();
  }, []); // Run once on mount

  // Auto-refresh when pagination or search changes (skip initial render)
  useEffect(() => {
    // Skip the initial render - documents are loaded by the first useEffect
    if (!hasLoadedInitially.current) {
      return;
    }
    
    const fetchData = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        const params = new URLSearchParams({
          page: state.pagination.currentPage.toString(),
          per_page: state.pagination.itemsPerPage.toString(),
          ...(state.searchQuery && { search: state.searchQuery }),
        });
        
        const response = await fetch(`/api/documents?${params}`);
        if (!response.ok) {
          throw new Error('Failed to fetch documents');
        }

        const data = await response.json();
        const transformedData = {
          documents: data.documents.map(transformDocumentFromAPI).filter((doc: any) => doc !== null),
          pagination: {
            currentPage: data.pagination?.page || data.page || 1,
            itemsPerPage: data.pagination?.per_page || data.per_page || 10,
            totalItems: data.pagination?.total || data.total || 0,
            totalPages: data.pagination?.total_pages || data.total_pages || 1,
          }
        };
        dispatch({ type: 'SET_DOCUMENTS', payload: transformedData });
      } catch (error) {
        console.error('Failed to refresh documents:', error);
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };
    
    fetchData();
  }, [state.pagination.currentPage, state.pagination.itemsPerPage, state.searchQuery]);

  const getFilteredDocuments = (): DocumentMetadata[] => {
    // With server-side pagination/filtering, just return the current documents
    return state.documents || [];
  };

  const selectAllDocuments = () => {
    const allIds = getFilteredDocuments().map(doc => doc.fileId);
    dispatch({ type: 'SET_SELECTED_DOCUMENTS', payload: allIds });
  };

  const clearSelection = () => {
    dispatch({ type: 'SET_SELECTED_DOCUMENTS', payload: [] });
  };

  const setPage = (page: number) => {
    dispatch({ type: 'SET_PAGE', payload: page });
  };

  const setItemsPerPage = (itemsPerPage: number) => {
    dispatch({ type: 'SET_ITEMS_PER_PAGE', payload: itemsPerPage });
  };

  const contextValue: DocumentContextValue = {
    state,
    dispatch,
    uploadDocument,
    deleteDocument,
    refreshDocuments,
    getFilteredDocuments,
    selectAllDocuments,
    clearSelection,
    setPage,
    setItemsPerPage,
  };

  return (
    <DocumentContext.Provider value={contextValue}>
      {children}
    </DocumentContext.Provider>
  );
};

// Hook
export const useDocuments = (): DocumentContextValue => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocuments must be used within a DocumentProvider');
  }
  return context;
};