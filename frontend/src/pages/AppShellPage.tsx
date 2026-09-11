import React from 'react';
import { Store, ShoppingBag, CreditCard, ShieldCheck, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AppShellPage: React.FC = () => {
  const { user } = useAuth();

  const renderRolePreview = () => {
    switch (user?.role) {
      case 'shopkeeper':
        return (
          <div className="preview-card-group">
            <div className="preview-card">
              <div className="preview-icon-box">
                <Store size={22} className="preview-icon" />
              </div>
              <div className="preview-details">
                <h3>Shop Management & Offer Studio</h3>
                <p>Create discounts with AI parsing, manage active/paused lifecycles, and view real-time claim footfall.</p>
              </div>
            </div>
            <div className="preview-card">
              <div className="preview-icon-box">
                <Sparkles size={22} className="preview-icon" />
              </div>
              <div className="preview-details">
                <h3>Points Ledger & Monthly Reports</h3>
                <p>Preload platform points, track ledger deductions, and analyze peak footfall days.</p>
              </div>
            </div>
          </div>
        );

      case 'shopper':
        return (
          <div className="preview-card-group">
            <div className="preview-card">
              <div className="preview-icon-box">
                <ShoppingBag size={22} className="preview-icon" />
              </div>
              <div className="preview-details">
                <h3>Hyperlocal Marketplace</h3>
                <p>Browse nearby active discounts in Vijayawada, filtered by category and savings.</p>
              </div>
            </div>
            <div className="preview-card">
              <div className="preview-icon-box">
                <ShieldCheck size={22} className="preview-icon" />
              </div>
              <div className="preview-details">
                <h3>My Claim Wallet</h3>
                <p>Access cryptographic claim codes (NO-XXXXXX) with live validity countdowns for checkout.</p>
              </div>
            </div>
          </div>
        );

      case 'counter':
        return (
          <div className="preview-card-group">
            <div className="preview-card">
              <div className="preview-icon-box">
                <CreditCard size={22} className="preview-icon" />
              </div>
              <div className="preview-details">
                <h3>Instant Checkout Redemption</h3>
                <p>Validate customer claim codes, apply discount caps, and complete redemptions idempotently.</p>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="app-shell-page">
      <div className="shell-welcome-banner">
        <div className="welcome-tag">
          <Sparkles size={14} />
          <span>Phase 11 Foundation Active</span>
        </div>
        <h1 className="welcome-heading">Welcome, {user?.email}</h1>
        <p className="welcome-text">
          Authenticated successfully as a <strong className="role-highlight">{user?.role}</strong>. Frontend routing, API client, authentication tokens, and error handling are fully operational.
        </p>
      </div>

      <div className="phase-placeholder-box">
        <div className="placeholder-status-badge">
          <Clock size={16} />
          <span>Phase 12 Preview</span>
        </div>
        <h2 className="placeholder-title">Role-Based Dashboard Coming in Phase 12</h2>
        <p className="placeholder-description">
          The foundation layer is connected to the live FastAPI backend. In Phase 12, this view will be replaced by your dedicated <strong>{user?.role?.toUpperCase()}</strong> dashboard interface:
        </p>

        {renderRolePreview()}

        <div className="foundation-status-bar">
          <div className="status-item">
            <CheckCircle2 size={16} className="status-check" />
            <span>API Client Connected (`http://localhost:8000`)</span>
          </div>
          <div className="status-item">
            <CheckCircle2 size={16} className="status-check" />
            <span>JWT Bearer Authorization Active</span>
          </div>
          <div className="status-item">
            <CheckCircle2 size={16} className="status-check" />
            <span>State Synchronized (`/auth/me`)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
