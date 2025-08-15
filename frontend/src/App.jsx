import { Routes, Route, Navigate } from 'react-router-dom';
// Components
import PrivateRoute from './components/PrivateRoute';
// Pages
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import SessionList from './pages/SessionList';
import SessionCreate from './pages/SessionCreate';

function App() {

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/session/list"
        element={
          <PrivateRoute>
            <SessionList />
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
  )
}

export default App
