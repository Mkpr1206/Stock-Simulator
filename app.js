// ── CONFIG ───────────────────────────────────────────────────────────
const API = 'http://localhost:8000';
let token = localStorage.getItem('stocksim_token');
let currentUser = null;
let currentTicker = null;
let currentPrice = 0;
let currentHolding = null;
let currentChartTicker = null;
let chartPeriod = '1mo';
let chartInterval = '1d';
let priceChartInstance = null;
let allocationChartInstance = null;
let allGlossaryTerms = [];
let currentLessonId = null;
let currentLesson = null;
let pendingModalAction = null;

// ── API ───────────────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null, auth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', '));
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Request failed');
  }
  return data;
}
async function apiForm(path, body) {
  const res = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(body).toString()
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed');
  return data;
}

// ── TOAST ─────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

// ── AUTH ──────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
  document.querySelector(`.auth-tab:nth-child(${tab === 'login' ? 1 : 2})`).classList.add('active');
  document.getElementById(tab + 'Form').classList.add('active');
  document.getElementById('authError').classList.add('hidden');
}

// ── Client-side validation helpers ──
function validateUsername(u) {
  if (!u) return 'Username is required';
  if (u.length < 3) return 'Username must be at least 3 characters';
  if (u.length > 30) return 'Username must be under 30 characters';
  if (!/^[a-zA-Z0-9_]+$/.test(u)) return 'Username can only contain letters, numbers, and underscores';
  return null;
}
function validateEmail(e) {
  if (!e) return 'Email is required';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return 'Please enter a valid email address';
  return null;
}
function validatePassword(p) {
  if (!p) return 'Password is required';
  if (p.length < 6) return 'Password must be at least 6 characters';
  return null;
}

function setAuthLoading(btn, loading) {
  btn.disabled = loading;
  btn.style.opacity = loading ? '0.6' : '1';
  btn.style.cursor = loading ? 'wait' : 'pointer';
  const span = btn.querySelector('span:first-child');
  if (span) span.textContent = loading ? 'PLEASE WAIT...' : btn.dataset.label;
}

async function login() {
  const username = document.getElementById('loginUsername').value.trim().toLowerCase();
  const password = document.getElementById('loginPassword').value;
  document.getElementById('authError').classList.add('hidden');

  // Client-side checks
  if (!username) return showAuthError('Please enter your username');
  if (!password)  return showAuthError('Please enter your password');

  const btn = document.querySelector('#loginForm .btn-primary');
  if (!btn.dataset.label) btn.dataset.label = 'ENTER MARKET';
  setAuthLoading(btn, true);

  try {
    const d = await apiForm('/auth/login', { username, password });
    if (!d.access_token) throw new Error('No token received — please try again');
    token = d.access_token;
    localStorage.setItem('stocksim_token', token);
    await enterApp();
  } catch(e) {
    // Friendlier messages for common cases
    const msg = e.message || '';
    if (msg.includes('fetch') || msg.includes('network') || msg.includes('Failed')) {
      showAuthError('Cannot connect to server. Make sure the backend is running (python main.py)');
    } else if (msg.includes('401') || msg.toLowerCase().includes('incorrect') || msg.toLowerCase().includes('invalid')) {
      showAuthError('Wrong username or password. Try demo_alice / demo1234');
    } else {
      showAuthError(msg || 'Login failed. Please try again.');
    }
  } finally {
    setAuthLoading(btn, false);
  }
}

async function register() {
  const username = document.getElementById('regUsername').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  document.getElementById('authError').classList.add('hidden');

  // Client-side validation first (before hitting server)
  const usernameErr = validateUsername(username);
  if (usernameErr) return showAuthError(usernameErr);
  const emailErr = validateEmail(email);
  if (emailErr) return showAuthError(emailErr);
  const passwordErr = validatePassword(password);
  if (passwordErr) return showAuthError(passwordErr);

  const btn = document.querySelector('#registerForm .btn-primary');
  if (!btn.dataset.label) btn.dataset.label = 'START WITH S$100,000';
  setAuthLoading(btn, true);

  try {
    const d = await api('/auth/register', 'POST', { username, email, password }, false);
    if (!d.access_token) throw new Error('Registration succeeded but no token received — please log in');
    token = d.access_token;
    localStorage.setItem('stocksim_token', token);
    await enterApp();
    toast('🎉 Welcome! You have S$100,000 SimBucks to start trading!', 'success');
  } catch(e) {
    const msg = e.message || '';
    if (msg.includes('fetch') || msg.includes('Failed to fetch')) {
      showAuthError('Cannot connect to server. Make sure the backend is running (python main.py)');
    } else if (msg.toLowerCase().includes('already') || msg.toLowerCase().includes('taken') || msg.toLowerCase().includes('exists')) {
      showAuthError('That username or email is already registered. Try logging in instead.');
    } else if (msg.toLowerCase().includes('email')) {
      showAuthError('Invalid email address. Please check and try again.');
    } else if (msg.toLowerCase().includes('username')) {
      showAuthError('Invalid username. Use letters, numbers and underscores only (3-30 chars).');
    } else if (msg.toLowerCase().includes('password')) {
      showAuthError('Password too weak. Use at least 6 characters.');
    } else {
      showAuthError(msg || 'Registration failed. Please try again.');
    }
  } finally {
    setAuthLoading(btn, false);
  }
}

