import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Store,
  ShoppingBag,
  CreditCard,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Tag,
  Clock,
  MapPin,
  Lock,
  Layers,
  Percent,
  Banknote,
  Search,
  BarChart3,
  Cpu,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { offersApi } from '../api/offers';
import { getRoleHomePath } from '../routes/ProtectedRoute';
import type { Offer } from '../types';

export const LandingPage: React.FC = () => {
  const { isAuthenticated, user, login } = useAuth();
  const navigate = useNavigate();

  const [publicOffers, setPublicOffers] = useState<Offer[]>([]);
  const [isLoadingOffers, setIsLoadingOffers] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'merchant' | 'shopper' | 'counter'>('merchant');

  useEffect(() => {
    let isMounted = true;
    offersApi
      .getPublicOffers()
      .then((data) => {
        if (isMounted) {
          setPublicOffers(data);
          setIsLoadingOffers(false);
        }
      })
      .catch(() => {
        if (isMounted) setIsLoadingOffers(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleQuickLogin = async (email: string) => {
    try {
      await login(email, 'DemoPassword123!');
      navigate('/app');
    } catch (err) {
      navigate('/login');
    }
  };

  const filteredOffers = publicOffers.filter((o) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      o.title.toLowerCase().includes(q) ||
      (o.description && o.description.toLowerCase().includes(q)) ||
      (o.shop_name && o.shop_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="landing-page-root">
      {/* 1. Global Navigation Bar */}
      <header className="landing-navbar">
        <div className="landing-nav-container">
          <Link to="/" className="landing-brand">
            <div className="brand-icon-box small">
              <Store size={20} className="brand-icon" />
            </div>
            <div className="brand-text">
              <span className="brand-title">Neighbourhood Offers</span>
              <span className="brand-sub">Hyperlocal Commerce Network</span>
            </div>
          </Link>

          <nav className="landing-nav-links">
            <a href="#live-offers" className="nav-item">Live Deals</a>
            <a href="#how-it-works" className="nav-item">How It Works</a>
            <a href="#merchant-value" className="nav-item">For Merchants</a>
            <a href="#architecture" className="nav-item">Architecture</a>
            <a href="#instant-access" className="nav-item">Portals</a>
          </nav>

          <div className="landing-nav-actions">
            {isAuthenticated && user ? (
              <Link to={getRoleHomePath(user.role)} className="btn-primary btn-sm">
                <span>Go to Dashboard</span>
                <ArrowRight size={14} />
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-secondary btn-sm">
                  Sign In
                </Link>
                <Link to="/register" className="btn-primary btn-sm">
                  <span>Register Free</span>
                  <ArrowRight size={14} />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="landing-hero-section">
        <div className="landing-hero-container">
          <div className="hero-badge">
            <Sparkles size={14} className="hero-badge-icon" />
            <span>Hyperlocal Footfall Commerce Network</span>
          </div>

          <h1 className="hero-headline">
            Turn Local Promotions Into <br />
            <span className="highlight-text">Real In-Store Footfall.</span>
          </h1>

          <p className="hero-description">
            The zero-waste discount platform for local commerce. Shoppers discover verified neighbourhood offers and claim free digital vouchers; merchants <strong>pay strictly for completed in-store checkouts</strong>, never for wasted advertising clicks.
          </p>

          <div className="hero-cta-group">
            <a href="#live-offers" className="btn-primary hero-btn-primary">
              <ShoppingBag size={18} />
              <span>Explore Live Neighbourhood Deals</span>
            </a>
            <Link to="/login" className="btn-secondary hero-btn-secondary">
              <Store size={18} />
              <span>Launch Merchant Studio</span>
            </Link>
          </div>

          {/* Key Value Metric Badges */}
          <div className="hero-stats-banner">
            <div className="stat-item">
              <div className="stat-icon-wrap">
                <CheckCircle2 size={18} className="text-success" />
              </div>
              <div>
                <strong>100% Verified Footfall</strong>
                <span>Points deduct only at checkout</span>
              </div>
            </div>

            <div className="stat-item">
              <div className="stat-icon-wrap">
                <ShieldCheck size={18} className="text-primary" />
              </div>
              <div>
                <strong>Single-Use Cryptographic Codes</strong>
                <span>Idempotent counter verification</span>
              </div>
            </div>

            <div className="stat-item">
              <div className="stat-icon-wrap">
                <Cpu size={18} className="text-warning" />
              </div>
              <div>
                <strong>AI Natural Language Studio</strong>
                <span>Create promotions in plain English</span>
              </div>
            </div>

            <div className="stat-item">
              <div className="stat-icon-wrap">
                <BarChart3 size={18} className="text-accent" />
              </div>
              <div>
                <strong>Row-Locked Points Ledger</strong>
                <span>PostgreSQL atomic transactions</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Live Interactive Offers Discovery Explorer */}
      <section id="live-offers" className="landing-section offers-preview-section">
        <div className="section-header">
          <span className="section-badge">Live Marketplace Preview</span>
          <h2 className="section-heading">Active Deals in Your Neighbourhood</h2>
          <p className="section-subheading">
            Browse real promotions active right now in Vijayawada. Claim vouchers for free and redeem them in-store.
          </p>
        </div>

        {/* Live Search Bar */}
        <div className="landing-search-container">
          <div className="search-input-wrapper">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search by shop name, grocery, fashion, or discount type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="filter-search-input"
            />
          </div>
          <span className="live-count-badge">
            {filteredOffers.length} {filteredOffers.length === 1 ? 'Offer' : 'Offers'} Available
          </span>
        </div>

        {/* Live Offers Grid */}
        <div className="offers-grid">
          {isLoadingOffers ? (
            <div className="loading-state-container">
              <div className="spinner" />
              <p>Loading live neighbourhood deals...</p>
            </div>
          ) : filteredOffers.length === 0 ? (
            <div className="empty-state-card">
              <ShoppingBag size={32} className="text-muted" />
              <h3>No matching offers found</h3>
              <p>Try searching with another keyword or explore our demo accounts.</p>
            </div>
          ) : (
            filteredOffers.map((offer) => (
              <div
                key={offer.id}
                className="offer-card"
              >
                <div className="offer-card-top">
                  <div className="offer-shop-badge">
                    <Store size={14} />
                    <span>{offer.shop_name || 'Local Store'}</span>
                  </div>
                  <div className="offer-discount-pill">
                    {offer.discount_type === 'percentage' ? (
                      <Percent size={14} />
                    ) : (
                      <Banknote size={14} />
                    )}
                    <span>
                      {offer.discount_type === 'percentage'
                        ? `${offer.discount_value}% OFF`
                        : `₹${offer.discount_value} OFF`}
                    </span>
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
                        ? `Min. Bill: ₹${offer.minimum_purchase}`
                        : 'No Minimum Spend'}
                    </span>
                  </div>
                  <div className="meta-item">
                    <Clock size={13} />
                    <span>
                      Valid until{' '}
                      {new Date(offer.expires_at).toLocaleDateString('en-IN', {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </div>
                </div>

                <div className="offer-card-footer">
                  <Link
                    to="/login"
                    className="btn-primary btn-claim"
                  >
                    <Tag size={15} />
                    <span>Sign In to Claim Voucher</span>
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 4. 4-Step Interactive Workflow */}
      <section id="how-it-works" className="landing-section workflow-section">
        <div className="section-header">
          <span className="section-badge">How It Works</span>
          <h2 className="section-heading">A Flawless Loop from Promotion to In-Store Sale</h2>
          <p className="section-subheading">
            How Neighbourhood Offers bridges online discovery with verified physical retail checkout.
          </p>
        </div>

        <div className="workflow-steps-grid">
          {/* Step 1 */}
          <div className="workflow-step-card">
            <div className="step-number-badge">01</div>
            <div className="step-icon-circle bg-amber">
              <Sparkles size={24} />
            </div>
            <h3 className="step-title">Merchant Launches Offer</h3>
            <p className="step-desc">
              Shopkeeper types a promotion in plain natural language (e.g. <em>"20% off groceries over ₹500"</em>). Our AI engine extracts structured parameters, minimum spend caps, and expiry dates.
            </p>
            <div className="step-tag">AI Natural-Language Studio</div>
          </div>

          {/* Step 2 */}
          <div className="workflow-step-card">
            <div className="step-number-badge">02</div>
            <div className="step-icon-circle bg-emerald">
              <Tag size={24} />
            </div>
            <h3 className="step-title">Shopper Claims Free Voucher</h3>
            <p className="step-desc">
              Nearby customers browse the local marketplace and claim exclusive discount codes. A single-use alphanumeric code (<code>NO-XXXXXX</code>) is instantly saved to their digital wallet.
            </p>
            <div className="step-tag">1-Click Claim Wallet</div>
          </div>

          {/* Step 3 */}
          <div className="workflow-step-card">
            <div className="step-number-badge">03</div>
            <div className="step-icon-circle bg-blue">
              <MapPin size={24} />
            </div>
            <h3 className="step-title">Customer Visits Physical Store</h3>
            <p className="step-desc">
              The customer visits the merchant's physical location, shops for products, and presents their active claim code to the counter staff at checkout.
            </p>
            <div className="step-tag">Verified In-Store Footfall</div>
          </div>

          {/* Step 4 */}
          <div className="workflow-step-card">
            <div className="step-number-badge">04</div>
            <div className="step-icon-circle bg-indigo">
              <CreditCard size={24} />
            </div>
            <h3 className="step-title">Instant POS Checkout & Deduct</h3>
            <p className="step-desc">
              Counter staff inputs the code and gross bill amount. The system validates terms atomically, calculates net customer bill, and deducts points from the shopkeeper's balance.
            </p>
            <div className="step-tag">Atomic Settlement & Receipt</div>
          </div>
        </div>
      </section>

      {/* 5. Merchant Value vs Traditional Advertising Comparison */}
      <section id="merchant-value" className="landing-section comparison-section">
        <div className="section-header">
          <span className="section-badge">The Merchant Advantage</span>
          <h2 className="section-heading">Pay for Footfall, Not for Advertising</h2>
          <p className="section-subheading">
            Traditional online ads charge for views and clicks that rarely enter your store. Neighbourhood Offers guarantees verified in-store footfall.
          </p>
        </div>

        <div className="comparison-dual-cards">
          {/* Traditional Ads Card */}
          <div className="comparison-card card-traditional">
            <div className="comparison-header">
              <span className="comp-tag old-way">Traditional Online Advertising</span>
              <h3>Paying for Clicks & Impressions</h3>
            </div>
            <ul className="comparison-list">
              <li className="comp-negative">
                <span className="cross-icon">✕</span>
                <span><strong>Upfront Cost:</strong> You pay money before any customer steps into your shop.</span>
              </li>
              <li className="comp-negative">
                <span className="cross-icon">✕</span>
                <span><strong>No Footfall Guarantee:</strong> High click-through rate with zero visits to your counter.</span>
              </li>
              <li className="comp-negative">
                <span className="cross-icon">✕</span>
                <span><strong>Unclear Attribution:</strong> Impossible to know which ad brought in which transaction.</span>
              </li>
              <li className="comp-negative">
                <span className="cross-icon">✕</span>
                <span><strong>Budget Drain:</strong> High CAC (Customer Acquisition Cost) with unpredictable return.</span>
              </li>
            </ul>
          </div>

          {/* Neighbourhood Offers Card */}
          <div className="comparison-card card-neighbourhood highlight-card">
            <div className="comparison-header">
              <span className="comp-tag new-way">Neighbourhood Offers Model</span>
              <h3>Pay Only When the Customer Pays</h3>
            </div>
            <ul className="comparison-list">
              <li className="comp-positive">
                <span className="check-icon">✓</span>
                <span><strong>Zero Waste:</strong> Impressions and voucher claims are 100% free to publish and claim.</span>
              </li>
              <li className="comp-positive">
                <span className="check-icon">✓</span>
                <span><strong>1 Point = ₹1 Real Discount:</strong> Points deduct strictly at checkout when the customer purchases.</span>
              </li>
              <li className="comp-positive">
                <span className="check-icon">✓</span>
                <span><strong>100% In-Store Attribution:</strong> Every discount is linked to a physical POS receipt and claim code.</span>
              </li>
              <li className="comp-positive">
                <span className="check-icon">✓</span>
                <span><strong>Complete Budget Control:</strong> Preload your platform budget and pause or resume offers at will.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 6. Interactive Tabbed Product Simulation */}
      <section className="landing-section product-preview-section">
        <div className="section-header">
          <span className="section-badge">Product Walkthrough</span>
          <h2 className="section-heading">Purpose-Built Portals for Every Role</h2>
          <p className="section-subheading">
            Explore how each role interacts with a streamlined, responsive interface.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="interactive-tabs-bar">
          <button
            type="button"
            onClick={() => setActiveTab('merchant')}
            className={`tab-btn-lg ${activeTab === 'merchant' ? 'active' : ''}`}
          >
            <Store size={18} />
            <span>Merchant AI Studio & Dashboard</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('shopper')}
            className={`tab-btn-lg ${activeTab === 'shopper' ? 'active' : ''}`}
          >
            <ShoppingBag size={18} />
            <span>Shopper Marketplace & Claim Wallet</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('counter')}
            className={`tab-btn-lg ${activeTab === 'counter' ? 'active' : ''}`}
          >
            <CreditCard size={18} />
            <span>Cashier POS Checkout Terminal</span>
          </button>
        </div>

        {/* Tab Content Display */}
        <div className="product-preview-box">
          {activeTab === 'merchant' && (
            <div className="preview-content-grid">
              <div className="preview-text-col">
                <span className="portal-pill badge-shopkeeper">Merchant Admin</span>
                <h3>AI Natural-Language Campaign Creation</h3>
                <p>
                  No complex advertising dashboards or multi-page forms. Type your promotion in plain language, review extracted parameters, and publish directly to nearby shoppers.
                </p>
                <div className="feature-bullets">
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>NLP parser with heuristic fallback engine</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Real-time points ledger with atomic top-ups</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Busy day footfall rankings and spend analytics</span>
                  </div>
                </div>
                <Link to="/login" className="btn-primary btn-sm">
                  <span>Try Merchant Studio</span>
                  <ArrowRight size={14} />
                </Link>
              </div>

              <div className="preview-mockup-col">
                <div className="mockup-window">
                  <div className="mockup-topbar">
                    <span className="dot dot-red" />
                    <span className="dot dot-amber" />
                    <span className="dot dot-green" />
                    <span className="mockup-title">AI Natural-Language Offer Studio</span>
                  </div>
                  <div className="mockup-body">
                    <div className="mock-prompt-box">
                      <span className="mock-label">Plain Natural Language Prompt</span>
                      <p className="mock-prompt-text">
                        "Give 20% discount on all fresh groceries for purchases over ₹500 valid until Sunday."
                      </p>
                    </div>
                    <div className="mock-extracted-card">
                      <div className="extracted-header">
                        <Sparkles size={14} className="text-warning" />
                        <strong>Extracted Parameters</strong>
                        <span className="confidence-tag">96% AI Confidence</span>
                      </div>
                      <div className="extracted-fields">
                        <div className="field-row">
                          <span>Discount:</span>
                          <strong>20% Percentage OFF</strong>
                        </div>
                        <div className="field-row">
                          <span>Min Spend:</span>
                          <strong>₹500.00</strong>
                        </div>
                        <div className="field-row">
                          <span>Status:</span>
                          <span className="status-pill pill-active">Ready to Launch</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'shopper' && (
            <div className="preview-content-grid">
              <div className="preview-text-col">
                <span className="portal-pill badge-shopper">Shopper Experience</span>
                <h3>Hyperlocal Discovery & Single-Use Vouchers</h3>
                <p>
                  Shoppers browse nearby neighborhood deals with transparent minimum spend rules. Claiming a voucher creates a dedicated single-use claim code that lives in their wallet until redemption.
                </p>
                <div className="feature-bullets">
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Real-time location and keyword filtering</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>One-click clipboard copy and QR-ready claim badge</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Status tracking across Active, Redeemed, and Expired</span>
                  </div>
                </div>
                <Link to="/login" className="btn-primary btn-sm">
                  <span>Open Shopper Marketplace</span>
                  <ArrowRight size={14} />
                </Link>
              </div>

              <div className="preview-mockup-col">
                <div className="mockup-window">
                  <div className="mockup-topbar">
                    <span className="dot dot-red" />
                    <span className="dot dot-amber" />
                    <span className="dot dot-green" />
                    <span className="mockup-title">My Claim Wallet</span>
                  </div>
                  <div className="mockup-body">
                    <div className="mock-voucher-card">
                      <div className="voucher-header">
                        <span className="voucher-shop">Anitha's Grocery</span>
                        <span className="voucher-pill">20% OFF</span>
                      </div>
                      <h4 className="voucher-title">Flat 20% on Grocery Bills &gt; ₹500</h4>
                      <div className="mock-code-box">
                        <span className="code-label">Show at checkout:</span>
                        <div className="code-display">NO-8K4P92</div>
                      </div>
                      <div className="voucher-footer">
                        <span>Expires in 4 days</span>
                        <span className="status-pill pill-claimed">Ready for Checkout</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'counter' && (
            <div className="preview-content-grid">
              <div className="preview-text-col">
                <span className="portal-pill badge-counter">Cashier POS</span>
                <h3>Instant POS Redemption & Receipt Calculation</h3>
                <p>
                  Counter staff can quickly process customer vouchers during billing. Simply enter the claim code and gross purchase amount; the system calculates the discounted total and gives an itemized receipt.
                </p>
                <div className="feature-bullets">
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Idempotency-protected submission prevents double-spending</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Automatic discount capping and min-spend enforcement</span>
                  </div>
                  <div className="bullet-row">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>Row-level database lock ensures zero ledger overdrafts</span>
                  </div>
                </div>
                <Link to="/login" className="btn-primary btn-sm">
                  <span>Access Counter Terminal</span>
                  <ArrowRight size={14} />
                </Link>
              </div>

              <div className="preview-mockup-col">
                <div className="mockup-window">
                  <div className="mockup-topbar">
                    <span className="dot dot-red" />
                    <span className="dot dot-amber" />
                    <span className="dot dot-green" />
                    <span className="mockup-title">POS Redemption Receipt</span>
                  </div>
                  <div className="mockup-body">
                    <div className="mock-receipt-card">
                      <div className="receipt-top">
                        <CheckCircle2 size={24} className="text-success" />
                        <strong>Redemption Approved</strong>
                        <span className="font-mono">NO-8K4P92</span>
                      </div>
                      <div className="receipt-lines">
                        <div className="line-row">
                          <span>Gross Purchase Bill:</span>
                          <span>₹1,200.00</span>
                        </div>
                        <div className="line-row text-success font-semibold">
                          <span>Discount Applied (20%):</span>
                          <span>-₹240.00</span>
                        </div>
                        <div className="line-row total-row">
                          <span>Customer Pays:</span>
                          <strong>₹960.00</strong>
                        </div>
                        <div className="line-row points-row">
                          <span>Points Deducted:</span>
                          <span>-240 pts</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 7. Architecture & Trust Guarantees */}
      <section id="architecture" className="landing-section architecture-section">
        <div className="section-header">
          <span className="section-badge">Engineering Excellence</span>
          <h2 className="section-heading">Built for High Concurrency & Financial Integrity</h2>
          <p className="section-subheading">
            Engineered with strict double-entry principles, row-level locking, and idempotency guarantees.
          </p>
        </div>

        <div className="tech-cards-grid">
          <div className="tech-card">
            <div className="tech-icon-circle bg-indigo">
              <Lock size={22} />
            </div>
            <h3>Atomic Row-Level Locking</h3>
            <p>
              Redemptions utilize PostgreSQL <code>SELECT ... FOR UPDATE</code> on the shop points row. Even under concurrent checkout traffic, balances are safely deducted without race conditions or overdrafts.
            </p>
          </div>

          <div className="tech-card">
            <div className="tech-icon-circle bg-emerald">
              <ShieldCheck size={22} />
            </div>
            <h3>Cryptographic Idempotency Keys</h3>
            <p>
              Every counter redemption accepts an <code>Idempotency-Key</code> header. Network retries or double clicks safely return the original transaction receipt rather than double-charging points.
            </p>
          </div>

          <div className="tech-card">
            <div className="tech-icon-circle bg-amber">
              <Cpu size={22} />
            </div>
            <h3>Resilient Dual NLP Parsing</h3>
            <p>
              Shopkeeper offer creation combines deep natural-language parsing with a deterministic regex heuristic engine, ensuring 100% uptime even if external AI services experience latency.
            </p>
          </div>

          <div className="tech-card">
            <div className="tech-icon-circle bg-blue">
              <Layers size={22} />
            </div>
            <h3>Strict RBAC & Tenant Isolation</h3>
            <p>
              Role-Based Access Control isolates merchant stores, cashier counters, and shoppers across authenticated JWT tokens, with 75 automated backend integration tests verifying every endpoint.
            </p>
          </div>
        </div>
      </section>

      {/* 8. Instant Role Portals & Demo Accounts */}
      <section id="instant-access" className="landing-section instant-access-section">
        <div className="section-header">
          <span className="section-badge">Live Enterprise Portals</span>
          <h2 className="section-heading">Instant Role Portals & Demonstration Accounts</h2>
          <p className="section-subheading">
            Evaluate the end-to-end platform immediately by choosing any pre-configured operational role.
          </p>
        </div>

        <div className="role-demo-cards-grid">
          {/* Shopkeeper */}
          <div className="role-demo-card card-shopkeeper">
            <div className="card-top-header">
              <div className="role-icon-box box-shopkeeper">
                <Store size={22} />
              </div>
              <span className="role-pill badge-shopkeeper">Merchant Admin</span>
            </div>

            <h3 className="role-card-title">Shopkeeper Portal</h3>
            <p className="role-card-desc">
              Create promotions with AI Studio, manage points ledger balance, and analyze footfall reports.
            </p>

            <div className="role-card-features">
              <span className="feat-chip">✓ AI Offer Studio</span>
              <span className="feat-chip">✓ Points Preload</span>
              <span className="feat-chip">✓ Busy Days Analytics</span>
            </div>

            <div className="role-card-actions">
              <button
                type="button"
                onClick={() => handleQuickLogin('anitha.demo@example.com')}
                className="btn-instant-login btn-shopkeeper"
              >
                <Zap size={14} />
                <span>Instant Access: Anitha (Grocery)</span>
                <ArrowRight size={14} />
              </button>
              <div className="secondary-user-row">
                <span className="alt-label">Alt Account:</span>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('rahul.demo@example.com')}
                  className="btn-alt-fill"
                >
                  Rahul (Fashion)
                </button>
              </div>
            </div>
          </div>

          {/* Shopper */}
          <div className="role-demo-card card-shopper">
            <div className="card-top-header">
              <div className="role-icon-box box-shopper">
                <ShoppingBag size={22} />
              </div>
              <span className="role-pill badge-shopper">Customer View</span>
            </div>

            <h3 className="role-card-title">Shopper Marketplace</h3>
            <p className="role-card-desc">
              Browse neighbourhood deals, claim instant voucher codes, and manage your claim wallet.
            </p>

            <div className="role-card-features">
              <span className="feat-chip">✓ Hyperlocal Deals</span>
              <span className="feat-chip">✓ 1-Click Voucher Claim</span>
              <span className="feat-chip">✓ Active Code Wallet</span>
            </div>

            <div className="role-card-actions">
              <button
                type="button"
                onClick={() => handleQuickLogin('priya.demo@example.com')}
                className="btn-instant-login btn-shopper"
              >
                <Zap size={14} />
                <span>Instant Access: Priya</span>
                <ArrowRight size={14} />
              </button>
              <div className="secondary-user-row">
                <span className="alt-label">Alt Account:</span>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('arjun.demo@example.com')}
                  className="btn-alt-fill"
                >
                  Arjun
                </button>
              </div>
            </div>
          </div>

          {/* Counter Staff */}
          <div className="role-demo-card card-counter">
            <div className="card-top-header">
              <div className="role-icon-box box-counter">
                <CreditCard size={22} />
              </div>
              <span className="role-pill badge-counter">Cashier POS</span>
            </div>

            <h3 className="role-card-title">Counter Staff POS Terminal</h3>
            <p className="role-card-desc">
              Validate claim codes at billing, calculate itemized receipts, and deduct platform points atomically.
            </p>

            <div className="role-card-features">
              <span className="feat-chip">✓ Rapid Code Lookup</span>
              <span className="feat-chip">✓ Auto Discount Math</span>
              <span className="feat-chip">✓ Idempotent Receipt</span>
            </div>

            <div className="role-card-actions">
              <button
                type="button"
                onClick={() => handleQuickLogin('ravi.demo@example.com')}
                className="btn-instant-login btn-counter"
              >
                <Zap size={14} />
                <span>Instant Access: Ravi</span>
                <ArrowRight size={14} />
              </button>
              <div className="secondary-user-row">
                <span className="alt-label">Alt Account:</span>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('meena.demo@example.com')}
                  className="btn-alt-fill"
                >
                  Meena
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 9. Final Call to Action */}
      <section className="landing-cta-banner">
        <div className="cta-banner-content">
          <h2 className="cta-headline">Ready to Experience Modern Hyperlocal Commerce?</h2>
          <p className="cta-sub">
            Join the neighbourhood retail revolution. Preload discount points, attract nearby footfall, and pay only for real checkouts.
          </p>
          <div className="cta-btn-row">
            <Link to="/register" className="btn-primary btn-lg">
              <span>Create Free Account</span>
              <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn-secondary btn-lg">
              <span>Sign In with Custom Credentials</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 10. Global Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-container">
          <div className="footer-brand-col">
            <div className="landing-brand">
              <div className="brand-icon-box small">
                <Store size={18} className="brand-icon" />
              </div>
              <span className="brand-title">Neighbourhood Offers</span>
            </div>
            <p className="footer-tagline">
              Turning local promotions into measurable in-store footfall across Vijayawada.
            </p>
          </div>

          <div className="footer-links-group">
            <div className="footer-col">
              <h4>Platform</h4>
              <a href="#live-offers">Live Offers</a>
              <a href="#how-it-works">How It Works</a>
              <a href="#merchant-value">Merchant Model</a>
              <a href="#architecture">Architecture</a>
            </div>

            <div className="footer-col">
              <h4>Portals</h4>
              <Link to="/login">Shopkeeper Studio</Link>
              <Link to="/login">Shopper Marketplace</Link>
              <Link to="/login">Counter POS Terminal</Link>
              <Link to="/register">Create Account</Link>
            </div>

            <div className="footer-col">
              <h4>Technology</h4>
              <span>FastAPI & Python 3.11</span>
              <span>React 18 & TypeScript</span>
              <span>PostgreSQL 15</span>
              <span>JWT & Argon2 Security</span>
            </div>
          </div>
        </div>

        <div className="footer-bottom-bar">
          <p>&copy; {new Date().getFullYear()} Neighbourhood Offers. Production-Grade Local Commerce Platform.</p>
        </div>
      </footer>
    </div>
  );
};
