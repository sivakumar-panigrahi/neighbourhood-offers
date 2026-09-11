import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Store,
  Coins,
  TrendingUp,
  Ticket,
  Calendar,
  Sparkles,
  Plus,
  ArrowRight,
  AlertCircle,
  RefreshCw,
  ShoppingBag,
} from 'lucide-react';
import { shopsApi } from '../../api/shops';
import { reportsApi } from '../../api/reports';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { Modal } from '../../components/Modal';
import type { MonthlyReport, PointsBalance, RedemptionResponse, Shop } from '../../types';

export const ShopkeeperDashboardPage: React.FC = () => {
  const [shop, setShop] = useState<Shop | null>(null);
  const [points, setPoints] = useState<PointsBalance | null>(null);
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [recentRedemptions, setRecentRedemptions] = useState<RedemptionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Shop Setup Form (for new shopkeepers)
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [setupName, setSetupName] = useState('');
  const [setupAddress, setSetupAddress] = useState('');
  const [setupCity, setSetupCity] = useState('Vijayawada');
  const [isSubmittingShop, setIsSubmittingShop] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      // 1. Fetch Shop
      let currentShop: Shop | null = null;
      try {
        currentShop = await shopsApi.getMyShop();
        setShop(currentShop);
      } catch (err: any) {
        if (err.status === 404) {
          setShowSetupModal(true);
          setIsLoading(false);
          return;
        }
        throw err;
      }

      // 2. Fetch Points, Report, and Redemptions in parallel
      const [ptsData, repData, rdmsData] = await Promise.all([
        shopsApi.getMyPoints().catch(() => null),
        reportsApi.getMonthlyReport().catch(() => null),
        shopsApi.getMyRedemptions().catch(() => []),
      ]);

      setPoints(ptsData);
      setReport(repData);
      setRecentRedemptions(rdmsData.slice(0, 5));
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to load shop dashboard data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleCreateShop = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setupName.trim() || !setupAddress.trim()) {
      setSetupError('Please provide both shop name and address.');
      return;
    }
    setIsSubmittingShop(true);
    setSetupError(null);

    try {
      const newShop = await shopsApi.createShop({
        name: setupName.trim(),
        address: setupAddress.trim(),
        city: setupCity.trim() || 'Vijayawada',
      });
      setShop(newShop);
      setShowSetupModal(false);
      await fetchDashboardData();
    } catch (err: any) {
      setSetupError(err.message || 'Failed to setup shop.');
    } finally {
      setIsSubmittingShop(false);
    }
  };

  const getTopBusyDay = () => {
    if (!report || !report.busy_days || report.busy_days.length === 0) {
      return null;
    }
    // Busy days are pre-sorted by highest redemptions first from the backend
    return report.busy_days[0];
  };

  const topDay = getTopBusyDay();

  return (
    <div className="shopkeeper-dashboard-page">
      {/* Top Banner / Shop Welcome */}
      <div className="dashboard-hero-banner">
        <div className="hero-content">
          <div className="hero-tag">
            <Store size={14} />
            <span>Verified Merchant Portal</span>
          </div>
          <h1 className="hero-title">{shop ? shop.name : "Shopkeeper's Dashboard"}</h1>
          <p className="hero-address">
            {shop ? `${shop.address}, ${shop.city}` : 'Vijayawada Hyperlocal Network'}
          </p>
          <div className="hero-promise-badge">
            <Sparkles size={14} />
            <span>Pay for real footfall at checkout, not for clicks.</span>
          </div>
        </div>

        <div className="hero-actions">
          <button
            type="button"
            onClick={fetchDashboardData}
            disabled={isLoading}
            className="btn-refresh"
            title="Refresh Dashboard"
          >
            <RefreshCw size={16} className={isLoading ? 'spin-icon' : ''} />
            <span>Sync</span>
          </button>
          <Link to="/app/shopkeeper/ai-create" className="btn-primary">
            <Sparkles size={16} />
            <span>Create with AI</span>
          </Link>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner message="Calculating shop metrics & points..." />
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div className="metrics-cards-grid">
            {/* 1. Remaining Points Balance */}
            <div className="metric-card card-points">
              <div className="metric-header">
                <span className="metric-label">Points Balance</span>
                <div className="metric-icon-circle points-icon">
                  <Coins size={20} />
                </div>
              </div>
              <div className="metric-value">
                {points ? Number(points.balance).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
                <span className="metric-unit">pts</span>
              </div>
              <div className="metric-footer">
                <span className="footer-note">1 pt = ₹1 discount budget</span>
                <Link to="/app/shopkeeper/points" className="metric-link">
                  Top Up <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* 2. Monthly Platform Spend */}
            <div className="metric-card card-spend">
              <div className="metric-header">
                <span className="metric-label">
                  Monthly Spend ({report?.month || 'Current'})
                </span>
                <div className="metric-icon-circle spend-icon">
                  <TrendingUp size={20} />
                </div>
              </div>
              <div className="metric-value">
                ₹{report ? Number(report.total_spend).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <div className="metric-footer">
                <span className="footer-note">Discounts redeemed this month</span>
                <Link to="/app/shopkeeper/reports" className="metric-link">
                  Analytics <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* 3. Total Redemptions */}
            <div className="metric-card card-redemptions">
              <div className="metric-header">
                <span className="metric-label">Redemptions Log</span>
                <div className="metric-icon-circle redemptions-icon">
                  <Ticket size={20} />
                </div>
              </div>
              <div className="metric-value">
                {recentRedemptions.length > 0 ? recentRedemptions.length : 0}
                <span className="metric-unit">checkouts</span>
              </div>
              <div className="metric-footer">
                <span className="footer-note">Customer checkouts recorded</span>
                <Link to="/app/shopkeeper/redemptions" className="metric-link">
                  History <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* 4. Peak Footfall Day */}
            <div className="metric-card card-busy">
              <div className="metric-header">
                <span className="metric-label">Peak Footfall Day</span>
                <div className="metric-icon-circle busy-icon">
                  <Calendar size={20} />
                </div>
              </div>
              <div className="metric-value-sm">
                {topDay ? (
                  <>
                    <strong className="top-day-date">{topDay.date}</strong>
                    <div className="top-day-details">
                      <span>{topDay.redemptions} customers</span>
                      <span>₹{topDay.spend.toFixed(0)} spent</span>
                    </div>
                  </>
                ) : (
                  <span className="text-muted">No checkouts yet</span>
                )}
              </div>
              <div className="metric-footer">
                <span className="footer-note">Based on live counter activity</span>
                <Link to="/app/shopkeeper/reports" className="metric-link">
                  View Days <ArrowRight size={13} />
                </Link>
              </div>
            </div>
          </div>

          {/* Quick Action Shortcuts */}
          <div className="quick-shortcuts-section">
            <h2 className="section-title">Quick Shopkeeper Tools</h2>
            <div className="shortcuts-grid">
              <Link to="/app/shopkeeper/ai-create" className="shortcut-card">
                <div className="shortcut-icon-box ai-box">
                  <Sparkles size={22} />
                </div>
                <div className="shortcut-info">
                  <h3>AI Offer Studio</h3>
                  <p>Type a plain English promotion and let AI structure and calculate discount parameters.</p>
                </div>
              </Link>

              <Link to="/app/shopkeeper/offers" className="shortcut-card">
                <div className="shortcut-icon-box offers-box">
                  <ShoppingBag size={22} />
                </div>
                <div className="shortcut-info">
                  <h3>Manage Offers</h3>
                  <p>Activate, pause, or resume your active discounts with single-click lifecycle toggles.</p>
                </div>
              </Link>

              <Link to="/app/shopkeeper/points" className="shortcut-card">
                <div className="shortcut-icon-box points-box">
                  <Coins size={22} />
                </div>
                <div className="shortcut-info">
                  <h3>Preload Points</h3>
                  <p>Top up your platform points budget so customers can continuously redeem your deals.</p>
                </div>
              </Link>

              <Link to="/app/shopkeeper/reports" className="shortcut-card">
                <div className="shortcut-icon-box reports-box">
                  <TrendingUp size={22} />
                </div>
                <div className="shortcut-info">
                  <h3>Monthly Reports</h3>
                  <p>Analyze footfall trends, discount expenditure, and busiest shopping days.</p>
                </div>
              </Link>
            </div>
          </div>

          {/* Recent Redemptions Table Preview */}
          <div className="dashboard-table-card">
            <div className="card-table-header">
              <div>
                <h3 className="card-table-title">Recent Checkout Redemptions</h3>
                <p className="card-table-subtitle">Verified customer discounts processed at counter</p>
              </div>
              <Link to="/app/shopkeeper/redemptions" className="btn-secondary btn-sm">
                <span>View All History</span>
                <ArrowRight size={14} />
              </Link>
            </div>

            {recentRedemptions.length === 0 ? (
              <div className="empty-table-notice">
                <Ticket size={28} className="empty-icon" />
                <p>No redemptions have been processed yet this month.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Claim Code</th>
                      <th>Purchase Amount</th>
                      <th>Discount Given</th>
                      <th>Customer Paid</th>
                      <th>Redeemed At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRedemptions.map((rdm) => (
                      <tr key={rdm.id}>
                        <td>
                          <span className="table-code-pill">{rdm.claim_code}</span>
                        </td>
                        <td>₹{Number(rdm.purchase_amount).toFixed(2)}</td>
                        <td className="text-success font-semibold">
                          -₹{Number(rdm.discount_amount).toFixed(2)}
                        </td>
                        <td>
                          ₹{(Number(rdm.purchase_amount) - Number(rdm.discount_amount)).toFixed(2)}
                        </td>
                        <td className="text-muted">
                          {new Date(rdm.redeemed_at).toLocaleString('en-IN', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* New Shop Setup Modal */}
      <Modal
        isOpen={showSetupModal}
        onClose={() => setShowSetupModal(false)}
        title="Setup Your Shop Profile"
      >
        <form onSubmit={handleCreateShop} className="setup-shop-form">
          <p className="setup-intro">
            Welcome to Neighbourhood Offers! Register your physical store details to begin publishing discounts.
          </p>

          {setupError && (
            <div className="alert-box alert-error">
              <AlertCircle size={16} />
              <span>{setupError}</span>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="shop-name">Store Name</label>
            <input
              id="shop-name"
              type="text"
              placeholder="e.g. Anitha's Grocery"
              value={setupName}
              onChange={(e) => setSetupName(e.target.value)}
              required
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="shop-address">Store Address</label>
            <input
              id="shop-address"
              type="text"
              placeholder="e.g. Shop #12, MG Road, Governorpet"
              value={setupAddress}
              onChange={(e) => setSetupAddress(e.target.value)}
              required
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="shop-city">City</label>
            <input
              id="shop-city"
              type="text"
              value={setupCity}
              onChange={(e) => setSetupCity(e.target.value)}
              required
              className="form-input"
            />
          </div>

          <div className="modal-actions">
            <button
              type="submit"
              disabled={isSubmittingShop}
              className="btn-primary btn-full"
            >
              {isSubmittingShop ? (
                <>
                  <div className="btn-spinner" />
                  <span>Registering Shop...</span>
                </>
              ) : (
                <>
                  <Plus size={18} />
                  <span>Register Store</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