function showAuthError(msg) {
  const el = document.getElementById('authError');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function logout() {
  localStorage.removeItem('stocksim_token');
  token = null; currentUser = null;
  document.getElementById('app').classList.remove('active');
  document.getElementById('splash').classList.add('active');
  // Clear any form values
  ['loginUsername','loginPassword','regUsername','regEmail','regPassword'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('authError').classList.add('hidden');
}

async function enterApp() {
  document.getElementById('splash').classList.remove('active');
  document.getElementById('app').classList.add('active');
  try {
    await loadCurrentUser();
  } catch(e) {
    // If loadCurrentUser fails (e.g. bad token), kick back to login
    console.warn('Could not load user after login:', e);
  }
  loadDashboard();
}
async function loadCurrentUser() {
  try {
    currentUser = await api('/auth/me');
    const u   = currentUser.username ?? '?';
    const xp  = currentUser.xp_points ?? currentUser.xp ?? 0;
    const lessons = currentUser.lessons_completed ?? currentUser.completed_lessons ?? 0;

    set('sidebarUsername', u);
    set('userAvatar',      u[0].toUpperCase());
    set('profileAvatar',   u[0].toUpperCase());
    set('profileUsername', u);
    set('profileEmail',    currentUser.email || '—');
    set('profileJoined',   fmtDate(currentUser.created_at ?? currentUser.joined_at));
    set('xpBadge',         `⭐ ${xp} XP`);
    set('profXp',          `${xp} XP`);
    set('profLessons',     `${lessons} / 10`);

    const totalVal = currentUser.portfolio_summary?.total_value
                  ?? currentUser.balance
                  ?? currentUser.wallet_balance
                  ?? 0;
    updateSidebarBalance(totalVal);
    updateGreeting(u);
  } catch(e) {
    console.warn('loadCurrentUser failed:', e.message);
  }
}
function updateSidebarBalance(v) { set('sidebarBalance', `S$${fmt(v)}`); }
function updateGreeting(u) {
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
  set('dashGreeting', `${g}, ${u}.`);
}

// ── NAVIGATION ────────────────────────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`panel-${name}`)?.classList.add('active');
  document.querySelector(`[data-panel="${name}"]`)?.classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'portfolio') loadPortfolio();
  if (name === 'watchlist') loadWatchlist();
  if (name === 'education') loadLessons();
  if (name === 'glossary') loadGlossary();
  if (name === 'leaderboard') loadLeaderboard();
  if (name === 'trade') loadTradeBalance();
  if (name === 'profile') loadProfile();
}

// ── DASHBOARD ─────────────────────────────────────────────────────────
async function loadDashboard() {
  loadFeatured();
  loadDashHoldings();
  loadSentiment();
  loadDashSummary();
}
async function loadDashSummary() {
  try {
    const p = await api('/portfolio');
    const total = p.total_value ?? p.portfolio_value ?? 0;
    const gl    = p.total_gain_loss ?? p.gain_loss ?? 0;
    const glPct = p.total_gain_loss_pct ?? p.gain_loss_pct ?? 0;
    set('headerTotalValue', `S$${fmt(total)}`);
    const pnlEl = document.getElementById('headerPnl');
    if (pnlEl) {
      pnlEl.textContent = `${gl >= 0 ? '+' : ''}S$${fmt(gl)} (${gl >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%)`;
      pnlEl.style.color = gl >= 0 ? 'var(--green)' : 'var(--red)';
    }
    updateSidebarBalance(total);
  } catch(e) { console.warn('Dashboard summary failed:', e.message); }
}
async function loadFeatured() {
  const grid = document.getElementById('featuredGrid');
  grid.innerHTML = '<div class="loading-row">Fetching live prices...</div>';
  try {
    const data = await api('/market/featured', 'GET', null, false);
    grid.innerHTML = '';
    data.forEach(item => {
      const chip = document.createElement('div');
      chip.className = 'ticker-chip';
      chip.innerHTML = `<div class="tc-symbol">${item.ticker}</div><div class="tc-price">${item.price > 0 ? '$' + item.price.toFixed(2) : '—'}</div>`;
      chip.onclick = () => { showPanel('trade'); selectTicker(item.ticker); };
      grid.appendChild(chip);
    });
  } catch(e) { grid.innerHTML = '<div class="loading-row">Could not load — is the server running?</div>'; }
}
async function loadSentiment() {
  try {
    const s = await api('/market/sentiment', 'GET', null, false);
    document.getElementById('sentimentFill').style.width = s.score + '%';
    set('sentimentValue', `${s.label} (${s.score}/100)`);
  } catch(e) {}
}
async function loadDashHoldings() {
  const el = document.getElementById('dashHoldings');
  try {
    const p = await api('/portfolio');
    const holdings = p.holdings ?? p.positions ?? [];
    if (!holdings.length) {
      el.innerHTML = '<div class="empty-state">No holdings yet. Head to Trade to buy your first stock!</div>';
      return;
    }
    el.innerHTML = '';
    holdings.slice(0, 6).forEach(h => {
      const gl    = h.gain_loss     ?? h.unrealized_gain ?? 0;
      const glPct = h.gain_loss_pct ?? h.gain_loss_percent ?? 0;
      const val   = h.current_value ?? h.market_value ?? 0;
      const cl = gl >= 0 ? 'var(--green)' : 'var(--red)';
      const div = document.createElement('div');
      div.className = 'dash-holding-row';
      div.innerHTML = `
        <div class="dh-left">
          <div class="dh-ticker" style="cursor:pointer" onclick="openChartFor('${h.ticker}')">${h.ticker}</div>
          <div class="dh-qty">${h.quantity} shares</div>
        </div>
        <div class="dh-right">
          <div class="dh-value">S$${fmt(val)}</div>
          <div class="dh-pnl" style="color:${cl}">${gl >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%</div>
        </div>`;
      el.appendChild(div);
    });
    // Tip
    try {
      const b = await api('/simulator/daily-briefing');
      if (b.tip_of_the_day) {
        set('tipText', b.tip_of_the_day);
        document.getElementById('tipSection').classList.remove('hidden');
      }
    } catch(e) {}
  } catch(e) {
    el.innerHTML = `<div class="empty-state" style="color:var(--red)">Could not load portfolio: ${e.message}</div>`;
  }
}

