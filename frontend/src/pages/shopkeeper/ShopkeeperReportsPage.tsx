import React, { useEffect, useState, useCallback } from 'react';
import {
  TrendingUp,
  Calendar,
  Coins,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  BarChart3,
} from 'lucide-react';
import { reportsApi } from '../../api/reports';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { EmptyState } from '../../components/EmptyState';
import type { MonthlyReport } from '../../types';

export const ShopkeeperReportsPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState<string>(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  });

  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await reportsApi.getMonthlyReport(selectedMonth);
      setReport(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to load monthly report.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedMonth]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handlePrevMonth = () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    const prevDate = new Date(year, month - 2, 1);
    const newMonth = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;
    setSelectedMonth(newMonth);
  };

  const handleNextMonth = () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    const nextDate = new Date(year, month, 1);
    const newMonth = `${nextDate.getFullYear()}-${String(nextDate.getMonth() + 1).padStart(2, '0')}`;
    setSelectedMonth(newMonth);
  };

  const getMaxRedemptions = () => {
    if (!report || !report.busy_days || report.busy_days.length === 0) return 1;
    return Math.max(...report.busy_days.map((d) => d.redemptions), 1);
  };

  const maxRedemptions = getMaxRedemptions();

  const formatMonthDisplay = (monthStr: string) => {
    try {
      const [year, month] = monthStr.split('-').map(Number);
      const d = new Date(year, month - 1, 1);
      return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
    } catch {
      return monthStr;
    }
  };

  return (
    <div className="shopkeeper-reports-page">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Monthly Footfall & Spend Analytics</h1>
          <p className="page-subtitle">
            Track customer redemptions, spend performance, and peak footfall days.
          </p>
        </div>

        {/* Month Selector Bar */}
        <div className="month-navigator-bar">
          <button
            type="button"
            onClick={handlePrevMonth}
            className="btn-month-nav"
            title="Previous Month"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="month-display-box">
            <Calendar size={16} className="text-highlight" />
            <span className="month-display-text">{formatMonthDisplay(selectedMonth)}</span>
          </div>
          <button
            type="button"
            onClick={handleNextMonth}
            className="btn-month-nav"
            title="Next Month"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="alert-box alert-error" role="alert">
          <AlertCircle size={18} className="alert-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner message={`Compiling report data for ${formatMonthDisplay(selectedMonth)}...`} />
      ) : (
        <div className="reports-content-layout">
          {/* Top Metric Cards */}
          <div className="report-metrics-grid">
            <div className="report-metric-card spend-gradient">
              <div className="report-metric-header">
                <span>Total Discount Spend</span>
                <TrendingUp size={20} />
              </div>
              <div className="report-metric-value">
                ₹{report ? Number(report.total_spend).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <span className="report-metric-sub">Verified customer savings this month</span>
            </div>

            <div className="report-metric-card points-gradient">
              <div className="report-metric-header">
                <span>Current Remaining Points</span>
                <Coins size={20} />
              </div>
              <div className="report-metric-value">
                {report ? Number(report.remaining_points).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
                <span className="metric-unit">pts</span>
              </div>
              <span className="report-metric-sub">Live points balance available</span>
            </div>

            <div className="report-metric-card footfall-gradient">
              <div className="report-metric-header">
                <span>Active Footfall Days</span>
                <BarChart3 size={20} />
              </div>
              <div className="report-metric-value">
                {report ? report.busy_days.length : 0}
                <span className="metric-unit">days</span>
              </div>
              <span className="report-metric-sub">Days with ≥1 successful redemption</span>
            </div>
          </div>

          {/* Busy Days Visual Breakdown */}
          <div className="busy-days-section-card">
            <div className="section-card-header">
              <div className="header-text">
                <h2 className="section-title">Busy Days Footfall Breakdown</h2>
                <p className="section-subtitle">
                  Days with verified customer checkouts, ranked by footfall and spend volume.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchReport}
                disabled={isLoading}
                className="btn-refresh"
                title="Refresh Report"
              >
                <RefreshCw size={14} className={isLoading ? 'spin-icon' : ''} />
                <span>Refresh</span>
              </button>
            </div>

            {!report || report.busy_days.length === 0 ? (
              <EmptyState
                icon={Calendar}
                title="No redemptions recorded in this month"
                description={`There was no redemption activity recorded for ${formatMonthDisplay(selectedMonth)}. Select another month using the controls above to review historical data.`}
              />
            ) : (
              <div className="busy-days-list">
                {report.busy_days.map((day, idx) => {
                  const percentWidth = Math.max(12, (day.redemptions / maxRedemptions) * 100);

                  return (
                    <div key={day.date} className="busy-day-row">
                      <div className="day-rank-badge">#{idx + 1}</div>

                      <div className="day-date-col">
                        <span className="date-str">{day.date}</span>
                        <span className="date-relative">
                          {new Date(day.date).toLocaleDateString('en-IN', { weekday: 'short' })}
                        </span>
                      </div>

                      {/* Visual Bar Indicator */}
                      <div className="day-bar-col">
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${percentWidth}%` }}
                          />
                        </div>
                        <div className="bar-label">
                          <strong>{day.redemptions} {day.redemptions === 1 ? 'redemption' : 'redemptions'}</strong>
                        </div>
                      </div>

                      <div className="day-spend-col">
                        <span className="spend-amount">₹{Number(day.spend).toFixed(2)}</span>
                        <span className="spend-label">discount spent</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
