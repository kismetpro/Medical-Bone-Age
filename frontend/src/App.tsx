import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import type { AuthRole } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import Home from './pages/Home';
import Auth from './pages/Auth';
import UserDashboard from './pages/UserDashboard';
import DoctorDashboard from './pages/DoctorDashboard';
import Community from './pages/Community';
import Consultation from './pages/Consultation';
import AiPet from './components/AiPet'; // 导入新组件
import './App.css';

const ProtectedRoute = ({
  children,
  allowedRoles,
}: {
  children: ReactNode;
  allowedRoles?: AuthRole[];
}) => {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated || !role) {
    return <Navigate to="/auth" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    if (role === 'doctor' || role === 'super_admin') {
      return <Navigate to="/doctor-dashboard" replace />;
    }
    if (role === 'user') {
      return <Navigate to="/user-dashboard" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="app-main-layout">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auth" element={<Auth />} />
        <Route
          path="/user-dashboard"
          element={(
            <ProtectedRoute allowedRoles={['user']}>
              <UserDashboard />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/doctor-dashboard"
          element={(
            <ProtectedRoute allowedRoles={['doctor', 'super_admin']}>
              <DoctorDashboard />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/consultation"
          element={(
            <ProtectedRoute allowedRoles={['user', 'doctor', 'super_admin']}>
              <Consultation />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/community"
          element={(
            <ProtectedRoute allowedRoles={['user', 'doctor', 'super_admin']}>
              <Community />
            </ProtectedRoute>
          )}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* 在路由外侧挂载 AI 小精灵，使其在所有页面保持存在 */}
      <AiPet />
    </div>
  );
}

export default App;