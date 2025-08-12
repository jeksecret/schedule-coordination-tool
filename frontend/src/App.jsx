import { Routes, Route, Navigate } from 'react-router-dom';
// Components
import PrivateRoute from './components/PrivateRoute';
// Pages
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import SessionCreate from "./pages/SessionCreate";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      <Route
        path="/session/create"
        element={
          <PrivateRoute>
            <SessionCreate />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
