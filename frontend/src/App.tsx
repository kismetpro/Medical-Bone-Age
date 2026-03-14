// import { Routes, Route, Navigate } from 'react-router-dom';
// import type { ReactNode } from 'react';
// import { useAuth } from './context/AuthContext';
// import Home from './pages/Home';
// import Auth from './pages/Auth';
// import UserDashboard from './pages/UserDashboard';
// import DoctorDashboard from './pages/DoctorDashboard';
// import './App.css';

// // Protected Route Component
// const ProtectedRoute = ({ children, allowedRoles }: { children: ReactNode; allowedRoles?: string[] }) => {
//   const { isAuthenticated, role } = useAuth();

//   if (!isAuthenticated) {
//     return <Navigate to="/auth" replace />;
//   }

//   if (allowedRoles && role && !allowedRoles.includes(role)) {
//     // Redirect based on current role if trying to access unauthorized route
//     if (role === 'admin') return <Navigate to="/doctor-dashboard" replace />;
//     if (role === 'user') return <Navigate to="/user-dashboard" replace />;
//     return <Navigate to="/" replace />;
//   }

//   return children;
// };

// function App() {
//   return (
//     <div className="app-main-layout">
//       <Routes>
//         <Route path="/" element={<Home />} />
//         <Route path="/auth" element={<Auth />} />

//         {/* User Route */}
//         <Route
//           path="/user-dashboard"
//           element={
//             <ProtectedRoute allowedRoles={['user']}>
//               <UserDashboard />
//             </ProtectedRoute>
//           }
//         />

//         {/* Doctor Route */}
//         <Route
//           path="/doctor-dashboard"
//           element={
//             <ProtectedRoute allowedRoles={['admin']}>
//               <DoctorDashboard />
//             </ProtectedRoute>
//           }
//         />

//         {/* Catch all */}
//         <Route path="*" element={<Navigate to="/" replace />} />
//       </Routes>
//     </div>
//   );
// }

// export default App;
import { Routes, Route, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from './context/AuthContext';
import Home from './pages/Home';
import Auth from './pages/Auth';
import UserDashboard from './pages/UserDashboard';
import DoctorDashboard from './pages/DoctorDashboard';
import AiPet from './components/AiPet'; // 导入新组件
import './App.css';

const ProtectedRoute = ({ children, allowedRoles }: { children: ReactNode; allowedRoles?: string[] }) => {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    if (role === 'admin') return <Navigate to="/doctor-dashboard" replace />;
    if (role === 'user') return <Navigate to="/user-dashboard" replace />;
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="app-main-layout">
      {/* 1. 路由配置 */}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auth" element={<Auth />} />

        <Route
          path="/user-dashboard"
          element={
            <ProtectedRoute allowedRoles={['user']}>
              <UserDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/doctor-dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <DoctorDashboard />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* 2. 在路由外侧挂载 AI 小精灵，使其在所有页面保持存在 */}
      <AiPet />
    </div>
  );
}

export default App;