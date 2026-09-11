import React from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle, Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="not-found-container">
      <div className="not-found-card">
        <div className="not-found-icon-box">
          <HelpCircle size={48} className="not-found-icon" />
        </div>
        <h1 className="not-found-code">404</h1>
        <h2 className="not-found-title">Page Not Found</h2>
        <p className="not-found-text">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link to="/app" className="btn-primary">
          <Home size={18} />
          <span>Return Home</span>
        </Link>
      </div>
    </div>
  );
};