// ── TRADE ─────────────────────────────────────────────────────────────
async function loadTradeBalance() {
  try {
    const w = await api('/wallet');
    const bal = w.balance ?? w.cash ?? w.simBucks ?? 0;
    set('tradeBalance', `S$${fmt(Math.max(0, bal))}`);
  } catch(e) { set('tradeBalance', 'S$—'); }
}
function onDropdownSelect(val) {
  if (!val) return;
  document.getElementById('tradeTickerInput').value = val;
  selectTicker(val);
}
async function lookupStock() {
  const ticker = document.getElementById('tradeTickerInput').value.trim().toUpperCase();
  if (!ticker) return;
  await selectTicker(ticker);
}
async function selectTicker(ticker) {
  currentTicker = ticker.toUpperCase();
  document.getElementById('stockCard').classList.add('hidden');
  document.getElementById('actionRow').classList.add('hidden');
  document.getElementById('actionPanel').classList.add('hidden');
  document.getElementById('actionDropdown').value = '';
  hideAllActionPanels();

  // sync dropdown
  const dd = document.getElementById('tickerDropdown');
  if (dd) { for (let o of dd.options) { if (o.value === currentTicker) { dd.value = currentTicker; break; } } }

  try {
    const [info, priceData] = await Promise.all([
      api(`/market/info/${currentTicker}`, 'GET', null, false),
      api(`/market/price/${currentTicker}`, 'GET', null, false)
    ]);
    currentPrice = priceData.price || 0;
    set('infoTicker', currentTicker);
    set('infoName', info.name || currentTicker);
    set('infoSector', info.sector || '—');
    set('infoPrice', `$${currentPrice.toFixed(2)}`);
    set('infoPE', info.pe_ratio ? info.pe_ratio.toFixed(1) : '—');
    set('infoMktCap', info.market_cap ? '$' + fmtBig(info.market_cap) : '—');
    set('infoBeta', info.beta ? info.beta.toFixed(2) : '—');
    set('infoDivYield', info.dividend_yield ? (info.dividend_yield * 100).toFixed(2) + '%' : '0%');
    set('info52High', info.fifty_two_week_high ? '$' + info.fifty_two_week_high.toFixed(2) : '—');
    set('info52Low', info.fifty_two_week_low ? '$' + info.fifty_two_week_low.toFixed(2) : '—');
    set('infoDesc', info.description || '');
    document.getElementById('stockCard').classList.remove('hidden');
    document.getElementById('actionRow').classList.remove('hidden');

    // check if user holds this stock
    try {
      const portfolio = await api('/portfolio');
      currentHolding = portfolio.holdings?.find(h => h.ticker === currentTicker) || null;
    } catch(e) { currentHolding = null; }

    calcCost(); calcSellProceeds();
  } catch(e) {
    toast(`Could not load "${ticker}" — check spelling or server`, 'error');
  }
}

function onActionChange() {
  const action = document.getElementById('actionDropdown').value;
  hideAllActionPanels();
  if (!action) { document.getElementById('actionPanel').classList.add('hidden'); return; }
  document.getElementById('actionPanel').classList.remove('hidden');
  const block = document.getElementById(`ap-${action}`);
  if (block) {
    block.classList.remove('hidden');
    if (action === 'buy') setupBuyPanel();
    if (action === 'sell') setupSellPanel();
    if (action === 'limit_buy') setupLimitBuyPanel();
    if (action === 'limit_sell') setupLimitSellPanel();
  }
}

function hideAllActionPanels() {
  document.querySelectorAll('.ap-block').forEach(b => b.classList.add('hidden'));
}

function setupBuyPanel() {
  set('previewPrice', `S$${currentPrice.toFixed(2)}`);
  calcCost();
}

function setupSellPanel() {
  set('sellPreviewPrice', `S$${currentPrice.toFixed(2)}`);
  const banner = document.getElementById('holdingBanner');
  if (currentHolding) {
    banner.innerHTML = `<span>You own <strong>${currentHolding.quantity} shares</strong> of ${currentTicker} @ avg S$${fmt(currentHolding.avg_cost)}</span>`;
    banner.classList.remove('hidden');
    set('sellAvgCost', `S$${fmt(currentHolding.avg_cost)}`);
  } else {
    banner.innerHTML = `<span style="color:var(--red)">⚠ You don't own any ${currentTicker}</span>`;
    banner.classList.remove('hidden');
  }
  calcSellProceeds();
}

function setupLimitBuyPanel() {
  set('limitCurrent', `$${currentPrice.toFixed(2)}`);
}

function setupLimitSellPanel() {
  set('limitSellCurrent', `$${currentPrice.toFixed(2)}`);
}

function adjustQty(id, delta) {
  const inp = document.getElementById(id);
  const v = Math.max(1, (parseInt(inp.value) || 1) + delta);
  inp.value = v;
  if (id === 'execQty') calcCost();
  if (id === 'sellQty') calcSellProceeds();
  if (id === 'limitBuyQty') calcLimitCost();
}

async function calcCost() {
  const qty = parseInt(document.getElementById('execQty')?.value) || 1;
  set('previewQty', qty);
  if (!currentPrice) return;
  const total = currentPrice * qty;
  set('estCost', `S$${fmt(total)}`);
  try {
    const w = await api('/wallet');
    const after = w.balance - total;
    set('afterBalance', `S$${fmt(after)}`);
    document.getElementById('afterBalance').style.color = after >= 0 ? 'var(--text)' : 'var(--red)';
  } catch(e) {}
}

function calcSellProceeds() {
  const qty = parseInt(document.getElementById('sellQty')?.value) || 1;
  if (!currentPrice) return;
  const proceeds = currentPrice * qty;
  set('sellProceeds', `S$${fmt(proceeds)}`);
  if (currentHolding) {
    const pnl = (currentPrice - currentHolding.avg_cost) * qty;
    const pnlEl = document.getElementById('sellPnl');
    if (pnlEl) {
      pnlEl.textContent = `${pnl >= 0 ? '+' : ''}S$${fmt(pnl)}`;
      pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';
    }
  }
}

function calcLimitCost() {
  const price = parseFloat(document.getElementById('limitBuyPrice')?.value) || 0;
  const qty = parseInt(document.getElementById('limitBuyQty')?.value) || 1;
  set('limitTarget', price ? `S$${price.toFixed(2)}` : '—');
  set('limitReserved', price ? `S$${fmt(price * qty)}` : '—');
}

function sellAllShares() {
  if (currentHolding) {
    document.getElementById('sellQty').value = currentHolding.quantity;
    calcSellProceeds();
  }
}

