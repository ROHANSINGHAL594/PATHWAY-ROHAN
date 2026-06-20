//TODO: Add the use notification hook for the
//TODO: net ni chal rha to sed
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import ProtectedRoute from "./pages/ProtectedRoute";
import AdminProtectedRoute from "./pages/AdminProtectedRoute";
import LoginPage from "./pages/Login.jsx";
import SignupPage from "./pages/Signup.jsx";
import WorkflowPage from "./pages/Workflows.jsx";
import Sidebar from "./components/common/sidebar.jsx";
import OverviewPage from "./pages/Overview.jsx";
import { AdminPage } from "./pages/Admin.jsx";
import { WorkflowsList } from "./pages/WorkflowsList.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import NotificationToast from "./components/common/NotificationToast.jsx";

function AppContent() {
  const location = useLocation();
  const isPublicRoute = ["/", "/login", "/signup", "/404"];

  return (
    <>
      {!isPublicRoute.includes(location.pathname) && <Sidebar />}
      {/* Global notification toast for logs, notifications, and alerts */}
      {!isPublicRoute.includes(location.pathname) && <NotificationToast />}
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/" element={<Navigate to="/overview" />} />
        <Route path="/404" element={<NotFoundPage />} />

        {/* Protected routes */}
        <Route
          path="/workflows"
          element={
            <ProtectedRoute>
              <WorkflowsList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/workflows/:pipelineId"
          element={
            <ProtectedRoute>
              <WorkflowPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/overview"
          element={
            <ProtectedRoute>
              <OverviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <AdminProtectedRoute>
              <AdminPage />
            </AdminProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/404" />} />
      </Routes>
    </>
  );
}

export default function App() {
  return <AppContent />;
}
