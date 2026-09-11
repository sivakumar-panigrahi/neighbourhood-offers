import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Store } from 'lucide-react';

export const AuthLayout: React.FC = () => {
  return (
    <div className="auth-layout-container">
      <div className="auth-card-wrapper">
        <header className="auth-header">
          <Link to="/" className="auth-brand-logo">
            <div className="brand-icon-box">
              <Store size={26} className="brand-icon" />
            </div>
            <div className="brand-titles">
              <h1 className="brand-name">Neighbourhood Offers</h1>
              <span className="brand-tagline">Hyperlocal Discounts & Rewards</span>
            </div>
          </Link>
        </header>

        <main className="auth-main-content">
          <Outlet />
        </main>

        <footer className="auth-footer">
          <p>&copy; {new Date().getFullYear()} Neighbourhood Offers. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};