async function executeTrade(mode) {
  if (!currentTicker) return toast('No stock selected', 'error');
  const qtyId = mode === 'buy' ? 'execQty' : 'sellQty';
  const qty = parseFloat(document.getElementById(qtyId)?.value);
  if (!qty || qty <= 0) return toast('Enter a valid quantity', 'error');
  const resultId = mode === 'buy' ? 'tradeResult' : 'sellResult';
  const resultEl = document.getElementById(resultId);
  resultEl.classList.add('hidden');
  try {
    const res = await api(`/trade/${mode}`, 'POST', { ticker: currentTicker, quantity: qty });
    resultEl.className = 'trade-result success';
    resultEl.textContent = res.message;
    resultEl.classList.remove('hidden');
    toast(res.message, 'success');
    loadTradeBalance();
    updateSidebarBalance(res.new_balance || 0);
    // refresh holding info
    try {
      const portfolio = await api('/portfolio');
      currentHolding = portfolio.holdings?.find(h => h.ticker === currentTicker) || null;
      if (mode === 'sell') setupSellPanel();
    } catch(e) {}
  } catch(e) {
    resultEl.className = 'trade-result error';
    resultEl.textContent = e.message;
    resultEl.classList.remove('hidden');
    toast(e.message, 'error');
  }
}

async function placeLimitOrder(type) {
  if (!currentTicker) return toast('No stock selected', 'error');
  const priceId = type === 'buy' ? 'limitBuyPrice' : 'limitSellPrice';
  const qtyId   = type === 'buy' ? 'limitBuyQty'   : 'limitSellQty';
  const resId    = type === 'buy' ? 'limitBuyResult' : 'limitSellResult';
  const price = parseFloat(document.getElementById(priceId)?.value);
  const qty   = parseInt(document.getElementById(qtyId)?.value);
  if (!price || !qty) return toast('Fill in price and quantity', 'error');
  const resultEl = document.getElementById(resId);
  try {
    const path = type === 'buy' ? '/orders/limit-buy' : '/orders/limit-sell';
    const res = await api(path, 'POST', { ticker: currentTicker, quantity: qty, limit_price: price });
    resultEl.className = 'trade-result success';
    resultEl.textContent = res.message;
    resultEl.classList.remove('hidden');
    toast(res.message, 'success');
    loadPendingOrders();
  } catch(e) {
    resultEl.className = 'trade-result error';
    resultEl.textContent = e.message;
    resultEl.classList.remove('hidden');
    toast(e.message, 'error');
  }
}

async function addCurrentToWatchlist() {
  if (!currentTicker) return;
  const resultEl = document.getElementById('watchlistResult');
  try {
    await api('/watchlist', 'POST', { ticker: currentTicker });
    resultEl.className = 'trade-result success';
    resultEl.textContent = `✓ ${currentTicker} added to your watchlist`;
    resultEl.classList.remove('hidden');
    toast(`${currentTicker} added to watchlist`, 'success');
  } catch(e) {
    resultEl.className = 'trade-result error';
    resultEl.textContent = e.message;
    resultEl.classList.remove('hidden');
  }
}

async function loadPendingOrders() {
  const el = document.getElementById('pendingOrders');
  try {
    const orders = await api('/orders/pending');
    if (!orders.length) { el.innerHTML = '<div class="empty-state">No pending orders</div>'; return; }
    el.innerHTML = '';
    orders.forEach(o => {
      const div = document.createElement('div');
      div.className = 'order-row';
      div.innerHTML = `
        <div class="order-info">
          <span class="order-action ${o.action === 'BUY' ? 'tag-buy' : 'tag-sell'}">${o.action}</span>
          <strong>${o.quantity}x ${o.ticker}</strong> @ S$${o.limit_price?.toFixed(2)}
        </div>
        <button class="btn-cancel" onclick="cancelOrder(${o.id})">CANCEL</button>`;
      el.appendChild(div);
    });
  } catch(e) { el.innerHTML = '<div class="empty-state">Could not load orders</div>'; }
}

async function cancelOrder(id) {
  try {
    await api(`/orders/${id}`, 'DELETE');
    toast('Order cancelled', 'info');
    loadPendingOrders();
  } catch(e) { toast(e.message, 'error'); }
}

// ── CHARTS ────────────────────────────────────────────────────────────
function chartTickerChanged(val) {
  if (!val) return;
  currentChartTicker = val;
  document.getElementById('chartTickerInput').value = val;
  loadChart();
}

function loadChart() {
  const inp = document.getElementById('chartTickerInput').value.trim().toUpperCase();
  const dd  = document.getElementById('chartDropdown').value;
  currentChartTicker = inp || dd;
  if (!currentChartTicker) return;
  fetchChart();
}

function setPeriod(period, interval, btn) {
  chartPeriod = period; chartInterval = interval;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (currentChartTicker) fetchChart();
}

async function fetchChart() {
  document.getElementById('chartEmpty').classList.add('hidden');
  document.getElementById('chartArea').classList.add('hidden');
  document.getElementById('chartLoading').classList.remove('hidden');

  try {
    const [hist, priceData, info] = await Promise.all([
      api(`/market/history/${currentChartTicker}?period=${chartPeriod}&interval=${chartInterval}`, 'GET', null, false),
      api(`/market/price/${currentChartTicker}`, 'GET', null, false),
      api(`/market/info/${currentChartTicker}`, 'GET', null, false).catch(() => ({}))
    ]);

    document.getElementById('chartLoading').classList.add('hidden');
    document.getElementById('chartArea').classList.remove('hidden');

    const price = priceData.price || 0;
    set('chartTickerLabel', currentChartTicker);
    set('chartNameLabel', info.name || currentChartTicker);
    set('chartCurrentPrice', `$${price.toFixed(2)}`);

    // Build data arrays
    const labels = hist.dates || Object.keys(hist.close || {});
    const closes = hist.close ? (Array.isArray(hist.close) ? hist.close : Object.values(hist.close)) : [];

    if (closes.length > 1) {
      const first = closes[0];
      const last  = closes[closes.length - 1];
      const change = last - first;
      const changePct = ((change / first) * 100).toFixed(2);
      const changeEl = document.getElementById('chartChange');
      changeEl.textContent = `${change >= 0 ? '+' : ''}$${Math.abs(change).toFixed(2)} (${change >= 0 ? '+' : ''}${changePct}%)`;
      changeEl.style.color = change >= 0 ? 'var(--green)' : 'var(--red)';
      set('chartChangePct', `${change >= 0 ? '+' : ''}${changePct}%`);
      document.getElementById('chartChangePct').style.color = change >= 0 ? 'var(--green)' : 'var(--red)';
      set('chartHigh', `$${Math.max(...closes).toFixed(2)}`);
      set('chartLow',  `$${Math.min(...closes).toFixed(2)}`);
    }

    const volumes = hist.volume ? (Array.isArray(hist.volume) ? hist.volume : Object.values(hist.volume)) : [];
    if (volumes.length) set('chartVolume', fmtBig(volumes.reduce((a, b) => a + b, 0) / volumes.length));

    drawPriceChart(labels, closes);
  } catch(e) {
    document.getElementById('chartLoading').classList.add('hidden');
    document.getElementById('chartEmpty').classList.remove('hidden');
    document.getElementById('chartEmpty').textContent = `Could not load chart for "${currentChartTicker}". Try another ticker.`;
    toast(e.message, 'error');
  }
}

