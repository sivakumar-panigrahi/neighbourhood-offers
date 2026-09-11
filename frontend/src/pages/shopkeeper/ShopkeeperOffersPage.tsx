import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Tag,
  Plus,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Clock,
  CheckCircle2,
  AlertCircle,
  Percent,
  Banknote,
} from 'lucide-react';
import { offersApi } from '../../api/offers';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { Modal } from '../../components/Modal';
import { EmptyState } from '../../components/EmptyState';
import type { DiscountType, Offer, OfferCreateRequest, OfferStatus } from '../../types';

export const ShopkeeperOffersPage: React.FC = () => {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Manual Create Offer Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [discountType, setDiscountType] = useState<DiscountType>('percentage');
  const [discountValue, setDiscountValue] = useState<number>(10);
  const [minimumPurchase, setMinimumPurchase] = useState<string>('500');
  const [startsAt, setStartsAt] = useState<string>(() => {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  const [expiresAt, setExpiresAt] = useState<string>(() => {
    const d = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchOffers = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await offersApi.getMyOffers();
      setOffers(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to fetch your store offers.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOffers();
  }, [fetchOffers]);

  // Lifecycle Action Handlers
  const handleActivate = async (offer: Offer) => {
    setActionLoadingId(offer.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await offersApi.activateOffer(offer.id);
      setSuccessMessage(`Activated "${offer.title}". It is now live in the Shopper Marketplace!`);
      await fetchOffers();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to activate offer.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handlePause = async (offer: Offer) => {
    setActionLoadingId(offer.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await offersApi.pauseOffer(offer.id);
      setSuccessMessage(`Paused "${offer.title}". Shoppers cannot claim it while paused.`);
      await fetchOffers();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to pause offer.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleResume = async (offer: Offer) => {
    setActionLoadingId(offer.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await offersApi.resumeOffer(offer.id);
      setSuccessMessage(`Resumed "${offer.title}". It is now active again!`);
      await fetchOffers();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to resume offer.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleCreateOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setCreateError('Please enter an offer title.');
      return;
    }
    if (discountValue <= 0) {
      setCreateError('Discount value must be greater than zero.');
      return;
    }
    if (discountType === 'percentage' && discountValue > 100) {
      setCreateError('Percentage discount cannot exceed 100%.');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const payload: OfferCreateRequest = {
        title: title.trim(),
        description: description.trim() || null,
        discount_type: discountType,
        discount_value: Number(discountValue),
        minimum_purchase: minimumPurchase ? Number(minimumPurchase) : null,
        starts_at: new Date(startsAt).toISOString(),
        expires_at: new Date(expiresAt).toISOString(),
        status: 'draft',
      };

      const created = await offersApi.createOffer(payload);
      setSuccessMessage(`Created offer "${created.title}" in Draft status. You can activate it when ready!`);
      setShowCreateModal(false);
      // Reset form
      setTitle('');
      setDescription('');
      await fetchOffers();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create offer.');
    } finally {
      setIsCreating(false);
    }
  };

  const filteredOffers = offers.filter((o) => {
    if (activeTab === 'all') return true;
    return o.status === activeTab;
  });

  const getStatusBadge = (status: OfferStatus) => {
    switch (status) {
      case 'active':
        return <span className="status-pill pill-active">Active</span>;
      case 'draft':
        return <span className="status-pill pill-draft">Draft</span>;
      case 'paused':
        return <span className="status-pill pill-paused">Paused</span>;
      case 'expired':
        return <span className="status-pill pill-expired">Expired</span>;
      default:
        return <span className="status-pill">{status}</span>;
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleDateString('en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="shopkeeper-offers-page">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Store Offers & Promotions</h1>
          <p className="page-subtitle">
            Manage your discounts across draft, active, and paused lifecycles.
          </p>
        </div>
        <div className="header-action-group">
          <Link to="/app/shopkeeper/ai-create" className="btn-secondary">
            <Sparkles size={16} />
            <span>AI Studio</span>
          </Link>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus size={16} />
            <span>New Offer</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="alert-box alert-success" role="alert">
          <CheckCircle2 size={18} className="alert-icon" />
          <span>{successMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Lifecycle Status Tabs */}
      <div className="tabs-container">
        <button
          type="button"
          onClick={() => setActiveTab('all')}
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          All ({offers.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('active')}
          className={`tab-btn ${activeTab === 'active' ? 'active' : ''}`}
        >
          Active ({offers.filter((o) => o.status === 'active').length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('draft')}
          className={`tab-btn ${activeTab === 'draft' ? 'active' : ''}`}
        >
          Draft ({offers.filter((o) => o.status === 'draft').length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('paused')}
          className={`tab-btn ${activeTab === 'paused' ? 'active' : ''}`}
        >
          Paused ({offers.filter((o) => o.status === 'paused').length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('expired')}
          className={`tab-btn ${activeTab === 'expired' ? 'active' : ''}`}
        >
          Expired ({offers.filter((o) => o.status === 'expired').length})
        </button>
      </div>

      {/* Offers Grid / List */}
      {isLoading ? (
        <LoadingSpinner message="Loading your store offers..." />
      ) : filteredOffers.length === 0 ? (
        <EmptyState
          icon={Tag}
          title={activeTab === 'all' ? 'No offers created yet' : `No ${activeTab} offers`}
          description="Create a new discount offer manually or use the AI natural-language parser to launch a promotion in seconds."
          action={{
            label: 'Create an Offer',
            icon: Plus,
            onClick: () => setShowCreateModal(true),
          }}
        />
      ) : (
        <div className="offers-management-grid">
          {filteredOffers.map((offer) => (
            <div key={offer.id} className={`offer-manage-card status-${offer.status}`}>
              <div className="manage-card-header">
                <div className="manage-discount-pill">
                  {offer.discount_type === 'percentage' ? (
                    <Percent size={14} />
                  ) : (
                    <Banknote size={14} />
                  )}
                  <span>
                    {offer.discount_type === 'percentage'
                      ? `${offer.discount_value}% OFF`
                      : `₹${Number(offer.discount_value).toFixed(0)} OFF`}
                  </span>
                </div>
                {getStatusBadge(offer.status)}
              </div>

              <div className="manage-card-body">
                <h3 className="manage-offer-title">{offer.title}</h3>
                {offer.description && (
                  <p className="manage-offer-desc">{offer.description}</p>
                )}
              </div>

              <div className="manage-card-meta">
                <div className="manage-meta-item">
                  <span className="meta-label">Minimum Purchase:</span>
                  <strong>
                    {offer.minimum_purchase
                      ? `₹${Number(offer.minimum_purchase).toFixed(0)}`
                      : 'None'}
                  </strong>
                </div>
                <div className="manage-meta-item">
                  <span className="meta-label">Validity:</span>
                  <span>{formatDate(offer.starts_at)} → {formatDate(offer.expires_at)}</span>
                </div>
              </div>

              {/* Lifecycle Actions */}
              <div className="manage-card-actions">
                {offer.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => handleActivate(offer)}
                    disabled={actionLoadingId === offer.id}
                    className="btn-action btn-activate"
                    title="Publish offer to marketplace"
                  >
                    {actionLoadingId === offer.id ? (
                      <div className="btn-spinner small" />
                    ) : (
                      <Play size={14} />
                    )}
                    <span>Activate Offer</span>
                  </button>
                )}

                {offer.status === 'active' && (
                  <button
                    type="button"
                    onClick={() => handlePause(offer)}
                    disabled={actionLoadingId === offer.id}
                    className="btn-action btn-pause"
                    title="Pause offer temporarily"
                  >
                    {actionLoadingId === offer.id ? (
                      <div className="btn-spinner small" />
                    ) : (
                      <Pause size={14} />
                    )}
                    <span>Pause Offer</span>
                  </button>
                )}

                {offer.status === 'paused' && (
                  <button
                    type="button"
                    onClick={() => handleResume(offer)}
                    disabled={actionLoadingId === offer.id}
                    className="btn-action btn-resume"
                    title="Resume paused offer"
                  >
                    {actionLoadingId === offer.id ? (
                      <div className="btn-spinner small" />
                    ) : (
                      <RotateCcw size={14} />
                    )}
                    <span>Resume Offer</span>
                  </button>
                )}

                {offer.status === 'expired' && (
                  <span className="text-muted text-sm flex items-center gap-1">
                    <Clock size={13} /> Expired promotion
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Manual Offer Creation Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Discount Offer"
      >
        <form onSubmit={handleCreateOffer} className="create-offer-form">
          {createError && (
            <div className="alert-box alert-error">
              <AlertCircle size={16} />
              <span>{createError}</span>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="offer-title">Offer Title *</label>
            <input
              id="offer-title"
              type="text"
              placeholder="e.g. 20% OFF on Organic Produce"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="offer-desc">Description (Optional)</label>
            <textarea
              id="offer-desc"
              rows={2}
              placeholder="e.g. Applicable on all fresh vegetables and fruits."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="form-input"
            />
          </div>

          <div className="form-row-dual">
            <div className="form-group">
              <label htmlFor="discount-type">Discount Type</label>
              <select
                id="discount-type"
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value as DiscountType)}
                className="form-input"
              >
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed Amount (₹)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="discount-val">
                Discount Value {discountType === 'percentage' ? '(%)' : '(₹)'} *
              </label>
              <input
                id="discount-val"
                type="number"
                min={1}
                max={discountType === 'percentage' ? 100 : 10000}
                value={discountValue}
                onChange={(e) => setDiscountValue(Number(e.target.value))}
                required
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="min-purchase">Minimum Purchase Bill (₹, Optional)</label>
            <input
              id="min-purchase"
              type="number"
              min={0}
              placeholder="e.g. 500 (0 for no minimum)"
              value={minimumPurchase}
              onChange={(e) => setMinimumPurchase(e.target.value)}
              className="form-input"
            />
          </div>

          <div className="form-row-dual">
            <div className="form-group">
              <label htmlFor="start-date">Starts At</label>
              <input
                id="start-date"
                type="datetime-local"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
                required
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="expiry-date">Expires At</label>
              <input
                id="expiry-date"
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                required
                className="form-input"
              />
            </div>
          </div>

          <div className="modal-actions">
            <button
              type="submit"
              disabled={isCreating}
              className="btn-primary btn-full"
            >
              {isCreating ? (
                <>
                  <div className="btn-spinner" />
                  <span>Creating Draft Offer...</span>
                </>
              ) : (
                <>
                  <Plus size={18} />
                  <span>Create Offer (Draft)</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
