import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { UserRole } from '../types';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
  children?: React.ReactNode;
}

export const getRoleHomePath = (role?: UserRole): string => {
  switch (role) {
    case 'shopkeeper':
      return '/app/shopkeeper/dashboard';
    case 'shopper':
      return '/app/shopper/discover';
    case 'counter':
      return '/app/counter/redeem';
    default:
      return '/login';
  }
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading application...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to user's dedicated dashboard
    return <Navigate to={getRoleHomePath(user.role)} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};