function drawPriceChart(labels, data) {
  const ctx = document.getElementById('priceChart').getContext('2d');
  if (priceChartInstance) priceChartInstance.destroy();

  const isUp = data.length > 1 && data[data.length - 1] >= data[0];
  const color = isUp ? '#00d4aa' : '#ff4560';

  priceChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: currentChartTicker,
        data,
        borderColor: color,
        backgroundColor: isUp ? 'rgba(0,212,170,0.08)' : 'rgba(255,69,96,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f1217',
          borderColor: '#1e2530',
          borderWidth: 1,
          titleColor: '#8896a8',
          bodyColor: '#e2e8f0',
          callbacks: {
            label: ctx => ` $${ctx.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#4a5568', font: { family: 'Space Mono', size: 10 }, maxTicksLimit: 8 },
          grid: { color: '#1e2530' }
        },
        y: {
          position: 'right',
          ticks: { color: '#8896a8', font: { family: 'Space Mono', size: 10 }, callback: v => '$' + v.toFixed(0) },
          grid: { color: '#1e2530' }
        }
      }
    }
  });
}

function goTradeFromChart(action) {
  if (!currentChartTicker) return;
  showPanel('trade');
  document.getElementById('tradeTickerInput').value = currentChartTicker;
  selectTicker(currentChartTicker).then(() => {
    document.getElementById('actionDropdown').value = action;
    onActionChange();
  });
}

// ── PORTFOLIO ─────────────────────────────────────────────────────────
async function loadPortfolio() {
  // Reset summary to loading state
  ['portTotalValue','portCash','portInvested','portPnl'].forEach(id => set(id, '...'));

  try {
    const p = await api('/portfolio');

    // Handle both possible field names from backend
    const totalValue   = p.total_value   ?? p.portfolio_value ?? 0;
    const cash         = p.cash          ?? p.cash_balance    ?? 0;
    const invested     = p.invested_value ?? p.stocks_value   ?? 0;
    const gainLoss     = p.total_gain_loss ?? p.gain_loss     ?? 0;
    const gainLossPct  = p.total_gain_loss_pct ?? p.gain_loss_pct ?? 0;
    const holdings     = p.holdings      ?? p.positions       ?? [];

    set('portTotalValue', `S$${fmt(totalValue)}`);
    set('portCash', `S$${fmt(cash)}`);
    set('portInvested', `S$${fmt(invested)}`);

    const pnlEl = document.getElementById('portPnl');
    if (pnlEl) {
      pnlEl.textContent = `${gainLoss >= 0 ? '+' : ''}S$${fmt(gainLoss)} (${gainLoss >= 0 ? '+' : ''}${(gainLossPct || 0).toFixed(2)}%)`;
      pnlEl.style.color = gainLoss >= 0 ? 'var(--green)' : 'var(--red)';
    }

    // Holdings table
    const tbody = document.getElementById('holdingsTbody');
    if (!holdings.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-row">No holdings yet — go to Trade to buy your first stock!</td></tr>';
      document.getElementById('allocationLegend').innerHTML = '<div class="empty-state" style="border:none;padding:8px">No holdings to display</div>';
    } else {
      tbody.innerHTML = '';
      holdings.forEach(h => {
        const gl     = h.gain_loss      ?? h.unrealized_gain ?? 0;
        const glPct  = h.gain_loss_pct  ?? h.gain_loss_percent ?? 0;
        const avgCost= h.avg_cost       ?? h.average_cost ?? h.cost_basis ?? 0;
        const curPx  = h.current_price  ?? h.price ?? 0;
        const curVal = h.current_value  ?? h.market_value ?? 0;
        const cl = gl >= 0 ? 'pos' : 'neg';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong style="cursor:pointer;color:var(--accent)" onclick="openChartFor('${h.ticker}')">${h.ticker}</strong></td>
          <td>${h.quantity}</td>
          <td>S$${fmt(avgCost)}</td>
          <td>S$${fmt(curPx)}</td>
          <td>S$${fmt(curVal)}</td>
          <td class="${cl}">${gl >= 0 ? '+' : ''}S$${fmt(gl)}</td>
          <td class="${cl}">${glPct >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%</td>
          <td><button class="quick-sell" onclick="quickSell('${h.ticker}',${h.quantity})">SELL ALL</button></td>`;
        tbody.appendChild(tr);
      });
      drawAllocationChart(holdings, cash);
    }
    updateSidebarBalance(totalValue);

    // Also update profile stats if visible
    set('profTotalValue', `S$${fmt(totalValue)}`);
    set('profCash', `S$${fmt(cash)}`);
    const profPnl = document.getElementById('profPnl');
    if (profPnl) { profPnl.textContent = `${gainLoss >= 0 ? '+' : ''}S$${fmt(gainLoss)}`; profPnl.style.color = gainLoss >= 0 ? 'var(--green)' : 'var(--red)'; }

  } catch(e) {
    console.error('Portfolio load error:', e);
    ['portTotalValue','portCash','portInvested'].forEach(id => set(id, '—'));
    document.getElementById('holdingsTbody').innerHTML =
      `<tr><td colspan="8" class="loading-row" style="color:var(--red)">Failed to load portfolio: ${e.message}</td></tr>`;
  }

  // Trade history
  try {
    const trades = await api('/portfolio/trades?limit=50');
    const list = Array.isArray(trades) ? trades : (trades.trades ?? trades.history ?? []);
    const tbody2 = document.getElementById('tradeHistoryTbody');
    if (!list.length) {
      tbody2.innerHTML = '<tr><td colspan="6" class="loading-row">No trades yet</td></tr>';
    } else {
      tbody2.innerHTML = '';
      list.forEach(t => {
        const action = t.action ?? t.trade_type ?? t.type ?? '—';
        const ts     = t.executed_at ?? t.timestamp ?? t.created_at ?? null;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${fmtDate(ts)}</td>
          <td class="${action === 'BUY' ? 'tag-buy' : 'tag-sell'}">${action}</td>
          <td><strong>${t.ticker}</strong></td>
          <td>${t.quantity}</td>
          <td>S$${fmt(t.price)}</td>
          <td>S$${fmt(t.total_value ?? t.total ?? (t.price * t.quantity))}</td>`;
        tbody2.appendChild(tr);
      });
    }
  } catch(e) {
    document.getElementById('tradeHistoryTbody').innerHTML =
      `<tr><td colspan="6" class="loading-row" style="color:var(--red)">Failed to load history: ${e.message}</td></tr>`;
  }
}

function drawAllocationChart(holdings, cash) {
  const ctx = document.getElementById('allocationChart')?.getContext('2d');
  if (!ctx) return;
  if (allocationChartInstance) allocationChartInstance.destroy();

  const colors = ['#00d4aa','#0099ff','#f5c842','#ff4560','#a855f7','#f97316','#22d3ee','#84cc16','#ec4899','#6366f1'];
  const labels = [...holdings.map(h => h.ticker)];
  const data   = [...holdings.map(h => h.current_value)];
  if (cash > 0) { labels.push('CASH'); data.push(cash); }

  allocationChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderColor: '#0a0c0f', borderWidth: 3, hoverOffset: 6 }]
    },
    options: {
      responsive: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f1217',
          callbacks: {
            label: ctx => ` S$${fmt(ctx.parsed)} (${((ctx.parsed / data.reduce((a,b)=>a+b,0))*100).toFixed(1)}%)`
          }
        }
      }
    }
  });

  // Legend
  const legend = document.getElementById('allocationLegend');
  legend.innerHTML = '';
  labels.forEach((l, i) => {
    const total = data.reduce((a,b)=>a+b,0);
    const pct = ((data[i]/total)*100).toFixed(1);
    const div = document.createElement('div');
    div.className = 'al-item';
    div.innerHTML = `<span class="al-dot" style="background:${colors[i % colors.length]}"></span><span class="al-name">${l}</span><span class="al-pct">${pct}%</span>`;
    legend.appendChild(div);
  });
}

function openChartFor(ticker) {
  currentChartTicker = ticker;
  document.getElementById('chartTickerInput').value = ticker;
  showPanel('charts');
  fetchChart();
}

async function quickSell(ticker, qty) {
  if (!confirm(`Sell all ${qty} shares of ${ticker}?`)) return;
  try {
    const res = await api('/trade/sell', 'POST', { ticker, quantity: qty });
    toast(res.message, 'success');
    loadPortfolio();
  } catch(e) { toast(e.message, 'error'); }
}

function confirmReset() {
  set('modalTitle', 'Reset Portfolio?');
  set('modalMessage', 'This clears ALL holdings and restores your balance to S$100,000. Trade history is kept. Cannot be undone.');
  pendingModalAction = resetPortfolio;
  document.getElementById('modal').classList.remove('hidden');
}
function closeModal() { document.getElementById('modal').classList.add('hidden'); pendingModalAction = null; }
function modalConfirm() { closeModal(); if (pendingModalAction) pendingModalAction(); }
async function resetPortfolio() {
  try {
    const r = await api('/wallet/reset', 'POST');
    toast(r.message, 'success');
    loadPortfolio(); loadDashboard();
    updateSidebarBalance(r.new_balance);
  } catch(e) { toast(e.message, 'error'); }
}

// ── WATCHLIST ─────────────────────────────────────────────────────────
async function loadWatchlist() {
  const el = document.getElementById('watchlistItems');
  try {
    const items = await api('/watchlist');
    if (!items.length) { el.innerHTML = '<div class="empty-state">Your watchlist is empty. Add tickers above.</div>'; return; }
    el.innerHTML = '';
    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'watchlist-item';
      div.innerHTML = `
        <div>
          <div class="wi-ticker" style="cursor:pointer" onclick="openChartFor('${item.ticker}')">${item.ticker}</div>
          <div class="wi-added">Added ${fmtDate(item.added_at)}</div>
        </div>
        <div style="display:flex;align-items:center;gap:16px">
          <div class="wi-price">${item.current_price > 0 ? '$' + item.current_price.toFixed(2) : '—'}</div>
          <button class="btn-remove" onclick="removeFromWatchlist('${item.ticker}')">✕</button>
        </div>`;
      el.appendChild(div);
    });
  } catch(e) { el.innerHTML = '<div class="empty-state">Could not load watchlist</div>'; }
}
async function addToWatchlist() {
  const ticker = document.getElementById('watchlistInput').value.trim().toUpperCase();
  if (!ticker) return;
  try {
    await api('/watchlist', 'POST', { ticker });
    document.getElementById('watchlistInput').value = '';
    toast(`${ticker} added to watchlist`, 'success');
    loadWatchlist();
  } catch(e) { toast(e.message, 'error'); }
}
async function removeFromWatchlist(ticker) {
  try {
    await api(`/watchlist/${ticker}`, 'DELETE');
    toast(`${ticker} removed`, 'info');
    loadWatchlist();
  } catch(e) { toast(e.message, 'error'); }
}

// ── EDUCATION ─────────────────────────────────────────────────────────
async function loadLessons() {
  document.getElementById('lessonsList').classList.remove('hidden');
  document.getElementById('lessonDetail').classList.add('hidden');
  const el = document.getElementById('lessonsList');
  el.innerHTML = '<div class="loading-row">Loading lessons...</div>';
  try {
    const [lessons, progress] = await Promise.all([
      api('/education/lessons', 'GET', null, false),
      api('/education/progress').catch(() => [])
    ]);
    const completedIds = new Set(progress.filter(p => p.completed).map(p => p.lesson_id));
    const completedCount = completedIds.size;
    const pct = (completedCount / 10) * 100;
    document.getElementById('progressFill').style.width = pct + '%';
    set('progressLabel', `${completedCount} / 10 lessons completed`);
    el.innerHTML = '';
    lessons.forEach(l => {
      const done = completedIds.has(l.id);
      const diffClass = `diff-${l.difficulty.toLowerCase()}`;
      const card = document.createElement('div');
      card.className = `lesson-card${done ? ' lesson-done' : ''}`;
      card.innerHTML = `
        <div class="lesson-card-top">
          <div class="lesson-num">${String(l.id).padStart(2,'0')}</div>
          <div class="lesson-xp-badge">+${l.xp_reward} XP</div>
        </div>
        <div class="lesson-title-card">${l.title}</div>
        <div class="lesson-meta-row">
          <span class="difficulty-badge ${diffClass}">${l.difficulty.toUpperCase()}</span>
          <span class="lesson-time">~${l.estimated_minutes} min</span>
        </div>
        ${done ? '<div class="lesson-complete-badge">✓ COMPLETED</div>' : ''}`;
      card.onclick = () => openLesson(l.id);
      el.appendChild(card);
    });
  } catch(e) { el.innerHTML = '<div class="empty-state">Could not load lessons. Is the server running?</div>'; }
}

async function openLesson(id) {
  document.getElementById('lessonsList').classList.add('hidden');
  document.getElementById('lessonDetail').classList.remove('hidden');
  currentLessonId = id;
  set('lessonBody', '<div class="loading-row">Loading lesson...</div>');
  document.getElementById('quizSection').classList.add('hidden');
  document.getElementById('quizResult').classList.add('hidden');
  try {
    const l = await api(`/education/lessons/${id}`, 'GET', null, false);
    currentLesson = l;
    const diffClass = `diff-${l.difficulty.toLowerCase()}`;
    document.getElementById('lessonDifficulty').className = `difficulty-badge ${diffClass}`;
    set('lessonDifficulty', l.difficulty.toUpperCase());
    set('lessonXP', `+${l.xp_reward} XP on completion`);
    set('lessonTitle', l.title);
    document.getElementById('lessonBody').innerHTML = renderMarkdown(l.content || '');
    if (l.quiz?.length) { buildQuiz(l.quiz); document.getElementById('quizSection').classList.remove('hidden'); }
  } catch(e) { toast('Could not load lesson', 'error'); }
}

function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^✅ (.+)$/gm, '<p class="md-good">✅ $1</p>')
    .replace(/^❌ (.+)$/gm, '<p class="md-bad">❌ $1</p>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hpuol])(.+)$/gm, '<p>$1</p>');
}

function buildQuiz(questions) {
  const el = document.getElementById('quizQuestions');
  el.innerHTML = '';
  questions.forEach((q, qi) => {
    const div = document.createElement('div');
    div.className = 'quiz-q';
    div.innerHTML = `<div class="quiz-q-text">Q${qi + 1}. ${q.question}</div>`;
    q.options.forEach((opt, oi) => {
      const label = document.createElement('label');
      label.className = 'quiz-option';
      label.innerHTML = `<input type="radio" name="q${qi}" value="${oi}"> ${opt}`;
      label.onclick = () => {
        document.querySelectorAll(`[name="q${qi}"]`).forEach(r => r.closest('.quiz-option').classList.remove('selected'));
        label.classList.add('selected');
      };
      div.appendChild(label);
    });
    el.appendChild(div);
  });
}

async function submitQuiz() {
  const answers = [];
  for (let i = 0; i < (currentLesson?.quiz?.length || 0); i++) {
    const sel = document.querySelector(`[name="q${i}"]:checked`);
    answers.push(sel ? parseInt(sel.value) : -1);
  }
  try {
    const result = await api(`/education/lessons/${currentLessonId}/quiz`, 'POST', { answers });
    const el = document.getElementById('quizResult');
    el.className = result.passed ? 'quiz-pass' : 'quiz-fail';
    let html = `<div class="quiz-score">${result.score_pct}%</div>`;
    html += `<div class="quiz-verdict">${result.passed ? '🎉 Passed!' : '📚 Keep studying'}</div>`;
    html += `<p>${result.message}</p>`;
    if (result.passed) html += `<div class="xp-earned">+${result.xp_earned} XP earned!</div>`;
    result.feedback?.forEach(f => {
      html += `<div class="feedback-item ${f.is_correct ? 'fb-correct' : 'fb-wrong'}">
        <div>${f.is_correct ? '✓' : '✗'} ${f.question}</div>
        <div class="fb-explanation">${f.explanation}</div>
      </div>`;
    });
    el.innerHTML = html;
    el.classList.remove('hidden');
    document.getElementById('submitQuizBtn').classList.add('hidden');
    if (result.passed) {
      set('xpBadge', `⭐ ${(currentUser?.xp_points || 0) + result.xp_earned} XP`);
    }
  } catch(e) { toast(e.message, 'error'); }
}

function closeLessonDetail() { loadLessons(); }

// ── GLOSSARY ──────────────────────────────────────────────────────────
async function loadGlossary() {
  const el = document.getElementById('glossaryList');
  try {
    allGlossaryTerms = await api('/education/glossary', 'GET', null, false);
    renderGlossary(allGlossaryTerms);
  } catch(e) { el.innerHTML = '<div class="empty-state">Could not load glossary</div>'; }
}
function renderGlossary(terms) {
  const el = document.getElementById('glossaryList');
  el.innerHTML = '';
  if (!terms.length) { el.innerHTML = '<div class="empty-state">No results found</div>'; return; }
  terms.forEach(t => {
    const div = document.createElement('div');
    div.className = 'glossary-item';
    div.innerHTML = `
      <div class="glossary-term">${t.term}</div>
      <div class="glossary-def">${t.definition}</div>
      ${t.example ? `<div class="glossary-example">Example: ${t.example}</div>` : ''}`;
    el.appendChild(div);
  });
}
function searchGlossary() {
  const q = document.getElementById('glossarySearch').value.toLowerCase();
  const filtered = allGlossaryTerms.filter(t =>
    t.term.toLowerCase().includes(q) || t.definition.toLowerCase().includes(q)
  );
  renderGlossary(filtered);
}

// ── LEADERBOARD ───────────────────────────────────────────────────────
async function loadLeaderboard() {
  const tbody = document.getElementById('leaderboardTbody');
  const cs    = document.getElementById('communityStats');
  tbody.innerHTML = '<tr><td colspan="6" class="loading-row">Loading...</td></tr>';
  cs.innerHTML    = '<div class="loading-row">Loading stats...</div>';

  try {
    const [boardRaw, statsRaw] = await Promise.all([
      api('/leaderboard', 'GET', null, false),
      api('/leaderboard/stats', 'GET', null, false)
    ]);

    // Handle array or wrapped response
    const board = Array.isArray(boardRaw) ? boardRaw : (boardRaw.leaderboard ?? boardRaw.users ?? []);
    const stats = statsRaw ?? {};

    cs.innerHTML = `
      <div class="cs-card"><div class="cs-label">TOTAL TRADERS</div><div class="cs-val">${stats.total_traders ?? stats.total_users ?? board.length}</div></div>
      <div class="cs-card"><div class="cs-label">TOTAL TRADES</div><div class="cs-val">${stats.total_trades ?? '—'}</div></div>
      <div class="cs-card"><div class="cs-label">AVG BALANCE</div><div class="cs-val">S$${fmt(stats.average_balance ?? stats.avg_balance ?? 0)}</div></div>`;

    // My rank (non-critical — don't let it break the page)
    try {
      const myRank = await api('/leaderboard/me');
      if (myRank?.rank) set('myRankChip', `My Rank: #${myRank.rank}`);
    } catch(e) { set('myRankChip', 'My Rank: —'); }

    if (!board.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-row">No traders yet</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    board.forEach((e, i) => {
      const rank    = e.rank ?? (i + 1);
      const total   = e.total_value   ?? e.portfolio_value ?? 0;
      const gl      = e.gain_loss     ?? e.total_gain_loss ?? 0;
      const glPct   = e.gain_loss_pct ?? e.total_gain_loss_pct ?? 0;
      const xp      = e.xp_points     ?? e.xp ?? 0;
      const cl      = gl >= 0 ? 'pos' : 'neg';
      const medal   = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
      const tr = document.createElement('tr');
      tr.className = rank <= 3 ? `rank-${rank}` : '';
      tr.innerHTML = `
        <td>${medal}</td>
        <td><strong>${e.username}</strong></td>
        <td>S$${fmt(total)}</td>
        <td class="${cl}">${gl >= 0 ? '+' : ''}S$${fmt(gl)}</td>
        <td class="${cl}">${glPct >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%</td>
        <td style="color:var(--yellow)">${xp} XP</td>`;
      tbody.appendChild(tr);
    });

  } catch(e) {
    console.error('Leaderboard error:', e);
    tbody.innerHTML = `<tr><td colspan="6" class="loading-row" style="color:var(--red)">Failed to load leaderboard: ${e.message}</td></tr>`;
    cs.innerHTML = '';
  }
}

