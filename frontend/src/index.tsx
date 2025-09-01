import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import './index.css';

// Cherry Studio inspired theme
const cherryTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#ff6b6b',
      light: '#ff8a80',
      dark: '#e53e3e'
    },
    secondary: {
      main: '#4ecdc4',
      light: '#80cbc4',
      dark: '#26a69a'
    },
    background: {
      default: '#1a1a1a',
      paper: '#262626'
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0'
    }
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", "Roboto", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
    }
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid #333',
        },
      },
    },
  },
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ThemeProvider theme={cherryTheme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);