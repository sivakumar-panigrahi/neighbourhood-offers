import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
}) => {
  return (
    <div className="empty-state-card">
      <div className="empty-state-icon-box">
        <Icon size={36} className="empty-state-icon" />
      </div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-description">{description}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="btn-primary empty-state-btn"
        >
          {action.icon && <action.icon size={16} />}
          <span>{action.label}</span>
        </button>
      )}
    </div>
  );
};
