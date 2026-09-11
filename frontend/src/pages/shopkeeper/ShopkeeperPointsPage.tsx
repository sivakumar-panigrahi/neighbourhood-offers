import React, { useEffect, useState, useCallback } from 'react';
import {
  Coins,
  PlusCircle,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw,
  ShieldCheck,
  CreditCard,
} from 'lucide-react';
import { shopsApi } from '../../api/shops';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import type { PointsBalance } from '../../types';

const TOPUP_PRESETS = [500, 1000, 2500, 5000];

export const ShopkeeperPointsPage: React.FC = () => {
  const [points, setPoints] = useState<PointsBalance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Top up Form State
  const [topUpAmount, setTopUpAmount] = useState<number>(1000);
  const [isSubmittingTopUp, setIsSubmittingTopUp] = useState(false);

  const fetchPoints = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await shopsApi.getMyPoints();
      setPoints(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to fetch store points account.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPoints();
  }, [fetchPoints]);

  const handleTopUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topUpAmount || topUpAmount <= 0) {
      setErrorMessage('Top-up amount must be greater than zero.');
      return;
    }

    setIsSubmittingTopUp(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const updated = await shopsApi.topUpPoints({
        amount: Number(topUpAmount),
        description: `Emulated dashboard top-up of ₹${topUpAmount}`,
      });
      setPoints(updated);
      setSuccessMessage(`Successfully topped up ${topUpAmount.toLocaleString()} points! New balance: ${Number(updated.balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })} pts.`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to top up points account.');
    } finally {
      setIsSubmittingTopUp(false);
    }
  };

  return (
    <div className="shopkeeper-points-page">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Points Management & Ledger</h1>
          <p className="page-subtitle">
            Preload platform points to fund your customer discounts.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchPoints}
          disabled={isLoading}
          className="btn-refresh"
          title="Refresh Points"
        >
          <RefreshCw size={16} className={isLoading ? 'spin-icon' : ''} />
          <span>Sync Balance</span>
        </button>
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

      {isLoading ? (
        <LoadingSpinner message="Retrieving live points balance..." />
      ) : (
        <div className="points-dashboard-layout">
          {/* Left Column: Balance & Explainer */}
          <div className="points-summary-col">
            {/* Big Balance Card */}
            <div className="points-balance-card">
              <div className="balance-icon-ring">
                <Coins size={36} />
              </div>
              <span className="balance-card-label">Available Points Balance</span>
              <div className="balance-number-display">
                <span className="balance-amount">
                  {points ? Number(points.balance).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
                </span>
                <span className="balance-unit">pts</span>
              </div>
              <div className="balance-conversion-pill">
                <ShieldCheck size={14} />
                <span>1 Point = ₹1 Verified Platform Spend</span>
              </div>
            </div>

            {/* Business Model Rule Card */}
            <div className="rule-explainer-card">
              <h3 className="explainer-title">
                <Sparkles size={16} className="text-highlight" />
                <span>How Points Work</span>
              </h3>
              <ul className="explainer-list">
                <li>
                  <strong>Atomic Deductions:</strong> Points are deducted strictly when counter staff process a verified checkout redemption.
                </li>
                <li>
                  <strong>Zero Wastage:</strong> Shopper claims and impressions do NOT deduct your balance. You only pay for verified footfall.
                </li>
                <li>
                  <strong>Safe Concurrency:</strong> Database row-level locking ensures balances never go negative.
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column: Preload Top-up Form */}
          <div className="points-topup-col">
            <div className="topup-form-card">
              <div className="topup-header">
                <div className="topup-icon-box">
                  <PlusCircle size={22} />
                </div>
                <div>
                  <h3 className="topup-title">Preload Points (Development Emulation)</h3>
                  <p className="topup-subtitle">Instantly add discount credits to your merchant balance</p>
                </div>
              </div>

              <form onSubmit={handleTopUp} className="topup-form">
                <div className="form-group">
                  <label htmlFor="topup-amt">Top-Up Amount (Points / ₹)</label>
                  <input
                    id="topup-amt"
                    type="number"
                    min={1}
                    max={100000}
                    step={100}
                    value={topUpAmount}
                    onChange={(e) => setTopUpAmount(Number(e.target.value))}
                    required
                    disabled={isSubmittingTopUp}
                    className="form-input"
                  />
                </div>

                {/* Preset Chips */}
                <div className="preset-amounts-row">
                  <span className="preset-label">Quick amounts:</span>
                  <div className="preset-chips">
                    {TOPUP_PRESETS.map((amt) => (
                      <button
                        key={amt}
                        type="button"
                        onClick={() => setTopUpAmount(amt)}
                        className={`preset-chip ${topUpAmount === amt ? 'active' : ''}`}
                      >
                        +₹{amt.toLocaleString()}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmittingTopUp || topUpAmount <= 0}
                  className="btn-primary btn-full btn-topup"
                >
                  {isSubmittingTopUp ? (
                    <>
                      <div className="btn-spinner" />
                      <span>Processing Top-up...</span>
                    </>
                  ) : (
                    <>
                      <CreditCard size={18} />
                      <span>Add {topUpAmount ? topUpAmount.toLocaleString() : 0} Points</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
