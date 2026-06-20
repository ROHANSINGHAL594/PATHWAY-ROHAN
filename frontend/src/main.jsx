import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n' 
import App from './App.jsx'
import { GlobalContextProvider } from "./context/GlobalContext.jsx";
import { GlobalWorkflowProvider } from "./context/GlobalWorkflowContext.jsx";
import { GlobalStateProvider } from "./context/GlobalStateContext.jsx";
import { ReactFlowProvider } from "@xyflow/react";
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import { WebSocketProvider } from './context/WebSocketContext.jsx'
import SettingsProvider from './providers/SettingsProvider.jsx';
import ThemeProvider from './providers/ThemeProvider.jsx';
import MobileViewBlocker from "./components/common/MobileViewBlocker.jsx";


const container = document.getElementById("root");

const root = createRoot(container);
root.render(
    <SettingsProvider>
      <ThemeProvider>
        <ReactFlowProvider>
          <BrowserRouter>
            <AuthProvider>
              <WebSocketProvider>
                <GlobalStateProvider>
                  <GlobalWorkflowProvider>
              <GlobalContextProvider>
                <MobileViewBlocker>
                  <App />
                </MobileViewBlocker>
              </GlobalContextProvider>
                  </GlobalWorkflowProvider>
                </GlobalStateProvider>
              </WebSocketProvider>
            </AuthProvider>
          </BrowserRouter>
        </ReactFlowProvider>
      </ThemeProvider>
    </SettingsProvider>
);
