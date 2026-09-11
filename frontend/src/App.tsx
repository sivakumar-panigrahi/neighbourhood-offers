import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AuthLayout } from './layouts/AuthLayout';
import { AppLayout } from './layouts/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProtectedRoute, getRoleHomePath } from './routes/ProtectedRoute';

// Shopper Pages
import { ShopperBrowsePage } from './pages/shopper/ShopperBrowsePage';
import { ShopperClaimsPage } from './pages/shopper/ShopperClaimsPage';
import { ShopperProfilePage } from './pages/shopper/ShopperProfilePage';

// Shopkeeper Pages
import { ShopkeeperDashboardPage } from './pages/shopkeeper/ShopkeeperDashboardPage';
import { ShopkeeperOffersPage } from './pages/shopkeeper/ShopkeeperOffersPage';
import { ShopkeeperAICreatePage } from './pages/shopkeeper/ShopkeeperAICreatePage';
import { ShopkeeperPointsPage } from './pages/shopkeeper/ShopkeeperPointsPage';
import { ShopkeeperReportsPage } from './pages/shopkeeper/ShopkeeperReportsPage';
import { ShopkeeperRedemptionsPage } from './pages/shopkeeper/ShopkeeperRedemptionsPage';

// Counter Staff Pages
import { CounterRedeemPage } from './pages/counter/CounterRedeemPage';

import { LandingPage } from './pages/LandingPage';

const RootRedirect: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading application...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getRoleHomePath(user.role)} replace />;
};

const PublicOnlyRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading application...</p>
      </div>
    );
  }

  if (isAuthenticated && user) {
    return <Navigate to={getRoleHomePath(user.role)} replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Product Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Public Auth Routes */}
          <Route
            element={
              <PublicOnlyRoute>
                <AuthLayout />
              </PublicOnlyRoute>
            }
          >
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Authenticated Role-Based Routes */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            {/* /app default index -> redirect to role home */}
            <Route index element={<RootRedirect />} />

            {/* Shopper Sub-Routes */}
            <Route
              path="shopper"
              element={<ProtectedRoute allowedRoles={['shopper']} />}
            >
              <Route index element={<Navigate to="discover" replace />} />
              <Route path="discover" element={<ShopperBrowsePage />} />
              <Route path="claims" element={<ShopperClaimsPage />} />
              <Route path="profile" element={<ShopperProfilePage />} />
            </Route>

            {/* Shopkeeper Sub-Routes */}
            <Route
              path="shopkeeper"
              element={<ProtectedRoute allowedRoles={['shopkeeper']} />}
            >
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<ShopkeeperDashboardPage />} />
              <Route path="offers" element={<ShopkeeperOffersPage />} />
              <Route path="ai-create" element={<ShopkeeperAICreatePage />} />
              <Route path="points" element={<ShopkeeperPointsPage />} />
              <Route path="reports" element={<ShopkeeperReportsPage />} />
              <Route path="redemptions" element={<ShopkeeperRedemptionsPage />} />
            </Route>

            {/* Counter Staff Sub-Routes */}
            <Route
              path="counter"
              element={<ProtectedRoute allowedRoles={['counter']} />}
            >
              <Route index element={<Navigate to="redeem" replace />} />
              <Route path="redeem" element={<CounterRedeemPage />} />
            </Route>
          </Route>

          {/* Fallback 404 Route */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
