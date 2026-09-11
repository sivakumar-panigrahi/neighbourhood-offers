import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus, AlertCircle, Store, ShoppingBag } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { UserRole } from '../types';

export const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('shopper');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please fill in all fields.');
      return;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await register(email.trim(), password, role);
      navigate('/app', { replace: true });
    } catch (err: any) {
      setErrorMessage(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-form-card">
      <div className="auth-form-header">
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Join the neighbourhood discounts network</p>
      </div>

      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="reg-email">Email Address</label>
          <input
            id="reg-email"
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
          <label htmlFor="reg-password">Password (min 6 characters)</label>
          <input
            id="reg-password"
            type="password"
            placeholder="Create a strong password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            autoComplete="new-password"
            disabled={isSubmitting}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label>Select Account Type</label>
          <div className="role-selector-grid dual-roles">
            <label className={`role-card ${role === 'shopper' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="role"
                value="shopper"
                checked={role === 'shopper'}
                onChange={() => setRole('shopper')}
                disabled={isSubmitting}
              />
              <div className="role-card-content">
                <ShoppingBag size={22} className="role-card-icon" />
                <span className="role-name">Shopper</span>
                <span className="role-desc">Discover & claim local deals</span>
              </div>
            </label>

            <label className={`role-card ${role === 'shopkeeper' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="role"
                value="shopkeeper"
                checked={role === 'shopkeeper'}
                onChange={() => setRole('shopkeeper')}
                disabled={isSubmitting}
              />
              <div className="role-card-content">
                <Store size={22} className="role-card-icon" />
                <span className="role-name">Shopkeeper</span>
                <span className="role-desc">Create offers & manage store points</span>
              </div>
            </label>
          </div>
          <span className="counter-staff-note">
            ℹ️ Counter Staff (Cashier POS) accounts are provisioned internally by merchant store administrators.
          </span>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary btn-full"
        >
          {isSubmitting ? (
            <>
              <div className="btn-spinner" />
              <span>Creating Account...</span>
            </>
          ) : (
            <>
              <UserPlus size={18} />
              <span>Register Account</span>
            </>
          )}
        </button>
      </form>

      <div className="auth-switch-link">
        Already have an account? <Link to="/login">Sign In</Link>
      </div>
    </div>
  );
};
