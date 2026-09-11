import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LogIn,
  AlertCircle,
  Sparkles,
  Eye,
  EyeOff,
  Store,
  ShoppingBag,
  CreditCard,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface RolePortal {
  role: 'shopkeeper' | 'shopper' | 'counter';
  title: string;
  badge: string;
  badgeClass: string;
  icon: React.ElementType;
  description: string;
  features: string[];
  primaryUser: { name: string; email: string };
  secondaryUser: { name: string; email: string };
}

const ROLE_PORTALS: RolePortal[] = [
  {
    role: 'shopkeeper',
    title: 'Shopkeeper Portal',
    badge: 'Merchant Admin',
    badgeClass: 'badge-shopkeeper',
    icon: Store,
    description: 'Create & publish discounts with AI NLP Studio, manage points ledger, and view sales reports.',
    features: ['AI Offer Studio', 'Points Preload', 'Footfall Analytics'],
    primaryUser: { name: 'Anitha (Grocery)', email: 'anitha.demo@example.com' },
    secondaryUser: { name: 'Rahul (Fashion)', email: 'rahul.demo@example.com' },
  },
  {
    role: 'shopper',
    title: 'Shopper Marketplace',
    badge: 'Customer View',
    badgeClass: 'badge-shopper',
    icon: ShoppingBag,
    description: 'Browse hyperlocal neighbourhood discounts, claim instant promo codes, and manage claim wallet.',
    features: ['Hyperlocal Deals', '1-Click Claim', 'QR & Claim Wallet'],
    primaryUser: { name: 'Priya', email: 'priya.demo@example.com' },
    secondaryUser: { name: 'Arjun', email: 'arjun.demo@example.com' },
  },
  {
    role: 'counter',
    title: 'Counter Staff Terminal',
    badge: 'Cashier POS',
    badgeClass: 'badge-counter',
    icon: CreditCard,
    description: 'Instant checkout redemption by claim code, idempotency validation, and automatic points deduction.',
    features: ['Fast Code Lookup', 'Auto Bill Discount', 'Points Deduction'],
    primaryUser: { name: 'Ravi', email: 'ravi.demo@example.com' },
    secondaryUser: { name: 'Meena', email: 'meena.demo@example.com' },
  },
];

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeQuickRole, setActiveQuickRole] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/app';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setErrorMessage(err.message || 'Incorrect email or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInstantAccess = async (targetEmail: string, roleName: string) => {
    setErrorMessage(null);
    setIsSubmitting(true);
    setActiveQuickRole(roleName);
    setEmail(targetEmail);
    setPassword('DemoPassword123!');

    try {
      await login(targetEmail, 'DemoPassword123!');
      navigate(from, { replace: true });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to authenticate user account.');
      setIsSubmitting(false);
      setActiveQuickRole(null);
    }
  };

  const handleSelectFill = (targetEmail: string) => {
    setEmail(targetEmail);
    setPassword('DemoPassword123!');
    setErrorMessage(null);
  };

  return (
    <div className="login-experience-container">
      {/* Enterprise Multi-Role Header */}
      <div className="demo-showcase-banner">
        <div className="showcase-banner-top">
          <div className="showcase-tag">
            <Sparkles size={14} />
            <span>Enterprise Multi-Role Portals</span>
          </div>
        </div>
        <h2 className="showcase-heading">Instant Role Access</h2>
        <p className="showcase-sub">
          Access pre-provisioned role accounts with one click, or sign in with your custom credentials below.
        </p>
      </div>

      {/* 3-Role Cards Grid */}
      <div className="role-demo-cards-grid">
        {ROLE_PORTALS.map((portal) => {
          const IconComponent = portal.icon;
          const isCurrentLoggingIn = isSubmitting && activeQuickRole === portal.role;

          return (
            <div key={portal.role} className={`role-demo-card card-${portal.role}`}>
              <div className="card-top-header">
                <div className={`role-icon-box box-${portal.role}`}>
                  <IconComponent size={22} />
                </div>
                <span className={`role-pill ${portal.badgeClass}`}>
                  {portal.badge}
                </span>
              </div>

              <h3 className="role-card-title">{portal.title}</h3>
              <p className="role-card-desc">{portal.description}</p>

              <div className="role-card-features">
                {portal.features.map((feat, idx) => (
                  <span key={idx} className="feat-chip">
                    ✓ {feat}
                  </span>
                ))}
              </div>

              <div className="role-card-actions">
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleInstantAccess(portal.primaryUser.email, portal.role)}
                  className={`btn-instant-login btn-${portal.role}`}
                >
                  {isCurrentLoggingIn ? (
                    <>
                      <div className="btn-spinner small" />
                      <span>Entering Portal...</span>
                    </>
                  ) : (
                    <>
                      <Zap size={14} />
                      <span>Instant Access: {portal.primaryUser.name}</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>

                <div className="secondary-user-row">
                  <span className="alt-label">Alt Account:</span>
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => handleSelectFill(portal.secondaryUser.email)}
                    className="btn-alt-fill"
                    title={`Fill ${portal.secondaryUser.email}`}
                  >
                    {portal.secondaryUser.name}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Standard Form */}
      <div className="auth-form-card">
        <div className="auth-form-header">
          <h3 className="auth-title">Or Sign In with Custom Credentials</h3>
          <p className="auth-subtitle">Pre-configured accounts password: <code>DemoPassword123!</code></p>
        </div>

        {errorMessage && (
          <div className="alert-box alert-error" role="alert">
            <AlertCircle size={18} className="alert-icon" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
              disabled={isSubmitting}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="password">Password</label>
              <button
                type="button"
                className="btn-toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                <span>{showPassword ? 'Hide' : 'Show'}</span>
              </button>
            </div>
            <div className="password-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                disabled={isSubmitting}
                className="form-input password-input"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary btn-full"
          >
            {isSubmitting && !activeQuickRole ? (
              <>
                <div className="btn-spinner" />
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <LogIn size={18} />
                <span>Sign In with Form</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-switch-link">
          Don't have an account? <Link to="/register">Create an Account (Shopper or Shopkeeper)</Link>
        </div>
      </div>
    </div>
  );
};
