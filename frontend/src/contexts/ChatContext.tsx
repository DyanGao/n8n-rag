import React, { createContext, useContext, useReducer, ReactNode, useEffect } from 'react';

// Types
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  metadata?: {
    workflow?: any;
    retrievedDocs?: string[];
    confidence?: number;
    processingTime?: number;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  lastActivity: Date;
  currentWorkflow?: any; // Store the generated workflow for this session
}

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isTyping: boolean;
  isGenerating: boolean;
  useKnowledgeBase: boolean;
  isCreatingSession: boolean;
}

// Actions
type ChatAction =
  | { type: 'SET_SESSIONS'; payload: ChatSession[] }
  | { type: 'ADD_SESSION'; payload: ChatSession }
  | { type: 'SET_ACTIVE_SESSION'; payload: string }
  | { type: 'ADD_MESSAGE'; payload: { sessionId: string; message: Message } }
  | { type: 'UPDATE_MESSAGE'; payload: { sessionId: string; messageId: string; updates: Partial<Message> } }
  | { type: 'UPDATE_SESSION_WORKFLOW'; payload: { sessionId: string; workflow: any } }
  | { type: 'UPDATE_SESSION_TITLE'; payload: { sessionId: string; title: string } }
  | { type: 'DELETE_SESSION'; payload: string }
  | { type: 'SET_TYPING'; payload: boolean }
  | { type: 'SET_GENERATING'; payload: boolean }
  | { type: 'SET_USE_KNOWLEDGE_BASE'; payload: boolean }
  | { type: 'SET_CREATING_SESSION'; payload: boolean }
  | { type: 'CLEAR_SESSIONS' };

// Initial state
const initialState: ChatState = {
  sessions: [],
  activeSessionId: null,
  isTyping: false,
  isGenerating: false,
  useKnowledgeBase: true,
  isCreatingSession: false,
};

// Reducer
const chatReducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case 'SET_SESSIONS':
      return {
        ...state,
        sessions: action.payload,
      };

    case 'ADD_SESSION':
      return {
        ...state,
        sessions: [action.payload, ...state.sessions],
        activeSessionId: action.payload.id,
      };

    case 'SET_ACTIVE_SESSION':
      return {
        ...state,
        activeSessionId: action.payload,
      };

    case 'ADD_MESSAGE':
      return {
        ...state,
        sessions: state.sessions.map(session =>
          session.id === action.payload.sessionId
            ? {
                ...session,
                messages: [...session.messages, action.payload.message],
                lastActivity: new Date(),
              }
            : session
        ),
      };

    case 'UPDATE_MESSAGE':
      return {
        ...state,
        sessions: state.sessions.map(session =>
          session.id === action.payload.sessionId
            ? {
                ...session,
                messages: session.messages.map(msg =>
                  msg.id === action.payload.messageId
                    ? { ...msg, ...action.payload.updates }
                    : msg
                ),
              }
            : session
        ),
      };

    case 'UPDATE_SESSION_WORKFLOW':
      return {
        ...state,
        sessions: state.sessions.map(session =>
          session.id === action.payload.sessionId
            ? {
                ...session,
                currentWorkflow: action.payload.workflow,
                lastActivity: new Date(),
              }
            : session
        ),
      };

    case 'UPDATE_SESSION_TITLE':
      return {
        ...state,
        sessions: state.sessions.map(session =>
          session.id === action.payload.sessionId
            ? {
                ...session,
                title: action.payload.title,
                lastActivity: new Date(),
              }
            : session
        ),
      };

    case 'DELETE_SESSION':
      const newSessions = state.sessions.filter(s => s.id !== action.payload);
      return {
        ...state,
        sessions: newSessions,
        activeSessionId: state.activeSessionId === action.payload 
          ? (newSessions[0]?.id || null)
          : state.activeSessionId,
      };

    case 'SET_TYPING':
      return {
        ...state,
        isTyping: action.payload,
      };

    case 'SET_GENERATING':
      return {
        ...state,
        isGenerating: action.payload,
      };

    case 'SET_USE_KNOWLEDGE_BASE':
      return {
        ...state,
        useKnowledgeBase: action.payload,
      };

    case 'CLEAR_SESSIONS':
      return {
        ...initialState,
      };

    default:
      return state;
  }
};

// Context
interface ChatContextValue {
  state: ChatState;
  dispatch: React.Dispatch<ChatAction>;
  
  // Helper functions
  createNewSession: (title?: string) => string;
  addMessage: (sessionId: string, content: string, role: Message['role'], metadata?: Message['metadata']) => void;
  getActiveSession: () => ChatSession | null;
  deleteSession: (sessionId: string) => void;
  setActiveSession: (sessionId: string) => void;
  updateSessionWorkflow: (sessionId: string, workflow: any) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

// Provider
interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  // Load sessions from localStorage on init
  const loadedState = (() => {
    try {
      const saved = localStorage.getItem('chatSessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          ...initialState,
          sessions: parsed.sessions.map((session: any) => ({
            ...session,
            createdAt: new Date(session.createdAt),
            lastActivity: new Date(session.lastActivity),
            messages: session.messages.map((msg: any) => ({
              ...msg,
              timestamp: new Date(msg.timestamp)
            }))
          })),
          activeSessionId: parsed.activeSessionId
        };
      }
    } catch (error) {
      console.warn('Failed to load chat sessions from localStorage:', error);
    }
    return initialState;
  })();

  const [state, dispatch] = useReducer(chatReducer, loadedState);

  // Save to localStorage whenever state changes
  useEffect(() => {
    try {
      localStorage.setItem('chatSessions', JSON.stringify({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId
      }));
    } catch (error) {
      console.warn('Failed to save chat sessions to localStorage:', error);
    }
  }, [state.sessions, state.activeSessionId]);

  const createNewSession = (title?: string): string => {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newSession: ChatSession = {
      id: sessionId,
      title: title || `Chat ${state.sessions.length + 1}`,
      messages: [],
      createdAt: new Date(),
      lastActivity: new Date(),
    };

    dispatch({ type: 'ADD_SESSION', payload: newSession });
    return sessionId;
  };

  const addMessage = (
    sessionId: string, 
    content: string, 
    role: Message['role'], 
    metadata?: Message['metadata']
  ) => {
    const message: Message = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content,
      role,
      timestamp: new Date(),
      metadata,
    };

    dispatch({ 
      type: 'ADD_MESSAGE', 
      payload: { sessionId, message } 
    });
  };

  const getActiveSession = (): ChatSession | null => {
    if (!state.activeSessionId) return null;
    return state.sessions.find(s => s.id === state.activeSessionId) || null;
  };

  const deleteSession = (sessionId: string) => {
    dispatch({ type: 'DELETE_SESSION', payload: sessionId });
  };

  const setActiveSession = (sessionId: string) => {
    dispatch({ type: 'SET_ACTIVE_SESSION', payload: sessionId });
  };

  const updateSessionWorkflow = (sessionId: string, workflow: any) => {
    dispatch({ type: 'UPDATE_SESSION_WORKFLOW', payload: { sessionId, workflow } });
  };

  const updateSessionTitle = (sessionId: string, title: string) => {
    dispatch({ type: 'UPDATE_SESSION_TITLE', payload: { sessionId, title } });
  };

  const contextValue: ChatContextValue = {
    state,
    dispatch,
    createNewSession,
    addMessage,
    getActiveSession,
    deleteSession,
    setActiveSession,
    updateSessionWorkflow,
    updateSessionTitle,
  };

  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  );
};

// Hook
export const useChat = (): ChatContextValue => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};