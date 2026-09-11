import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  HelpCircle,
} from 'lucide-react';
import { offersApi } from '../../api/offers';
import type { DiscountType, OfferCreateRequest, OfferParseResponse } from '../../types';

const PROMPT_SUGGESTIONS = [
  'Give customers 20% off all groceries on bills above ₹500 until Sunday.',
  'Flat ₹150 instant discount on total purchase exceeding ₹1200 valid for 10 days.',
  '15% discount on all fresh vegetables and fruits with minimum spend of ₹300.',
  'Diwali special: flat ₹500 off on men ethnic wear above ₹3000.',
];

export const ShopkeeperAICreatePage: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [parseResponse, setParseResponse] = useState<OfferParseResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  // Editable fields after parsing
  const [parsedTitle, setParsedTitle] = useState('');
  const [parsedDescription, setParsedDescription] = useState('');
  const [parsedDiscountType, setParsedDiscountType] = useState<DiscountType>('percentage');
  const [parsedDiscountValue, setParsedDiscountValue] = useState<number>(10);
  const [parsedMinPurchase, setParsedMinPurchase] = useState<string>('');
  const [parsedStartsAt, setParsedStartsAt] = useState<string>('');
  const [parsedExpiresAt, setParsedExpiresAt] = useState<string>('');
  const [activateImmediately, setActivateImmediately] = useState(true);

  const [isCreating, setIsCreating] = useState(false);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  const navigate = useNavigate();

  const handleParse = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) {
      setParseError('Please enter an offer description to parse.');
      return;
    }

    setIsParsing(true);
    setParseError(null);
    setCreateSuccess(null);

    try {
      const resp = await offersApi.parseOfferPrompt(inputText.trim());
      setParseResponse(resp);

      const p = resp.parsed || {};
      setParsedTitle(p.title || inputText.slice(0, 50));
      setParsedDescription(p.description || inputText);
      setParsedDiscountType((p.discount_type as DiscountType) || 'percentage');
      setParsedDiscountValue(p.discount_value !== undefined && p.discount_value !== null ? Number(p.discount_value) : 10);
      setParsedMinPurchase(p.minimum_purchase !== undefined && p.minimum_purchase !== null ? String(p.minimum_purchase) : '');

      const startDt = p.starts_at ? new Date(p.starts_at) : new Date();
      setParsedStartsAt(
        new Date(startDt.getTime() - startDt.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
      );

      const expDt = p.expires_at
        ? new Date(p.expires_at)
        : new Date(Date.now() + 14 * 24 * 60 * 60 * 1000);
      setParsedExpiresAt(
        new Date(expDt.getTime() - expDt.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
      );
    } catch (err: any) {
      setParseError(err.message || 'Failed to parse offer prompt.');
    } finally {
      setIsParsing(false);
    }
  };

  const handleConfirmAndCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parsedTitle.trim()) {
      setParseError('Please provide an offer title.');
      return;
    }
    if (parsedDiscountValue <= 0) {
      setParseError('Discount value must be greater than zero.');
      return;
    }
    if (parsedDiscountType === 'percentage' && parsedDiscountValue > 100) {
      setParseError('Percentage discount cannot exceed 100%.');
      return;
    }

    let startsAtIso: string;
    let expiresAtIso: string;

    try {
      if (!parsedStartsAt) {
        throw new Error('Please select a valid start date and time.');
      }
      if (!parsedExpiresAt) {
        throw new Error('Please select a valid expiry date and time.');
      }

      const startDt = new Date(parsedStartsAt);
      const expDt = new Date(parsedExpiresAt);

      if (isNaN(startDt.getTime())) {
        throw new Error('Start date format is invalid.');
      }
      if (isNaN(expDt.getTime())) {
        throw new Error('Expiry date format is invalid.');
      }
      if (expDt.getTime() <= startDt.getTime()) {
        throw new Error('Expiry date must be later than start date.');
      }

      startsAtIso = startDt.toISOString();
      expiresAtIso = expDt.toISOString();
    } catch (dateErr: any) {
      setParseError(dateErr.message || 'Please provide a valid date range.');
      return;
    }

    setIsCreating(true);
    setParseError(null);

    try {
      const payload: OfferCreateRequest = {
        title: parsedTitle.trim(),
        description: parsedDescription.trim() || null,
        discount_type: parsedDiscountType,
        discount_value: Number(parsedDiscountValue),
        minimum_purchase:
          parsedMinPurchase !== '' && !isNaN(Number(parsedMinPurchase))
            ? Number(parsedMinPurchase)
            : null,
        starts_at: startsAtIso,
        expires_at: expiresAtIso,
      };

      const created = await offersApi.createOffer(payload);

      // If requested, activate immediately
      if (activateImmediately) {
        await offersApi.activateOffer(created.id);
        setCreateSuccess(`Successfully created and activated "${created.title}"!`);
      } else {
        setCreateSuccess(`Successfully created "${created.title}" in Draft status.`);
      }

      setTimeout(() => {
        navigate('/app/shopkeeper/offers');
      }, 1200);
    } catch (err: any) {
      setParseError(err.message || 'Failed to create offer from parsed parameters.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="ai-create-page">
      {/* Banner */}
      <div className="ai-banner">
        <div className="ai-banner-icon">
          <Sparkles size={28} />
        </div>
        <div>
          <h1 className="ai-banner-title">AI Natural-Language Offer Studio</h1>
          <p className="ai-banner-subtitle">
            Describe your discount in everyday natural language. Our NLP engine will extract structured parameters for your review and confirmation.
          </p>
        </div>
      </div>

      {/* Notifications */}
      {createSuccess && (
        <div className="alert-box alert-success" role="alert">
          <CheckCircle2 size={18} className="alert-icon" />
          <span>{createSuccess} Redirecting to your Offers manager...</span>
        </div>
      )}
      {parseError && (
        <div className="alert-box alert-error" role="alert">
          <AlertTriangle size={18} className="alert-icon" />
          <span>{parseError}</span>
        </div>
      )}

      {/* Input Stage */}
      <div className="ai-input-card">
        <h2 className="ai-card-title">1. Describe Your Offer</h2>
        <form onSubmit={handleParse} className="ai-prompt-form">
          <div className="form-group">
            <textarea
              rows={3}
              placeholder="e.g. Give customers 20% off on all groceries when spending above 500 until this Sunday..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isParsing}
              className="form-input ai-textarea"
            />
          </div>

          {/* Preset Prompts */}
          <div className="ai-suggestions-row">
            <span className="suggestions-label">Try an example:</span>
            <div className="suggestions-list">
              {PROMPT_SUGGESTIONS.map((sug, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setInputText(sug)}
                  className="suggestion-chip"
                >
                  "{sug}"
                </button>
              ))}
            </div>
          </div>

          <div className="ai-action-row">
            <button
              type="submit"
              disabled={isParsing || !inputText.trim()}
              className="btn-primary"
            >
              {isParsing ? (
                <>
                  <div className="btn-spinner" />
                  <span>Analyzing with NLP...</span>
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  <span>Parse Offer</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Parsed & Confirmation Stage */}
      {parseResponse && (
        <div className="ai-parsed-review-card">
          <div className="parsed-card-header">
            <div className="header-meta-group">
              <h2 className="ai-card-title">2. Review & Confirm Parameters</h2>
              <div className="parser-badges-row">
                <span className="parser-tag-badge">
                  <Cpu size={13} />
                  <span>{parseResponse.parser_type === 'ai' ? 'AI Model' : 'Heuristic Engine'}</span>
                </span>
                {parseResponse.confidence !== null && parseResponse.confidence !== undefined && (
                  <span className="confidence-badge">
                    Confidence: {Math.round(parseResponse.confidence * 100)}%
                  </span>
                )}
                {parseResponse.needs_confirmation && (
                  <span className="confirmation-badge">
                    <HelpCircle size={13} /> Review Required
                  </span>
                )}
              </div>
            </div>
            <p className="parsed-sub">
              Check the extracted values below, adjust any fields as needed, then confirm creation.
            </p>
          </div>

          {/* Warnings Banner */}
          {parseResponse.warnings && parseResponse.warnings.length > 0 && (
            <div className="parser-warnings-box">
              <div className="warning-title-row">
                <AlertTriangle size={16} className="warning-icon" />
                <strong>Parser Notices & Clarifications:</strong>
              </div>
              <ul className="warnings-list">
                {parseResponse.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Editable Review Form */}
          <form onSubmit={handleConfirmAndCreate} className="parsed-edit-form">
            <div className="form-group">
              <label htmlFor="parsed-title">Offer Title *</label>
              <input
                id="parsed-title"
                type="text"
                value={parsedTitle}
                onChange={(e) => setParsedTitle(e.target.value)}
                required
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="parsed-desc">Description</label>
              <textarea
                id="parsed-desc"
                rows={2}
                value={parsedDescription}
                onChange={(e) => setParsedDescription(e.target.value)}
                className="form-input"
              />
            </div>

            <div className="form-row-dual">
              <div className="form-group">
                <label htmlFor="parsed-type">Discount Type</label>
                <select
                  id="parsed-type"
                  value={parsedDiscountType}
                  onChange={(e) => setParsedDiscountType(e.target.value as DiscountType)}
                  className="form-input"
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="fixed">Fixed Amount (₹)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="parsed-val">
                  Discount Value {parsedDiscountType === 'percentage' ? '(%)' : '(₹)'} *
                </label>
                <input
                  id="parsed-val"
                  type="number"
                  min={1}
                  max={parsedDiscountType === 'percentage' ? 100 : 10000}
                  value={parsedDiscountValue}
                  onChange={(e) => setParsedDiscountValue(Number(e.target.value))}
                  required
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="parsed-min">Minimum Purchase (₹, Optional)</label>
              <input
                id="parsed-min"
                type="number"
                min={0}
                placeholder="e.g. 500"
                value={parsedMinPurchase}
                onChange={(e) => setParsedMinPurchase(e.target.value)}
                className="form-input"
              />
            </div>

            <div className="form-row-dual">
              <div className="form-group">
                <label htmlFor="parsed-starts">Starts At</label>
                <input
                  id="parsed-starts"
                  type="datetime-local"
                  value={parsedStartsAt}
                  onChange={(e) => setParsedStartsAt(e.target.value)}
                  required
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="parsed-expires">Expires At</label>
                <input
                  id="parsed-expires"
                  type="datetime-local"
                  value={parsedExpiresAt}
                  onChange={(e) => setParsedExpiresAt(e.target.value)}
                  required
                  className="form-input"
                />
              </div>
            </div>

            {/* Immediate Activation Checkbox */}
            <div className="activation-checkbox-box">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={activateImmediately}
                  onChange={(e) => setActivateImmediately(e.target.checked)}
                />
                <span>
                  <strong>Activate immediately</strong> (make visible to Shoppers in Marketplace right away)
                </span>
              </label>
            </div>

            <div className="confirmation-actions-row">
              <button
                type="submit"
                disabled={isCreating}
                className="btn-primary btn-confirm"
              >
                {isCreating ? (
                  <>
                    <div className="btn-spinner" />
                    <span>Creating Offer...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={18} />
                    <span>Confirm & Launch Offer</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
