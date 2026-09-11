import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  ShoppingBag,
  Search,
  Store,
  Tag,
  Clock,
  CheckCircle2,
  Sparkles,
  MapPin,
  AlertCircle,
  Percent,
  Banknote,
  ExternalLink,
} from 'lucide-react';
import { offersApi } from '../../api/offers';
import { claimsApi } from '../../api/claims';
import { Modal } from '../../components/Modal';
import { ClaimCodeBadge } from '../../components/ClaimCodeBadge';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { EmptyState } from '../../components/EmptyState';
import type { Claim, Offer } from '../../types';

export const ShopperBrowsePage: React.FC = () => {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCity, setSelectedCity] = useState('');

  // Claim state
  const [claimingOfferId, setClaimingOfferId] = useState<number | null>(null);
  const [claimSuccessData, setClaimSuccessData] = useState<{ offer: Offer; claim: Claim } | null>(null);
  const [selectedOfferDetail, setSelectedOfferDetail] = useState<Offer | null>(null);

  const fetchOffers = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await offersApi.getPublicOffers({
        search: searchTerm.trim() || undefined,
        city: selectedCity.trim() || undefined,
      });
      setOffers(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to load neighbourhood offers.');
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, selectedCity]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchOffers();
    }, 250);
    return () => clearTimeout(timer);
  }, [fetchOffers]);

  const handleClaim = async (offer: Offer, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setClaimingOfferId(offer.id);
    setErrorMessage(null);

    try {
      const claim = await claimsApi.claimOffer(offer.id);
      setClaimSuccessData({ offer, claim });
      setSelectedOfferDetail(null);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to claim offer. It may have expired or already been claimed.');
    } finally {
      setClaimingOfferId(null);
    }
  };

  const formatDiscount = (type: string, val: number) => {
    if (type === 'percentage') {
      return `${Math.round(val)}% OFF`;
    }
    return `₹${val.toFixed(0)} OFF`;
  };

  const formatExpiry = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="shopper-page">
      {/* Page Header */}
      <div className="page-header-banner">
        <div className="banner-content">
          <div className="banner-tag">
            <Sparkles size={14} />
            <span>Hyperlocal Marketplace</span>
          </div>
          <h1 className="page-title">Discover Neighbourhood Offers</h1>
          <p className="page-subtitle">
            Browse exclusive discounts from verified local shops in your area. Claim free codes and redeem instantly at checkout!
          </p>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="filters-bar">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search offers, groceries, clothing, electronics..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="filter-search-input"
          />
        </div>

        <div className="city-filter-wrapper">
          <MapPin size={16} className="city-icon" />
          <select
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value)}
            className="city-select"
            aria-label="Filter by City"
          >
            <option value="">All Locations</option>
            <option value="Vijayawada">Vijayawada</option>
          </select>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Offers Grid */}
      {isLoading ? (
        <LoadingSpinner message="Discovering live neighbourhood offers..." />
      ) : offers.length === 0 ? (
        <EmptyState
          icon={ShoppingBag}
          title="No active offers found"
          description={
            searchTerm || selectedCity
              ? 'Try adjusting your search query or location filter to find more deals.'
              : 'There are currently no active neighbourhood offers available. Check back soon!'
          }
          action={
            searchTerm || selectedCity
              ? {
                  label: 'Clear Filters',
                  onClick: () => {
                    setSearchTerm('');
                    setSelectedCity('');
                  },
                }
              : undefined
          }
        />
      ) : (
        <div className="offers-grid">
          {offers.map((offer) => (
            <div
              key={offer.id}
              className="offer-card"
              onClick={() => setSelectedOfferDetail(offer)}
            >
              <div className="offer-card-top">
                <div className="offer-shop-badge">
                  <Store size={14} />
                  <span>{offer.shop_name || 'Local Shop'}</span>
                </div>
                <div className="offer-discount-pill">
                  {offer.discount_type === 'percentage' ? (
                    <Percent size={14} />
                  ) : (
                    <Banknote size={14} />
                  )}
                  <span>{formatDiscount(offer.discount_type, offer.discount_value)}</span>
                </div>
              </div>

              <div className="offer-card-body">
                <h3 className="offer-title">{offer.title}</h3>
                {offer.description && (
                  <p className="offer-description">{offer.description}</p>
                )}
              </div>

              <div className="offer-card-meta">
                <div className="meta-item">
                  <Tag size={13} />
                  <span>
                    {offer.minimum_purchase
                      ? `Min. Bill: ₹${offer.minimum_purchase.toFixed(0)}`
                      : 'No Minimum Spend'}
                  </span>
                </div>
                <div className="meta-item">
                  <Clock size={13} />
                  <span>Expires {formatExpiry(offer.expires_at)}</span>
                </div>
              </div>

              <div className="offer-card-footer">
                <button
                  type="button"
                  onClick={(e) => handleClaim(offer, e)}
                  disabled={claimingOfferId === offer.id}
                  className="btn-primary btn-claim"
                >
                  {claimingOfferId === offer.id ? (
                    <>
                      <div className="btn-spinner" />
                      <span>Generating Code...</span>
                    </>
                  ) : (
                    <>
                      <Tag size={16} />
                      <span>Claim Free Offer</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Offer Detail Modal */}
      <Modal
        isOpen={Boolean(selectedOfferDetail)}
        onClose={() => setSelectedOfferDetail(null)}
        title="Offer Details & Terms"
      >
        {selectedOfferDetail && (
          <div className="offer-detail-modal-content">
            <div className="modal-discount-header">
              <div className="modal-discount-tag">
                {formatDiscount(
                  selectedOfferDetail.discount_type,
                  selectedOfferDetail.discount_value
                )}
              </div>
              <h2 className="modal-offer-title">{selectedOfferDetail.title}</h2>
            </div>

            <div className="detail-shop-info">
              <Store size={18} className="shop-info-icon" />
              <div>
                <strong>{selectedOfferDetail.shop_name || 'Local Shop'}</strong>
                <p className="shop-sub">Verified Neighbourhood Business</p>
              </div>
            </div>

            {selectedOfferDetail.description && (
              <div className="detail-section">
                <h4>Description</h4>
                <p>{selectedOfferDetail.description}</p>
              </div>
            )}

            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Minimum Purchase</span>
                <span className="detail-value">
                  {selectedOfferDetail.minimum_purchase
                    ? `₹${selectedOfferDetail.minimum_purchase.toFixed(2)}`
                    : 'None (Any Amount)'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Valid Until</span>
                <span className="detail-value">
                  {formatExpiry(selectedOfferDetail.expires_at)}
                </span>
              </div>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                onClick={() => handleClaim(selectedOfferDetail)}
                disabled={claimingOfferId === selectedOfferDetail.id}
                className="btn-primary btn-full"
              >
                {claimingOfferId === selectedOfferDetail.id ? (
                  <>
                    <div className="btn-spinner" />
                    <span>Claiming...</span>
                  </>
                ) : (
                  <>
                    <Tag size={18} />
                    <span>Claim This Offer</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Claim Success Celebration Modal */}
      <Modal
        isOpen={Boolean(claimSuccessData)}
        onClose={() => setClaimSuccessData(null)}
        title="🎉 Offer Claimed Successfully!"
        maxWidth="500px"
      >
        {claimSuccessData && (
          <div className="claim-success-modal-content">
            <div className="celebration-badge">
              <CheckCircle2 size={36} className="celebration-icon" />
            </div>

            <h3 className="success-heading">Your Exclusive Claim Code is Ready!</h3>
            <p className="success-sub">
              Present this code at <strong>{claimSuccessData.offer.shop_name || 'the shop'}</strong> counter during checkout to receive your discount.
            </p>

            {/* Prominent Claim Code Badge */}
            <div className="prominent-code-box">
              <ClaimCodeBadge code={claimSuccessData.claim.code} large />
            </div>

            <div className="claim-summary-card">
              <div className="summary-row">
                <span>Offer:</span>
                <strong>{claimSuccessData.offer.title}</strong>
              </div>
              <div className="summary-row">
                <span>Discount:</span>
                <strong className="text-highlight">
                  {formatDiscount(
                    claimSuccessData.offer.discount_type,
                    claimSuccessData.offer.discount_value
                  )}
                </strong>
              </div>
              <div className="summary-row">
                <span>Expires:</span>
                <span>{formatExpiry(claimSuccessData.claim.expires_at)}</span>
              </div>
            </div>

            <div className="modal-actions-dual">
              <button
                type="button"
                onClick={() => setClaimSuccessData(null)}
                className="btn-secondary"
              >
                Done
              </button>
              <Link
                to="/app/shopper/claims"
                className="btn-primary btn-link-action"
                onClick={() => setClaimSuccessData(null)}
              >
                <span>View in My Claims</span>
                <ExternalLink size={16} />
              </Link>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
