import React, { useState } from 'react';
import { Copy, Check, Ticket } from 'lucide-react';

interface ClaimCodeBadgeProps {
  code: string;
  large?: boolean;
}

export const ClaimCodeBadge: React.FC<ClaimCodeBadgeProps> = ({ code, large = false }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code to clipboard', err);
    }
  };

  return (
    <div className={`claim-code-container ${large ? 'large' : ''}`}>
      <div className="claim-code-content">
        <Ticket size={large ? 22 : 16} className="claim-ticket-icon" />
        <span className="claim-code-text">{code}</span>
      </div>
      <button
        type="button"
        onClick={handleCopy}
        className={`claim-code-copy-btn ${copied ? 'copied' : ''}`}
        title="Copy claim code to clipboard"
        aria-label="Copy claim code"
      >
        {copied ? (
          <>
            <Check size={large ? 16 : 13} />
            <span className="copy-label">Copied!</span>
          </>
        ) : (
          <>
            <Copy size={large ? 16 : 13} />
            <span className="copy-label">Copy</span>
          </>
        )}
      </button>
    </div>
  );
};
