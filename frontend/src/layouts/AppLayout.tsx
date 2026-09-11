import React from 'react';
import { Outlet, NavLink, Link, useNavigate } from 'react-router-dom';
import {
  Store,
  LogOut,
  User as UserIcon,
  Shield,
  ShoppingBag,
  Ticket,
  Sparkles,
  Coins,
  TrendingUp,
  Receipt,
  CreditCard,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case 'shopkeeper':
        return 'badge-shopkeeper';
      case 'shopper':
        return 'badge-shopper';
      case 'counter':
        return 'badge-counter';
      default:
        return 'badge-default';
    }
  };

  const renderNavLinks = () => {
    if (!user) return null;

    if (user.role === 'shopkeeper') {
      return (
        <nav className="nav-links-list">
          <NavLink
            to="/app/shopkeeper/dashboard"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <Store size={16} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink
            to="/app/shopkeeper/offers"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <ShoppingBag size={16} />
            <span>Offers</span>
          </NavLink>
          <NavLink
            to="/app/shopkeeper/ai-create"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <Sparkles size={16} className="text-highlight" />
            <span>AI Studio</span>
          </NavLink>
          <NavLink
            to="/app/shopkeeper/points"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <Coins size={16} />
            <span>Points</span>
          </NavLink>
          <NavLink
            to="/app/shopkeeper/reports"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <TrendingUp size={16} />
            <span>Reports</span>
          </NavLink>
          <NavLink
            to="/app/shopkeeper/redemptions"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <Receipt size={16} />
            <span>Redemptions</span>
          </NavLink>
        </nav>
      );
    }

    if (user.role === 'shopper') {
      return (
        <nav className="nav-links-list">
          <NavLink
            to="/app/shopper/discover"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <ShoppingBag size={16} />
            <span>Discover Deals</span>
          </NavLink>
          <NavLink
            to="/app/shopper/claims"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <Ticket size={16} />
            <span>My Claim Wallet</span>
          </NavLink>
          <NavLink
            to="/app/shopper/profile"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <UserIcon size={16} />
            <span>Profile & Sign Out</span>
          </NavLink>
        </nav>
      );
    }

    if (user.role === 'counter') {
      return (
        <nav className="nav-links-list">
          <NavLink
            to="/app/counter/redeem"
            className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
          >
            <CreditCard size={16} />
            <span>Redeem Checkout</span>
          </NavLink>
        </nav>
      );
    }

    return null;
  };

  const getHomeLink = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'shopkeeper':
        return '/app/shopkeeper/dashboard';
      case 'shopper':
        return '/app/shopper/discover';
      case 'counter':
        return '/app/counter/redeem';
      default:
        return '/app';
    }
  };

  const getUserDisplayName = () => {
    if (!user?.email) return 'Account';
    const prefix = user.email.split('@')[0];
    const name = prefix.split('.')[0];
    return name.charAt(0).toUpperCase() + name.slice(1);
  };

  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <header className="app-navbar">
        <div className="navbar-container">
          <div className="nav-left-cluster">
            <Link to={getHomeLink()} className="nav-brand">
              <div className="brand-icon-box small">
                <Store size={18} className="brand-icon" />
              </div>
              <span className="brand-title">Neighbourhood Offers</span>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="desktop-nav-menu">
              {renderNavLinks()}
            </div>
          </div>

          <div className="nav-actions">
            {user && (
              <Link
                to={user.role === 'shopper' ? '/app/shopper/profile' : getHomeLink()}
                className="user-profile-badge profile-clickable"
                title={`${user.email} (${user.role})`}
              >
                <div className="user-icon-circle">
                  <UserIcon size={14} />
                </div>
                <div className="user-info-text">
                  <span className="user-email">{getUserDisplayName()}</span>
                  <span className={`role-pill ${getRoleBadgeClass(user.role)}`}>
                    <Shield size={10} className="role-icon" />
                    {user.role}
                  </span>
                </div>
              </Link>
            )}

            <button
              onClick={handleLogout}
              className="btn-logout"
              title="Sign Out of Session"
              aria-label="Sign Out"
            >
              <LogOut size={15} />
              <span className="btn-logout-label">Sign Out</span>
            </button>
          </div>
        </div>

        {/* Mobile Sub-Navbar for Navigation Links */}
        <div className="mobile-nav-subbar">
          {renderNavLinks()}
        </div>
      </header>

      {/* Main Page Area */}
      <main className="app-main">
        <div className="app-content-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
