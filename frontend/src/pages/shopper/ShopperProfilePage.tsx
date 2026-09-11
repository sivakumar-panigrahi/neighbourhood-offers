import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  User,
  LogOut,
  ShoppingBag,
  Ticket,
  ShieldCheck,
  MapPin,
  Clock,
  Sparkles,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { claimsApi } from '../../api/claims';
import type { Claim } from '../../types';

export const ShopperProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [claims, setClaims] = useState<Claim[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    claimsApi
      .getMyClaims()
      .then((data) => {
        if (isMounted) setClaims(data);
      })
      .catch(() => {
        // Fallback silently
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const activeClaimsCount = claims.filter((c) => c.status === 'claimed').length;
  const redeemedClaimsCount = claims.filter((c) => c.status === 'redeemed').length;

  const getUserDisplayName = () => {
    if (!user?.email) return 'Shopper';
    const prefix = user.email.split('@')[0];
    const name = prefix.split('.')[0];
    return name.charAt(0).toUpperCase() + name.slice(1);
  };

  return (
    <div className="shopper-profile-page">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Shopper Account & Profile</h1>
          <p className="page-subtitle">
            Manage your personal profile, active discount wallet, and account settings.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="btn-danger-logout"
          title="Sign Out of Shopper Account"
          aria-label="Sign Out"
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Main Profile Card */}
      <div className="profile-hero-card">
        <div className="profile-hero-left">
          <div className="profile-avatar-box">
            <User size={36} className="profile-avatar-icon" />
            <div className="avatar-status-dot" />
          </div>
          <div className="profile-hero-info">
            <div className="profile-name-row">
              <h2 className="profile-user-name">{getUserDisplayName()}</h2>
              <span className="role-pill badge-shopper">
                <ShieldCheck size={12} />
                Shopper
              </span>
            </div>
            <p className="profile-user-email">{user?.email}</p>
            <div className="profile-meta-tags">
              <span className="meta-tag">
                <MapPin size={13} />
                Vijayawada Region
              </span>
              <span className="meta-tag">
                <CheckCircle2 size={13} />
                Verified Customer
              </span>
            </div>
          </div>
        </div>

        <div className="profile-hero-actions">
          <button
            type="button"
            onClick={handleLogout}
            className="btn-primary-logout"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Stats Summary Grid */}
      <div className="profile-stats-grid">
        <div className="profile-stat-card">
          <div className="stat-card-icon-box bg-purple">
            <Ticket size={20} />
          </div>
          <div className="stat-card-body">
            <span className="stat-card-label">Total Claims</span>
            <strong className="stat-card-val">
              {isLoading ? '...' : claims.length}
            </strong>
            <span className="stat-card-sub">All-time promotional claims</span>
          </div>
        </div>

        <div className="profile-stat-card">
          <div className="stat-card-icon-box bg-emerald">
            <Clock size={20} />
          </div>
          <div className="stat-card-body">
            <span className="stat-card-label">Active Wallet Codes</span>
            <strong className="stat-card-val text-success">
              {isLoading ? '...' : activeClaimsCount}
            </strong>
            <span className="stat-card-sub">Ready for store checkout</span>
          </div>
        </div>

        <div className="profile-stat-card">
          <div className="stat-card-icon-box bg-blue">
            <CheckCircle2 size={20} />
          </div>
          <div className="stat-card-body">
            <span className="stat-card-label">Completed Savings</span>
            <strong className="stat-card-val">
              {isLoading ? '...' : redeemedClaimsCount}
            </strong>
            <span className="stat-card-sub">Discounts redeemed at counters</span>
          </div>
        </div>
      </div>

      {/* Quick Links & Presentation Showcase */}
      <div className="profile-sections-grid">
        {/* Navigation Quick Links */}
        <div className="profile-content-card">
          <h3 className="profile-card-title">Quick Actions</h3>
          <p className="profile-card-desc">
            Jump to your shopper discovery tools and claim wallet.
          </p>

          <div className="quick-actions-list">
            <Link to="/app/shopper/discover" className="quick-action-row">
              <div className="quick-action-icon bg-indigo">
                <ShoppingBag size={18} />
              </div>
              <div className="quick-action-text">
                <strong>Discover Local Deals</strong>
                <span>Browse discounts and promotions from nearby shops</span>
              </div>
              <ExternalLink size={16} className="quick-action-arrow" />
            </Link>

            <Link to="/app/shopper/claims" className="quick-action-row">
              <div className="quick-action-icon bg-emerald">
                <Ticket size={18} />
              </div>
              <div className="quick-action-text">
                <strong>My Claim Wallet</strong>
                <span>View your active QR codes and countdown timers for checkout</span>
              </div>
              <ExternalLink size={16} className="quick-action-arrow" />
            </Link>
          </div>
        </div>

        {/* Enterprise Role Switcher Hub */}
        <div className="profile-content-card highlight-border">
          <div className="card-header-with-badge">
            <h3 className="profile-card-title">Enterprise Role Switcher</h3>
            <span className="presentation-badge">
              <Sparkles size={12} />
              Live Portals
            </span>
          </div>
          <p className="profile-card-desc">
            You are currently signed in as a <strong>Shopper</strong>. To explore or switch to the other operational roles:
          </p>

          <div className="role-demo-guide-list">
            <div className="guide-item">
              <strong>1. Sign Out:</strong> Click <em>Sign Out</em> to access the role selection portal.
            </div>
            <div className="guide-item">
              <strong>2. Shopkeeper Portal:</strong> Access <em>Anitha's Grocery</em> or <em>Rahul's Fashion</em> to manage the AI discount studio, points ledger, and footfall analytics.
            </div>
            <div className="guide-item">
              <strong>3. Counter Staff POS:</strong> Access <em>Ravi</em> or <em>Meena</em> to process instant checkout redemptions and bill discount calculations.
            </div>
          </div>

          <div className="signout-highlight-box">
            <button
              type="button"
              onClick={handleLogout}
              className="btn-danger-full-logout"
            >
              <LogOut size={16} />
              <span>Sign Out & Switch Role</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
