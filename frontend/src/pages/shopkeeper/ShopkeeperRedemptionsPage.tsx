import React, { useEffect, useState, useCallback } from 'react';
import {
  AlertCircle,
  RefreshCw,
  Search,
  Receipt,
} from 'lucide-react';
import { shopsApi } from '../../api/shops';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { EmptyState } from '../../components/EmptyState';
import type { RedemptionResponse } from '../../types';

export const ShopkeeperRedemptionsPage: React.FC = () => {
  const [redemptions, setRedemptions] = useState<RedemptionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchRedemptions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await shopsApi.getMyRedemptions();
      setRedemptions(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to fetch redemption history.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRedemptions();
  }, [fetchRedemptions]);

  const filteredRedemptions = redemptions.filter((r) => {
    if (!searchTerm.trim()) return true;
    return r.claim_code.toLowerCase().includes(searchTerm.toLowerCase().trim());
  });

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString('en-IN', {
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
    <div className="shopkeeper-redemptions-page">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Store Redemption History</h1>
          <p className="page-subtitle">
            Complete audit trail of customer discount claims redeemed at your checkout counters.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchRedemptions}
          disabled={isLoading}
          className="btn-refresh"
          title="Refresh History"
        >
          <RefreshCw size={16} className={isLoading ? 'spin-icon' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="filters-bar">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Filter by Claim Code (e.g. NO-847291)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="filter-search-input"
          />
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Table Content */}
      {isLoading ? (
        <LoadingSpinner message="Retrieving checkout redemption records..." />
      ) : filteredRedemptions.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title={searchTerm ? 'No matching redemptions found' : 'No checkout redemptions recorded yet'}
          description="When counter staff process shopper claim codes at checkout, they will appear in this ledger."
        />
      ) : (
        <div className="redemptions-table-card">
          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Redemption ID</th>
                  <th>Claim Code</th>
                  <th>Bill Total</th>
                  <th>Discount Given</th>
                  <th>Customer Paid</th>
                  <th>Points Deducted</th>
                  <th>Redeemed Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredRedemptions.map((rdm) => {
                  const finalPaid = Number(rdm.purchase_amount) - Number(rdm.discount_amount);

                  return (
                    <tr key={rdm.id}>
                      <td className="text-muted">#{rdm.id}</td>
                      <td>
                        <span className="table-code-pill font-mono">{rdm.claim_code}</span>
                      </td>
                      <td>₹{Number(rdm.purchase_amount).toFixed(2)}</td>
                      <td className="text-success font-semibold">
                        -₹{Number(rdm.discount_amount).toFixed(2)}
                      </td>
                      <td className="font-semibold">₹{finalPaid.toFixed(2)}</td>
                      <td>
                        <span className="points-deduct-pill">
                          -{Number(rdm.points_deducted || rdm.discount_amount).toFixed(0)} pts
                        </span>
                      </td>
                      <td className="text-muted">{formatDate(rdm.redeemed_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
