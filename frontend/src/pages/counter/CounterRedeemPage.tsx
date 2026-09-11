import React, { useState } from 'react';
import {
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Ticket,
  Receipt,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import { redemptionsApi } from '../../api/redemptions';
import type { RedemptionResponse } from '../../types';

export const CounterRedeemPage: React.FC = () => {
  const [claimCode, setClaimCode] = useState('');
  const [purchaseAmount, setPurchaseAmount] = useState<string>('');
  const [isRedeeming, setIsRedeeming] = useState(false);
  const [redemptionResult, setRedemptionResult] = useState<RedemptionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Generate a random UUID v4 for idempotency
  const generateIdempotencyKey = () => {
    return 'idem-' + Math.random().toString(36).substring(2, 15) + '-' + Date.now();
  };

  const handleRedeem = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = claimCode.trim().toUpperCase();
    const amountNum = parseFloat(purchaseAmount);

    if (!cleanCode) {
      setErrorMessage('Please enter a customer claim code (e.g. NO-X7K92M).');
      return;
    }
    if (isNaN(amountNum) || amountNum <= 0) {
      setErrorMessage('Please enter a valid purchase bill amount greater than ₹0.');
      return;
    }

    setIsRedeeming(true);
    setErrorMessage(null);
    setRedemptionResult(null);

    const idempotencyKey = generateIdempotencyKey();

    try {
      const response = await redemptionsApi.createRedemption(
        {
          claim_code: cleanCode,
          purchase_amount: amountNum,
        },
        idempotencyKey
      );

      setRedemptionResult(response);
    } catch (err: any) {
      setErrorMessage(err.message || 'Redemption failed. Check code and minimum purchase requirements.');
    } finally {
      setIsRedeeming(false);
    }
  };

  const handleResetForNext = () => {
    setClaimCode('');
    setPurchaseAmount('');
    setRedemptionResult(null);
    setErrorMessage(null);
  };

  return (
    <div className="counter-redeem-page">
      {/* Banner */}
      <div className="counter-hero-banner">
        <div className="counter-banner-tag">
          <CreditCard size={14} />
          <span>Point-of-Sale Terminal</span>
        </div>
        <h1 className="counter-title">Counter Staff Checkout & Redemption</h1>
        <p className="counter-subtitle">
          Verify customer claim codes, apply store discount caps atomically, and process instant checkout savings.
        </p>
      </div>

      {/* Main Terminal Grid */}
      <div className="counter-terminal-grid">
        {/* Left Side: Redemption Form */}
        <div className="counter-form-card">
          <div className="form-card-header">
            <h2 className="terminal-card-title">Customer Checkout</h2>
            <span className="terminal-status-pill">Ready</span>
          </div>

          {errorMessage && (
            <div className="alert-box alert-error" role="alert">
              <AlertCircle size={18} className="alert-icon" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleRedeem} className="terminal-form">
            <div className="form-group">
              <label htmlFor="claim-code-input">
                Customer Claim Code * (Format: NO-XXXXXX)
              </label>
              <div className="code-input-wrapper">
                <Ticket size={18} className="input-icon" />
                <input
                  id="claim-code-input"
                  type="text"
                  placeholder="e.g. NO-X7K92M"
                  value={claimCode}
                  onChange={(e) => setClaimCode(e.target.value.toUpperCase())}
                  required
                  autoFocus
                  disabled={isRedeeming || Boolean(redemptionResult)}
                  className="form-input font-mono uppercase font-bold"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="purchase-amount-input">
                Gross Purchase Amount (Total Bill in ₹) *
              </label>
              <div className="amount-input-wrapper">
                <span className="currency-prefix">₹</span>
                <input
                  id="purchase-amount-input"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="e.g. 1500.00"
                  value={purchaseAmount}
                  onChange={(e) => setPurchaseAmount(e.target.value)}
                  required
                  disabled={isRedeeming || Boolean(redemptionResult)}
                  className="form-input amount-input font-semibold"
                />
              </div>
            </div>

            {!redemptionResult && (
              <button
                type="submit"
                disabled={isRedeeming || !claimCode.trim() || !purchaseAmount}
                className="btn-primary btn-full btn-redeem-action"
              >
                {isRedeeming ? (
                  <>
                    <div className="btn-spinner" />
                    <span>Processing Redemption...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={18} />
                    <span>Apply Discount & Redeem</span>
                  </>
                )}
              </button>
            )}
          </form>

          {/* Business Rules Reminder */}
          <div className="terminal-rules-footer">
            <div className="rules-item">
              <ShieldCheck size={14} className="text-success" />
              <span>Idempotent submission protection</span>
            </div>
            <div className="rules-item">
              <ShieldCheck size={14} className="text-success" />
              <span>1 Point = ₹1 Discount Deduction</span>
            </div>
          </div>
        </div>

        {/* Right Side: Receipt Result or Guidance */}
        <div className="counter-result-col">
          {redemptionResult ? (
            <div className="receipt-card">
              <div className="receipt-header">
                <div className="receipt-success-badge">
                  <CheckCircle2 size={28} />
                </div>
                <h3 className="receipt-title">Redemption Successful!</h3>
                <span className="receipt-code">{redemptionResult.claim_code}</span>
              </div>

              <div className="receipt-breakdown">
                <div className="receipt-row">
                  <span>Gross Purchase Bill:</span>
                  <strong>₹{Number(redemptionResult.purchase_amount).toFixed(2)}</strong>
                </div>

                <div className="receipt-row discount-row">
                  <span>Discount Applied:</span>
                  <strong className="text-success">
                    -₹{Number(redemptionResult.discount_amount).toFixed(2)}
                  </strong>
                </div>

                <div className="receipt-divider" />

                <div className="receipt-row payable-row">
                  <span>Customer Pays (Net):</span>
                  <strong className="payable-amount">
                    ₹{Number(redemptionResult.final_amount).toFixed(2)}
                  </strong>
                </div>

                <div className="receipt-divider" />

                <div className="receipt-row points-row">
                  <span>Points Deducted from Shop:</span>
                  <span className="points-deducted-tag">
                    -{Number(redemptionResult.points_deducted).toFixed(0)} pts
                  </span>
                </div>

                <div className="receipt-row">
                  <span>Remaining Shop Points:</span>
                  <span className="text-muted">
                    {Number(redemptionResult.remaining_points).toLocaleString('en-IN', {
                      minimumFractionDigits: 2,
                    })}{' '}
                    pts
                  </span>
                </div>
              </div>

              <div className="receipt-actions">
                <button
                  type="button"
                  onClick={handleResetForNext}
                  className="btn-primary btn-full btn-next-customer"
                >
                  <RotateCcw size={16} />
                  <span>Next Customer Checkout</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="terminal-instructions-card">
              <div className="instructions-icon-box">
                <Receipt size={32} />
              </div>
              <h3 className="instructions-title">Checkout Procedure</h3>
              <ol className="instructions-list">
                <li>
                  <strong>1. Ask for Claim Code:</strong> Shoppers find their <code>NO-XXXXXX</code> code in their Claim Wallet.
                </li>
                <li>
                  <strong>2. Enter Total Bill:</strong> Input the gross amount before applying any platform discount.
                </li>
                <li>
                  <strong>3. Instant Verification:</strong> System atomically validates minimum purchase, expiry, and shop points balance.
                </li>
                <li>
                  <strong>4. Collect Net Amount:</strong> Charge the customer the discounted net payable total shown on the receipt.
                </li>
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
