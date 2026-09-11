import React, { useEffect, useState, useCallback } from 'react';
import {
  Ticket,
  Clock,
  CheckCircle2,
  AlertCircle,
  ShoppingBag,
  Store,
  RefreshCw,
  Percent,
  Banknote,
} from 'lucide-react';
import { claimsApi } from '../../api/claims';
import { ClaimCodeBadge } from '../../components/ClaimCodeBadge';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { EmptyState } from '../../components/EmptyState';
import type { Claim } from '../../types';

export const ShopperClaimsPage: React.FC = () => {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'claimed' | 'redeemed' | 'expired'>('all');

  const fetchClaims = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const statusParam = activeTab === 'all' ? undefined : activeTab;
      const data = await claimsApi.getMyClaims(statusParam);
      setClaims(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to load your claims.');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'claimed':
        return (
          <span className="status-pill pill-claimed">
            <Clock size={12} />
            <span>Ready for Checkout</span>
          </span>
        );
      case 'redeemed':
        return (
          <span className="status-pill pill-redeemed">
            <CheckCircle2 size={12} />
            <span>Redeemed</span>
          </span>
        );
      case 'expired':
        return (
          <span className="status-pill pill-expired">
            <AlertCircle size={12} />
            <span>Expired</span>
          </span>
        );
      default:
        return <span className="status-pill pill-default">{status}</span>;
    }
  };

  const formatDiscount = (type?: string, val?: number) => {
    if (!type || val === undefined) return '';
    if (type === 'percentage') {
      return `${Math.round(val)}% OFF`;
    }
    return `₹${val.toFixed(0)} OFF`;
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="shopper-claims-page">
      {/* Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">My Claim Wallet</h1>
          <p className="page-subtitle">
            Manage your claimed discount codes and redeem them at participating neighbourhood counters.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchClaims}
          disabled={isLoading}
          className="btn-refresh"
          title="Refresh Claims"
        >
          <RefreshCw size={16} className={isLoading ? 'spin-icon' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <button
          type="button"
          onClick={() => setActiveTab('all')}
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          All Claims
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('claimed')}
          className={`tab-btn ${activeTab === 'claimed' ? 'active' : ''}`}
        >
          Active / Ready
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('redeemed')}
          className={`tab-btn ${activeTab === 'redeemed' ? 'active' : ''}`}
        >
          Redeemed
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('expired')}
          className={`tab-btn ${activeTab === 'expired' ? 'active' : ''}`}
        >
          Expired
        </button>
      </div>

      {/* Error State */}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Claims List */}
      {isLoading ? (
        <LoadingSpinner message="Fetching your claim wallet..." />
      ) : claims.length === 0 ? (
        <EmptyState
          icon={Ticket}
          title={
            activeTab === 'all'
              ? "You haven't claimed any offers yet"
              : `No ${activeTab} claims found`
          }
          description="Browse the neighbourhood marketplace and claim free discount codes to start saving at your local shops."
          action={{
            label: 'Discover Offers',
            icon: ShoppingBag,
            onClick: () => {
              window.location.href = '/app/shopper/discover';
            },
          }}
        />
      ) : (
        <div className="claims-list-grid">
          {claims.map((claim) => (
            <div key={claim.id} className={`claim-card card-status-${claim.status}`}>
              <div className="claim-card-header">
                <div className="claim-shop-info">
                  <Store size={15} />
                  <span>{claim.shop?.name || claim.offer?.shop_name || 'Neighbourhood Shop'}</span>
                </div>
                {getStatusBadge(claim.status)}
              </div>

              <div className="claim-card-body">
                <h3 className="claim-offer-title">
                  {claim.offer?.title || 'Neighbourhood Discount Offer'}
                </h3>
                {claim.offer && (
                  <div className="claim-discount-inline">
                    {claim.offer.discount_type === 'percentage' ? (
                      <Percent size={14} />
                    ) : (
                      <Banknote size={14} />
                    )}
                    <span>
                      {formatDiscount(
                        claim.offer.discount_type,
                        claim.offer.discount_value
                      )}
                    </span>
                    {claim.offer.minimum_purchase && (
                      <span className="claim-min-spend">
                        (Min. Bill: ₹{claim.offer.minimum_purchase.toFixed(0)})
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Code Box */}
              <div className="claim-card-code-section">
                <span className="code-instruction-label">Show this code at counter:</span>
                <ClaimCodeBadge code={claim.code} large={claim.status === 'claimed'} />
              </div>

              {/* Dates & Timeline */}
              <div className="claim-card-footer">
                <div className="claim-meta-text">
                  <span>Claimed: {formatDate(claim.claimed_at)}</span>
                  <span>
                    {claim.status === 'redeemed'
                      ? '✓ Used at checkout'
                      : `Expires: ${formatDate(claim.expires_at)}`}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