// ── PROFILE ───────────────────────────────────────────────────────────
async function loadProfile() {
  try {
    const [p, myRank] = await Promise.all([
      api('/portfolio'),
      api('/leaderboard/me').catch(() => null)
    ]);
    set('profTotalValue', `S$${fmt(p.total_value)}`);
    set('profCash', `S$${fmt(p.cash)}`);
    const pnlEl = document.getElementById('profPnl');
    if (pnlEl) {
      pnlEl.textContent = `${p.total_gain_loss >= 0 ? '+' : ''}S$${fmt(p.total_gain_loss)}`;
      pnlEl.style.color = p.total_gain_loss >= 0 ? 'var(--green)' : 'var(--red)';
    }
    if (myRank?.rank) set('profRank', '#' + myRank.rank);
    // Badges
    const badges = [];
    if ((currentUser?.lessons_completed || 0) >= 1)  badges.push({ icon: '📚', label: 'First Lesson' });
    if ((currentUser?.lessons_completed || 0) >= 5)  badges.push({ icon: '🎓', label: 'Halfway There' });
    if ((currentUser?.lessons_completed || 0) >= 10) badges.push({ icon: '🏆', label: 'Graduate' });
    if (p.total_gain_loss > 0)                        badges.push({ icon: '📈', label: 'In the Green' });
    if ((p.holdings?.length || 0) >= 3)               badges.push({ icon: '🌍', label: 'Diversified' });
    const badgeEl = document.getElementById('profileBadges');
    badgeEl.innerHTML = badges.length ? badges.map(b => `<div class="badge-chip"><span>${b.icon}</span><span>${b.label}</span></div>`).join('') : '';
  } catch(e) {}
}

// ── UTILS ─────────────────────────────────────────────────────────────
function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function fmt(n) { return parseFloat(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmtBig(n) {
  if (!n) return '—';
  if (n >= 1e12) return (n/1e12).toFixed(1) + 'T';
  if (n >= 1e9)  return (n/1e9).toFixed(1) + 'B';
  if (n >= 1e6)  return (n/1e6).toFixed(1) + 'M';
  return n.toLocaleString();
}
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── TICKER TAPE ───────────────────────────────────────────────────────
function initTickerTape() {
  const tickers = ['AAPL $189.50','MSFT $415.20','GOOGL $178.30','AMZN $198.75','TSLA $245.60','NVDA $875.00','META $525.40','JPM $210.80','V $285.00','BRK-B $380.00'];
  const content = tickers.join('  ·  ');
  const tape = document.getElementById('tickerTape');
  if (tape) tape.innerHTML = `<div class="ticker-tape-inner">${content}  ·  ${content}</div>`;
}

// ── INIT ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTickerTape();
  if (token) {
    enterApp().catch(() => { localStorage.removeItem('stocksim_token'); token = null; });
  }
});
