import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  inline?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading...',
  inline = false,
}) => {
  if (inline) {
    return (
      <div className="inline-spinner-container">
        <div className="spinner small" />
        {message && <span className="inline-spinner-text">{message}</span>}
      </div>
    );
  }

  return (
    <div className="loading-state-container">
      <div className="spinner" />
      {message && <p className="loading-state-message">{message}</p>}
    </div>
  );
};
