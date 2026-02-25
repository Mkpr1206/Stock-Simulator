// ── CONFIG ───────────────────────────────────────────────────────────
const API = 'https://stock-simulator-1-vlo6.onrender.com';
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

// ── REGION SYSTEM ─────────────────────────────────────────────────────
const REGIONS = {
  IN: {
    name: 'India',
    flag: '🇮🇳',
    currency: '₹',
    currencyCode: 'INR',
    exchange: 'NSE/BSE',
    suffix: '.NS',
    timezone: ['Asia/Calcutta', 'Asia/Kolkata'],
    marketHours: '9:15 AM – 3:30 PM IST',
    stocks: {
      'IT & Tech': [
        { v: 'TCS.NS',        l: 'TCS — Tata Consultancy Services' },
        { v: 'INFY.NS',       l: 'INFY — Infosys' },
        { v: 'WIPRO.NS',      l: 'WIPRO — Wipro' },
        { v: 'HCLTECH.NS',    l: 'HCLTECH — HCL Technologies' },
        { v: 'TECHM.NS',      l: 'TECHM — Tech Mahindra' },
      ],
      'Banking & Finance': [
        { v: 'HDFCBANK.NS',   l: 'HDFCBANK — HDFC Bank' },
        { v: 'ICICIBANK.NS',  l: 'ICICIBANK — ICICI Bank' },
        { v: 'SBIN.NS',       l: 'SBIN — State Bank of India' },
        { v: 'KOTAKBANK.NS',  l: 'KOTAKBANK — Kotak Mahindra Bank' },
        { v: 'AXISBANK.NS',   l: 'AXISBANK — Axis Bank' },
        { v: 'BAJFINANCE.NS', l: 'BAJFINANCE — Bajaj Finance' },
      ],
      'Conglomerate': [
        { v: 'RELIANCE.NS',   l: 'RELIANCE — Reliance Industries' },
        { v: 'ADANIENT.NS',   l: 'ADANIENT — Adani Enterprises' },
        { v: 'TATAMOTORS.NS', l: 'TATAMOTORS — Tata Motors' },
        { v: 'TATASTEEL.NS',  l: 'TATASTEEL — Tata Steel' },
      ],
      'Consumer & FMCG': [
        { v: 'HINDUNILVR.NS', l: 'HINDUNILVR — Hindustan Unilever' },
        { v: 'ITC.NS',        l: 'ITC — ITC Limited' },
        { v: 'NESTLEIND.NS',  l: 'NESTLEIND — Nestle India' },
        { v: 'BRITANNIA.NS',  l: 'BRITANNIA — Britannia Industries' },
      ],
      'Energy & Infra': [
        { v: 'ONGC.NS',       l: 'ONGC — Oil & Natural Gas Corp' },
        { v: 'NTPC.NS',       l: 'NTPC — NTPC Limited' },
        { v: 'POWERGRID.NS',  l: 'POWERGRID — Power Grid Corp' },
        { v: 'BPCL.NS',       l: 'BPCL — Bharat Petroleum' },
      ],
      'Indices / ETFs': [
        { v: 'NIFTYBEES.NS',  l: 'NIFTYBEES — Nifty 50 ETF' },
        { v: 'BANKBEES.NS',   l: 'BANKBEES — Bank Nifty ETF' },
      ],
    },
  },
  US: {
    name: 'United States',
    flag: '🇺🇸',
    currency: '$',
    currencyCode: 'USD',
    exchange: 'NYSE/NASDAQ',
    suffix: '',
    timezone: ['America/New_York', 'America/Chicago', 'America/Los_Angeles', 'America/Denver', 'America/Phoenix', 'America/Anchorage', 'Pacific/Honolulu'],
    marketHours: '9:30 AM – 4:00 PM EST',
    stocks: {
      'Technology': [
        { v: 'AAPL',  l: 'AAPL — Apple' },
        { v: 'MSFT',  l: 'MSFT — Microsoft' },
        { v: 'GOOGL', l: 'GOOGL — Alphabet' },
        { v: 'AMZN',  l: 'AMZN — Amazon' },
        { v: 'META',  l: 'META — Meta' },
        { v: 'NVDA',  l: 'NVDA — NVIDIA' },
        { v: 'TSLA',  l: 'TSLA — Tesla' },
        { v: 'AMD',   l: 'AMD — AMD' },
        { v: 'NFLX',  l: 'NFLX — Netflix' },
        { v: 'ADBE',  l: 'ADBE — Adobe' },
      ],
      'Finance': [
        { v: 'JPM',   l: 'JPM — JPMorgan Chase' },
        { v: 'BAC',   l: 'BAC — Bank of America' },
        { v: 'GS',    l: 'GS — Goldman Sachs' },
        { v: 'V',     l: 'V — Visa' },
        { v: 'MA',    l: 'MA — Mastercard' },
        { v: 'BRK-B', l: 'BRK-B — Berkshire Hathaway' },
      ],
      'Healthcare': [
        { v: 'JNJ',   l: 'JNJ — Johnson & Johnson' },
        { v: 'PFE',   l: 'PFE — Pfizer' },
        { v: 'UNH',   l: 'UNH — UnitedHealth' },
        { v: 'ABBV',  l: 'ABBV — AbbVie' },
      ],
      'Consumer': [
        { v: 'WMT',   l: 'WMT — Walmart' },
        { v: 'KO',    l: 'KO — Coca-Cola' },
        { v: 'MCD',   l: "MCD — McDonald's" },
        { v: 'NKE',   l: 'NKE — Nike' },
        { v: 'PG',    l: 'PG — Procter & Gamble' },
        { v: 'SBUX',  l: 'SBUX — Starbucks' },
      ],
      'Energy': [
        { v: 'XOM',   l: 'XOM — ExxonMobil' },
        { v: 'CVX',   l: 'CVX — Chevron' },
      ],
      'ETFs': [
        { v: 'SPY',   l: 'SPY — S&P 500 ETF' },
        { v: 'QQQ',   l: 'QQQ — NASDAQ ETF' },
        { v: 'DIA',   l: 'DIA — Dow Jones ETF' },
        { v: 'VTI',   l: 'VTI — Total Market ETF' },
      ],
    },
  },
  GB: {
    name: 'United Kingdom',
    flag: '🇬🇧',
    currency: '£',
    currencyCode: 'GBP',
    exchange: 'LSE',
    suffix: '.L',
    timezone: ['Europe/London'],
    marketHours: '8:00 AM – 4:30 PM GMT',
    stocks: {
      'Finance': [
        { v: 'HSBA.L', l: 'HSBA — HSBC Holdings' },
        { v: 'LLOY.L', l: 'LLOY — Lloyds Banking' },
        { v: 'BARC.L', l: 'BARC — Barclays' },
        { v: 'NWG.L',  l: 'NWG — NatWest Group' },
      ],
      'Energy': [
        { v: 'BP.L',   l: 'BP — BP plc' },
        { v: 'SHEL.L', l: 'SHEL — Shell plc' },
      ],
      'Consumer': [
        { v: 'ULVR.L', l: 'ULVR — Unilever' },
        { v: 'DGE.L',  l: 'DGE — Diageo' },
        { v: 'MKS.L',  l: 'MKS — Marks & Spencer' },
      ],
      'Healthcare': [
        { v: 'AZN.L',  l: 'AZN — AstraZeneca' },
        { v: 'GSK.L',  l: 'GSK — GSK plc' },
      ],
      'Telecom & Tech': [
        { v: 'VOD.L',  l: 'VOD — Vodafone' },
        { v: 'BT-A.L', l: 'BT — BT Group' },
      ],
    },
  },
  JP: {
    name: 'Japan',
    flag: '🇯🇵',
    currency: '¥',
    currencyCode: 'JPY',
    exchange: 'TSE',
    suffix: '.T',
    timezone: ['Asia/Tokyo'],
    marketHours: '9:00 AM – 3:30 PM JST',
    stocks: {
      'Tech & Auto': [
        { v: '7203.T',  l: '7203 — Toyota Motor' },
        { v: '6758.T',  l: '6758 — Sony Group' },
        { v: '6861.T',  l: '6861 — Keyence' },
        { v: '9984.T',  l: '9984 — SoftBank Group' },
        { v: '6501.T',  l: '6501 — Hitachi' },
      ],
      'Finance': [
        { v: '8306.T',  l: '8306 — Mitsubishi UFJ Financial' },
        { v: '8411.T',  l: '8411 — Mizuho Financial' },
      ],
      'Consumer': [
        { v: '9983.T',  l: '9983 — Fast Retailing (Uniqlo)' },
        { v: '4519.T',  l: '4519 — Chugai Pharmaceutical' },
      ],
    },
  },
  EU: {
    name: 'Europe',
    flag: '🇪🇺',
    currency: '€',
    currencyCode: 'EUR',
    exchange: 'Various',
    suffix: '',
    timezone: ['Europe/Paris', 'Europe/Berlin', 'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam'],
    marketHours: '9:00 AM – 5:30 PM CET',
    stocks: {
      'Tech & Auto': [
        { v: 'SAP',    l: 'SAP — SAP SE' },
        { v: 'ASML',   l: 'ASML — ASML Holding' },
        { v: 'VWAGY',  l: 'VWAGY — Volkswagen' },
        { v: 'BMWYY',  l: 'BMWYY — BMW Group' },
      ],
      'Finance': [
        { v: 'DB',     l: 'DB — Deutsche Bank' },
        { v: 'BNP.PA', l: 'BNP — BNP Paribas' },
        { v: 'AXA.PA', l: 'AXA — AXA Group' },
      ],
      'Consumer & Luxury': [
        { v: 'MC.PA',  l: 'MC — LVMH' },
        { v: 'OR.PA',  l: 'OR — L\'Oréal' },
        { v: 'NESN.SW',l: 'NESN — Nestlé' },
      ],
      'Energy': [
        { v: 'TTFCF',  l: 'TTFCF — TotalEnergies' },
        { v: 'ENEL.MI',l: 'ENEL — Enel SpA' },
      ],
    },
  },
};

let currentRegion = 'US'; // default, will be overridden by detection

function detectRegion() {
  const saved = localStorage.getItem('stocksim_region');
  if (saved && REGIONS[saved]) return saved;
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone; // e.g. "Asia/Kolkata"
    for (const [code, region] of Object.entries(REGIONS)) {
      if (region.timezone.some(t => tz === t || tz.startsWith(t))) {
        return code;
      }
    }
    // Broader continent matching
    if (tz.startsWith('Asia/Cal') || tz.startsWith('Asia/Kol')) return 'IN';
    if (tz.startsWith('Asia/To'))  return 'JP';
    if (tz.startsWith('Asia/'))    return 'IN'; // most Asia = India fallback
    if (tz.startsWith('Europe/'))  return 'EU';
    if (tz.startsWith('America/')) return 'US';
    // Language fallback
    const lang = navigator.language || '';
    if (lang.includes('-IN') || lang.startsWith('hi')) return 'IN';
    if (lang.startsWith('ja')) return 'JP';
    if (lang.includes('-GB')) return 'GB';
    if (lang.startsWith('fr') || lang.startsWith('de') || lang.startsWith('es') || lang.startsWith('it')) return 'EU';
  } catch(e) {}
  return 'US';
}

function setRegion(code) {
  if (!REGIONS[code]) return;
  currentRegion = code;
  localStorage.setItem('stocksim_region', code);
  const r = REGIONS[code];
  document.querySelectorAll('.currency-sym').forEach(el => el.textContent = r.currency);
  const badge = document.getElementById('marketBadge');
  if (badge) badge.innerHTML = `${ef(r.flag)} ${r.name} <span style="color:var(--text3)">· ${r.exchange}</span>`;
  rebuildStockDropdowns();
  document.querySelectorAll('.region-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.region === code);
  });
  document.querySelectorAll('.region-btn-sidebar').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.region === code);
  });
  const banner = document.getElementById('regionDetectText');
  if (banner) banner.textContent = `${r.flag} ${r.name} market (${r.exchange})`;
  toast(`Switched to ${r.flag} ${r.name} market`, 'success');
}

function rebuildStockDropdowns() {
  const r = REGIONS[currentRegion];
  const dropdowns = ['tickerDropdown', 'chartDropdown'];
  dropdowns.forEach(ddId => {
    const dd = document.getElementById(ddId);
    if (!dd) return;
    dd.innerHTML = `<option value="">— ${r.flag} ${r.name} stocks —</option>`;
    Object.entries(r.stocks).forEach(([sector, stocks]) => {
      const og = document.createElement('optgroup');
      og.label = sector;
      stocks.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.v;
        opt.textContent = s.l;
        og.appendChild(opt);
      });
      dd.appendChild(og);
    });
  });
}

function getCurrency() { return REGIONS[currentRegion]?.currency || 'S$'; }
function fmtMoney(n)   { return `${getCurrency()}${fmt(n)}`; }

// ── API HELPERS ───────────────────────────────────────────────────────
// ── fetchWithTimeout: prevents infinite hang on Render free tier spin-up ────
function fetchWithTimeout(url, opts = {}, ms = 20000) {
  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), ms);
  return fetch(url, { ...opts, signal: controller.signal })
    .finally(() => clearTimeout(tid))
    .catch(err => {
      if (err.name === 'AbortError') throw new Error('Server took too long to respond. It may be waking up — please try again in 30 seconds.');
      throw err;
    });
}

async function api(path, method = 'GET', body = null, auth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetchWithTimeout(API + path, opts);
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

// POST with query params — this is what the StockSim backend actually uses
// e.g. POST /trade/buy?ticker=AAPL&quantity=5
async function apiQuery(path, params = {}, auth = true) {
  const headers = {};
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;
  const qs = new URLSearchParams(params).toString();
  const res = await fetchWithTimeout(`${API}${path}?${qs}`, { method: 'POST', headers });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) throw new Error(detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', '));
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Request failed');
  }
  return data;
}
async function apiForm(path, body) {
  const res = await fetchWithTimeout(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(body).toString()
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) throw new Error(detail.map(e => e.msg || JSON.stringify(e)).join(', '));
    throw new Error(typeof detail === 'string' ? detail : 'Login failed');
  }
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
function validateUsername(u) {
  if (!u) return 'Username is required';
  if (u.length < 3) return 'Username must be at least 3 characters';
  if (u.length > 30) return 'Username must be under 30 characters';
  if (!/^[a-zA-Z0-9_]+$/.test(u)) return 'Username: letters, numbers and underscores only';
  return null;
}
function validateEmail(e) {
  if (!e) return 'Email is required';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return 'Please enter a valid email';
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
  const span = btn.querySelector('span:first-child');
  if (span) span.textContent = loading ? 'PLEASE WAIT...' : (btn.dataset.label || span.textContent);
}
async function login() {
  const usernameOrEmail = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  document.getElementById('authError').classList.add('hidden');
  if (!usernameOrEmail) return showAuthError('Please enter your username or email');
  if (!password) return showAuthError('Please enter your password');
  const btn = document.querySelector('#loginForm .btn-primary');
  btn.dataset.label = btn.dataset.label || 'ENTER MARKET';
  setAuthLoading(btn, true);
  try {
    // Try as username first, then as email if that fails
    let d = null;
    try {
      d = await apiForm('/auth/login', { username: usernameOrEmail.toLowerCase(), password });
    } catch(e) {
      // If login failed and input looks like email, try email lookup
      if (usernameOrEmail.includes('@')) {
        d = await apiForm('/auth/login-email', { email: usernameOrEmail.toLowerCase(), password });
      } else {
        throw e;
      }
    }
    if (!d.access_token) throw new Error('No token received');
    token = d.access_token;
    localStorage.setItem('stocksim_token', token);
    await enterApp();
  } catch(e) {
    const msg = e.message || '';
    if (msg.includes('fetch') || msg.includes('Failed')) showAuthError('Cannot connect to server.');
    else if (msg.includes('401') || msg.toLowerCase().includes('incorrect') || msg.toLowerCase().includes('invalid')) showAuthError('Wrong username/email or password. Try demo_alice / demo1234');
    else showAuthError(msg || 'Login failed');
  } finally { setAuthLoading(btn, false); }
}
async function register() {
  const username = document.getElementById('regUsername').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  document.getElementById('authError').classList.add('hidden');
  const err = validateUsername(username) || validateEmail(email) || validatePassword(password);
  if (err) return showAuthError(err);
  const chosenRegion = document.querySelector('#regMarketPicker .market-pick-btn.selected')?.dataset.region || currentRegion;
  const btn = document.querySelector('#registerForm .btn-primary');
  btn.dataset.label = 'START WITH 100,000';
  setAuthLoading(btn, true);

  // Backend uses query params (not JSON body) for register
  // def register(username: str, email: str, password: str) — FastAPI query params
  const attempts = [
    // Query params — what the backend actually expects
    () => fetch(`${API}/auth/register?username=${encodeURIComponent(username)}&email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, { method: 'POST' }).then(async r => { const d = await r.json(); if (!r.ok) { const det = d.detail; throw new Error(Array.isArray(det) ? det.map(e=>e.msg||e.message||JSON.stringify(e)).join(', ') : (typeof det==='string'?det:JSON.stringify(det)||'Failed')); } return d; }),
    // JSON body fallback (if backend is ever updated)
    () => api('/auth/register', 'POST', { username, email, password }, false),
    () => api('/auth/register', 'POST', { username, email, password, confirm_password: password }, false),
    // Form encoded fallback
    () => apiForm('/auth/register', { username, email, password }),
  ];

  let d = null;
  let lastErr = '';
  let debugLog = [];

  for (const attempt of attempts) {
    try {
      d = await attempt();
      break;
    } catch(e) {
      lastErr = e.message || '';
      debugLog.push(lastErr);
      // Only keep trying on field/validation/404 errors
      if (!lastErr.includes('Field') && !lastErr.includes('Not Found') &&
          !lastErr.includes('404') && !lastErr.includes('422') &&
          !lastErr.includes('Unprocessable') && !lastErr.includes('required') &&
          !lastErr.includes('value_error') && !lastErr.includes('missing')) {
        break;
      }
    }
  }

  // If all attempts failed, log full debug info to console so user can report it
  if (!d) {
    console.error('=== StockSim Registration Debug ===');
    console.error('All endpoints tried. Last errors:', debugLog);
    console.error('Open your backend main.py and look for: @router.post("/auth/register")');
    console.error('Check the Pydantic model fields required by that route');
    console.error('====================================');
  }

  try {
    if (!d) throw new Error(lastErr || 'Registration failed');
    if (!d.access_token) throw new Error('Account created — please log in with your credentials');
    token = d.access_token;
    localStorage.setItem('stocksim_token', token);
    currentRegion = chosenRegion;
    localStorage.setItem('stocksim_region', chosenRegion);
    await enterApp();
    const r = REGIONS[chosenRegion];
    toast(`\uD83C\uDF89 Welcome! Trading ${r.name} market with 100,000 SimBucks!`, 'success');
  } catch(e) {
    const msg = e.message || '';
    if (msg.includes('fetch') || msg.includes('Failed to fetch')) {
      showAuthError('Cannot connect to server. Make sure the backend is running: python main.py');
    } else if (msg.toLowerCase().includes('already') || msg.toLowerCase().includes('taken') || msg.toLowerCase().includes('exists')) {
      showAuthError('Username or email already registered. Try logging in instead.');
    } else if (msg.includes('please log in')) {
      showAuthError('\u2713 Account created! Please log in with your username and password.');
    } else {
      showAuthError(msg || 'Registration failed');
    }
  } finally { setAuthLoading(btn, false); }
}
function showAuthError(msg) {
  const el = document.getElementById('authError');
  el.textContent = msg;
  el.classList.remove('hidden');
}
function logout() {
  localStorage.removeItem('stocksim_token');
  token = null; currentUser = null;
  cachedWalletBalance = null;
  currentTicker = null; currentPrice = 0; currentHolding = null;
  currentChartTicker = null;
  ['loginUsername','loginPassword','regUsername','regEmail','regPassword'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  document.getElementById('authError').classList.add('hidden');
  location.reload();
}
function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  pendingModalAction = null;
  // Reset modal buttons to default (delete account modal changes them)
  const confirmBtn = document.querySelector('#modal .btn-danger');
  const cancelBtn  = document.querySelector('#modal .btn-ghost');
  if (confirmBtn) { confirmBtn.textContent = 'CONFIRM'; confirmBtn.style.background = ''; }
  if (cancelBtn)  { cancelBtn.textContent  = 'CANCEL'; }
}
async function modalConfirm() {
  const confirmBtn = document.querySelector('#modal .btn-danger');
  if (confirmBtn) { confirmBtn.textContent = 'PLEASE WAIT...'; confirmBtn.disabled = true; }
  const action = pendingModalAction;
  closeModal();
  if (confirmBtn) { confirmBtn.textContent = 'CONFIRM'; confirmBtn.disabled = false; }
  if (action) {
    try { await action(); }
    catch(e) { toast(e.message || 'Action failed', 'error'); }
  }
}
async function enterApp() {
  document.getElementById('splash').classList.remove('active');
  document.getElementById('app').classList.add('active');
  // Only detect region if not already set (preserve registration choice)
  if (!localStorage.getItem('stocksim_region')) {
    currentRegion = detectRegion();
  }
  setRegion(currentRegion);
  try { await loadCurrentUser(); } catch(e) { console.warn('loadCurrentUser:', e); }
  loadDashboard();
}

// ── USER ──────────────────────────────────────────────────────────────
async function loadCurrentUser() {
  try {
    currentUser = await api('/auth/me');
    const u = currentUser.username ?? '?';
    const xp = currentUser.xp_points ?? 0;
    const lessons = currentUser.lessons_completed ?? 0;
    set('sidebarUsername', u);
    set('userAvatar', u[0].toUpperCase());
    set('profileAvatar', u[0].toUpperCase());
    set('profileUsername', u);
    set('profileEmail', currentUser.email || '—');
    const joined = currentUser.created_at ?? currentUser.joined_at ?? currentUser.member_since ?? null;
    set('profileJoined', joined ? fmtDate(joined) : 'recently');
    set('xpBadge', `⭐ ${xp} XP`);
    set('profXp', `${xp} XP`);
    set('profLessons', `${lessons} / 10`);
    updateGreeting(u);
  } catch(e) { console.warn('loadCurrentUser:', e.message); }
}

function updateSidebarBalance(v) { set('sidebarBalance', `${getCurrency()}${fmt(v)}`); }
function updateGreeting(u) {
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
  set('dashGreeting', `${g}, ${u}. ${REGIONS[currentRegion].name} market`);
}

// ── NAVIGATION ────────────────────────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`panel-${name}`)?.classList.add('active');
  document.querySelector(`[data-panel="${name}"]`)?.classList.add('active');
  const loaders = { dashboard: loadDashboard, portfolio: loadPortfolio, watchlist: loadWatchlist,
    education: loadLessons, glossary: loadGlossary,
    trade: loadTradeBalance, profile: loadProfile, charts: () => {} };
  loaders[name]?.();
}

// ── DASHBOARD ─────────────────────────────────────────────────────────
async function loadDashboard() {
  loadFeatured(); loadDashHoldings(); loadSentiment(); loadDashSummary();
}
async function loadDashSummary() {
  try {
    const p = await api('/portfolio');
    const total = p.total_value ?? p.portfolio_value ?? 0;
    const gl    = p.total_gain_loss ?? p.gain_loss ?? 0;
    const glPct = p.total_gain_loss_pct ?? p.gain_loss_pct ?? 0;
    set('headerTotalValue', fmtMoney(total));
    const pnlEl = document.getElementById('headerPnl');
    if (pnlEl) {
      pnlEl.textContent = `${gl >= 0 ? '+' : ''}${fmtMoney(gl)} (${gl >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%)`;
      pnlEl.style.color = gl >= 0 ? 'var(--green)' : 'var(--red)';
    }
    updateSidebarBalance(total);
  } catch(e) {}
}
async function loadFeatured() {
  const grid = document.getElementById('featuredGrid');
  grid.innerHTML = '<div class="loading-row">Fetching live prices...</div>';
  try {
    const data = await api(`/market/featured?region=${currentRegion}`, 'GET', null, false);
    grid.innerHTML = '';
    data.forEach(item => {
      const chip = document.createElement('div');
      chip.className = 'ticker-chip';
      const chg = item.change_pct || 0;
      chip.innerHTML = `
        <div class="tc-symbol">${item.ticker}</div>
        <div class="tc-price">${item.price > 0 ? getCurrency() + item.price.toFixed(2) : '—'}</div>
        <div class="tc-change ${chg >= 0 ? 'pos' : 'neg'}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</div>`;
      chip.onclick = () => { showPanel('trade'); selectTicker(item.ticker); };
      grid.appendChild(chip);
    });
  } catch(e) { grid.innerHTML = `<div class="loading-row" style="color:var(--red)">Could not load — is the server running?</div>`; }
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
      const gl    = h.gain_loss ?? h.unrealized_gain ?? 0;
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
          <div class="dh-value">${fmtMoney(val)}</div>
          <div class="dh-pnl" style="color:${cl}">${gl >= 0 ? '+' : ''}${(glPct || 0).toFixed(2)}%</div>
        </div>`;
      el.appendChild(div);
    });
    const tipSection = document.getElementById('tipSection');
    if (tipSection) tipSection.classList.add('hidden'); // no briefing endpoint in backend
  } catch(e) { el.innerHTML = `<div class="empty-state" style="color:var(--red)">${e.message}</div>`; }
}

// ── TRADE ─────────────────────────────────────────────────────────────
async function loadTradeBalance() {
  try {
    const w = await api('/wallet');
    const bal = w.balance ?? w.cash ?? w.simBucks ?? 0;
    cachedWalletBalance = Math.max(0, bal); // refresh cache too
    set('tradeBalance', fmtMoney(Math.max(0, bal)));
  } catch(e) { set('tradeBalance', '—'); }
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
    set('infoPrice', fmtMoney(currentPrice));
    set('infoPriceSub', `LIVE PRICE (${REGIONS[currentRegion].currencyCode})`);
    set('infoPE', info.pe_ratio ? info.pe_ratio.toFixed(1) : '—');
    set('infoMktCap', info.market_cap ? getCurrency() + fmtBig(info.market_cap) : '—');
    set('infoBeta', info.beta ? info.beta.toFixed(2) : '—');
    // Dividend yield — handle both decimal and percent formats
    // Dividend yield — backend may send as decimal (0.023) or percent (2.3)
    // Cap at 30% to catch bad data (yfinance sometimes sends garbage for non-US stocks)
    const rawDiv = info.dividend_yield ?? info.dividendYield ?? info.div_yield ?? 0;
    let divDisplay = '—';
    if (rawDiv && rawDiv > 0) {
      const divPct = rawDiv < 1 ? rawDiv * 100 : rawDiv; // convert decimal to %
      divDisplay = divPct > 30 ? '—' : divPct.toFixed(2) + '%'; // cap bad data
    }
    set('infoDivYield', divDisplay);
    const high = info.fifty_two_week_high ?? info.fiftyTwoWeekHigh ?? info['52_week_high'] ?? null;
    const low  = info.fifty_two_week_low  ?? info.fiftyTwoWeekLow  ?? info['52_week_low']  ?? null;
    set('info52High', high ? getCurrency() + parseFloat(high).toFixed(2) : '—');
    set('info52Low',  low  ? getCurrency() + parseFloat(low).toFixed(2)  : '—');
    set('infoDesc', info.description || '');
    document.getElementById('stockCard').classList.remove('hidden');
    document.getElementById('actionRow').classList.remove('hidden');
    try {
      const portfolio = await api('/portfolio');
      currentHolding = (portfolio.holdings ?? portfolio.positions ?? []).find(h => h.ticker === currentTicker) || null;
    } catch(e) { currentHolding = null; }
    calcCost(); calcSellProceeds();
  } catch(e) { toast(`Could not load "${ticker}" — check spelling or server`, 'error'); }
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
    if (action === 'limit_buy') set('limitCurrent', fmtMoney(currentPrice));
    if (action === 'limit_sell') set('limitSellCurrent', fmtMoney(currentPrice));
  }
}
function hideAllActionPanels() { document.querySelectorAll('.ap-block').forEach(b => b.classList.add('hidden')); }
function setupBuyPanel() { set('previewPrice', fmtMoney(currentPrice)); calcCost(); }
function setupSellPanel() {
  set('sellPreviewPrice', fmtMoney(currentPrice));
  const banner = document.getElementById('holdingBanner');
  if (currentHolding) {
    banner.innerHTML = `<span>You own <strong>${currentHolding.quantity} shares</strong> of ${currentTicker} @ avg ${fmtMoney(currentHolding.avg_cost)}</span>`;
    set('sellAvgCost', fmtMoney(currentHolding.avg_cost));
  } else {
    banner.innerHTML = `<span style="color:var(--red)">⚠ You don't own any ${currentTicker}</span>`;
  }
  banner.classList.remove('hidden');
  calcSellProceeds();
}
function adjustQty(id, delta) {
  const inp = document.getElementById(id);
  const v = Math.max(1, (parseInt(inp.value) || 1) + delta);
  inp.value = v;
  if (id === 'execQty') calcCost();
  if (id === 'sellQty') calcSellProceeds();
  if (id === 'limitBuyQty') calcLimitCost();
}
let cachedWalletBalance = null; // cache to avoid hitting /wallet on every keystroke

async function refreshWalletCache() {
  try {
    const w = await api('/wallet');
    cachedWalletBalance = w.balance ?? w.cash ?? w.simBucks ?? 0;
  } catch(e) {}
}

async function calcCost() {
  const qty = parseInt(document.getElementById('execQty')?.value) || 1;
  set('previewQty', qty);
  if (!currentPrice) return;
  const total = currentPrice * qty;
  set('estCost', fmtMoney(total));
  // Use cached balance — only fetch if we don't have one yet
  if (cachedWalletBalance === null) await refreshWalletCache();
  const bal = cachedWalletBalance ?? 0;
  const after = bal - total;
  set('afterBalance', fmtMoney(after));
  document.getElementById('afterBalance').style.color = after >= 0 ? 'var(--text)' : 'var(--red)';
}
function calcSellProceeds() {
  const qty = parseInt(document.getElementById('sellQty')?.value) || 1;
  if (!currentPrice) return;
  set('sellProceeds', fmtMoney(currentPrice * qty));
  if (currentHolding) {
    const pnl = (currentPrice - currentHolding.avg_cost) * qty;
    const pnlEl = document.getElementById('sellPnl');
    if (pnlEl) { pnlEl.textContent = `${pnl >= 0 ? '+' : ''}${fmtMoney(pnl)}`; pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)'; }
  }
}
function calcLimitCost() {
  const price = parseFloat(document.getElementById('limitBuyPrice')?.value) || 0;
  const qty = parseInt(document.getElementById('limitBuyQty')?.value) || 1;
  set('limitTarget', price ? fmtMoney(price) : '—');
  set('limitReserved', price ? fmtMoney(price * qty) : '—');
}
function sellAllShares() {
  if (currentHolding) { document.getElementById('sellQty').value = currentHolding.quantity; calcSellProceeds(); }
}

async function executeTrade(mode) {
  if (!currentTicker) return toast('No stock selected', 'error');
  const qtyId = mode === 'buy' ? 'execQty' : 'sellQty';
  const qty = parseFloat(document.getElementById(qtyId)?.value);
  if (!qty || qty <= 0) return toast('Enter a valid quantity', 'error');
  const resultId = mode === 'buy' ? 'tradeResult' : 'sellResult';
  const resultEl = document.getElementById(resultId);
  resultEl.classList.add('hidden');
  toast(`Processing ${mode}...`, 'info');
  try {
    // Backend uses query params: POST /trade/buy?ticker=AAPL&quantity=5
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const url = `${API}/trade/${mode}?ticker=${encodeURIComponent(currentTicker)}&quantity=${qty}`;
    const rawRes = await fetchWithTimeout(url, { method: 'POST', headers });
    const text = await rawRes.text();
    let res;
    try { res = JSON.parse(text); }
    catch(e) { throw new Error(`Server error: ${text.substring(0, 100)}`); }
    if (!rawRes.ok) {
      const detail = res.detail;
      throw new Error(Array.isArray(detail) ? detail.map(e=>e.msg||e).join(', ') : (typeof detail==='string' ? detail : text.substring(0,100)));
    }
    resultEl.className = 'trade-result success';
    resultEl.textContent = res.message ?? `${mode.toUpperCase()} successful!`;
    resultEl.classList.remove('hidden');
    toast(res.message ?? `${mode.toUpperCase()} successful!`, 'success');
    cachedWalletBalance = null;
    loadTradeBalance();
    if (res.new_balance) updateSidebarBalance(res.new_balance);
    try {
      const portfolio = await api('/portfolio');
      currentHolding = (portfolio.holdings ?? []).find(h => h.ticker === currentTicker) || null;
      if (mode === 'sell') setupSellPanel();
    } catch(e) {}
  } catch(e) {
    resultEl.className = 'trade-result error';
    resultEl.textContent = e.message || `${mode} failed`;
    resultEl.classList.remove('hidden');
    toast(e.message || `${mode} failed`, 'error');
  }
}

async function placeLimitOrder(type) {
  // Backend doesn't have limit orders yet — show friendly message
  toast('Limit orders coming soon! For now, use market buy/sell.', 'info');
  const resId = type === 'buy' ? 'limitBuyResult' : 'limitSellResult';
  const resultEl = document.getElementById(resId);
  resultEl.className = 'trade-result';
  resultEl.style.borderColor = 'var(--accent2)';
  resultEl.textContent = '⏳ Limit orders are not yet available in this version of the backend.';
  resultEl.classList.remove('hidden');
}

async function addCurrentToWatchlist() {
  if (!currentTicker) return;
  const resultEl = document.getElementById('watchlistResult');
  resultEl.classList.add('hidden');
  try {
    // Backend: POST /watchlist?ticker=AAPL  (query param)
    await apiQuery('/watchlist', { ticker: currentTicker });
    resultEl.className = 'trade-result success';
    resultEl.textContent = `✓ ${currentTicker} added to your watchlist`;
    resultEl.classList.remove('hidden');
    toast(`${currentTicker} added to watchlist`, 'success');
  } catch(e) {
    resultEl.className = 'trade-result error';
    resultEl.textContent = e.message.includes('Already') ? `${currentTicker} is already on your watchlist` : e.message;
    resultEl.classList.remove('hidden');
  }
}

async function loadPendingOrders() {
  // Backend has no /orders endpoint — hide section gracefully
  const el = document.getElementById('pendingOrders');
  el.innerHTML = '<div class="empty-state" style="font-size:11px">Limit orders not yet available in backend</div>';
}

async function cancelOrder(id) {
  toast('Order cancellation not available in this backend version', 'info');
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
    set('chartCurrentPrice', fmtMoney(price));
    // Backend returns: { ticker, period, data: { Close: {"date": val}, Volume: {"date": val} } }
    const raw = hist.data || hist;
    const closeObj = raw.Close || raw.close || raw.closes || {};
    const volumeObj = raw.Volume || raw.volume || {};
    const labels = Object.keys(closeObj);
    const closes = Object.values(closeObj).map(Number);
    if (closes.length > 1) {
      const change = closes[closes.length-1] - closes[0];
      const changePct = ((change / closes[0]) * 100).toFixed(2);
      const changeEl = document.getElementById('chartChange');
      changeEl.textContent = `${change >= 0 ? '+' : ''}${getCurrency()}${Math.abs(change).toFixed(2)} (${change >= 0 ? '+' : ''}${changePct}%)`;
      changeEl.style.color = change >= 0 ? 'var(--green)' : 'var(--red)';
      set('chartChangePct', `${change >= 0 ? '+' : ''}${changePct}%`);
      document.getElementById('chartChangePct').style.color = change >= 0 ? 'var(--green)' : 'var(--red)';
      set('chartHigh', fmtMoney(Math.max(...closes)));
      set('chartLow',  fmtMoney(Math.min(...closes)));
    }
    const volumes = Object.values(volumeObj).map(Number).filter(v => v > 0);
    if (volumes.length) set('chartVolume', fmtBig(volumes.reduce((a,b)=>a+b,0)/volumes.length));
    drawPriceChart(labels, closes);
  } catch(e) {
    document.getElementById('chartLoading').classList.add('hidden');
    document.getElementById('chartEmpty').classList.remove('hidden');
    document.getElementById('chartEmpty').textContent = `Could not load chart for "${currentChartTicker}"`;
  }
}
function drawPriceChart(labels, data) {
  const ctx = document.getElementById('priceChart').getContext('2d');
  if (priceChartInstance) priceChartInstance.destroy();
  const isUp = data.length > 1 && data[data.length-1] >= data[0];
  const color = isUp ? '#00d4aa' : '#ff4560';
  priceChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: currentChartTicker, data, borderColor: color, backgroundColor: isUp ? 'rgba(0,212,170,0.08)' : 'rgba(255,69,96,0.08)', borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, fill: true, tension: 0.3 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#0f1217', borderColor: '#1e2530', borderWidth: 1, titleColor: '#8896a8', bodyColor: '#e2e8f0', callbacks: { label: ctx => ` ${getCurrency()}${ctx.parsed.y.toFixed(2)}` } } },
      scales: {
        x: { ticks: { color: '#4a5568', font: { family: 'Space Mono', size: 10 }, maxTicksLimit: 8 }, grid: { color: '#1e2530' } },
        y: { position: 'right', ticks: { color: '#8896a8', font: { family: 'Space Mono', size: 10 }, callback: v => getCurrency() + v.toFixed(0) }, grid: { color: '#1e2530' } }
      }
    }
  });
}
function goTradeFromChart(action) {
  if (!currentChartTicker) return;
  showPanel('trade');
  document.getElementById('tradeTickerInput').value = currentChartTicker;
  selectTicker(currentChartTicker).then(() => { document.getElementById('actionDropdown').value = action; onActionChange(); });
}

// ── PORTFOLIO ─────────────────────────────────────────────────────────
async function loadPortfolio() {
  ['portTotalValue','portCash','portInvested','portPnl'].forEach(id => set(id, '...'));
  try {
    const p = await api('/portfolio');
    const total   = p.total_value    ?? p.portfolio_value ?? 0;
    const cash    = p.cash           ?? p.cash_balance    ?? 0;
    const invested= p.invested_value ?? p.stocks_value    ?? 0;
    const gl      = p.total_gain_loss ?? p.gain_loss      ?? 0;
    const glPct   = p.total_gain_loss_pct ?? p.gain_loss_pct ?? 0;
    const holdings= p.holdings       ?? p.positions       ?? [];
    set('portTotalValue', fmtMoney(total));
    set('portCash', fmtMoney(cash));
    set('portInvested', fmtMoney(invested));
    const pnlEl = document.getElementById('portPnl');
    if (pnlEl) { pnlEl.textContent = `${gl >= 0 ? '+' : ''}${fmtMoney(gl)} (${gl >= 0 ? '+' : ''}${(glPct||0).toFixed(2)}%)`; pnlEl.style.color = gl >= 0 ? 'var(--green)' : 'var(--red)'; }
    const tbody = document.getElementById('holdingsTbody');
    if (!holdings.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-row">No holdings yet — go trade!</td></tr>';
      document.getElementById('allocationLegend').innerHTML = '';
    } else {
      tbody.innerHTML = '';
      holdings.forEach(h => {
        const hgl   = h.gain_loss ?? h.unrealized_gain ?? 0;
        const hglPct= h.gain_loss_pct ?? h.gain_loss_percent ?? 0;
        const avg   = h.avg_cost ?? h.average_cost ?? h.cost_basis ?? 0;
        const curPx = h.current_price ?? h.price ?? 0;
        const curVal= h.current_value ?? h.market_value ?? 0;
        const cl = hgl >= 0 ? 'pos' : 'neg';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong style="cursor:pointer;color:var(--accent)" onclick="openChartFor('${h.ticker}')">${h.ticker}</strong></td>
          <td>${h.quantity}</td><td>${fmtMoney(avg)}</td><td>${fmtMoney(curPx)}</td><td>${fmtMoney(curVal)}</td>
          <td class="${cl}">${hgl >= 0 ? '+' : ''}${fmtMoney(hgl)}</td>
          <td class="${cl}">${hglPct >= 0 ? '+' : ''}${(hglPct||0).toFixed(2)}%</td>
          <td><button class="quick-sell" onclick="quickSell('${h.ticker}',${h.quantity})">SELL ALL</button></td>`;
        tbody.appendChild(tr);
      });
      drawAllocationChart(holdings, cash);
    }
    updateSidebarBalance(total);
  } catch(e) { document.getElementById('holdingsTbody').innerHTML = `<tr><td colspan="8" class="loading-row" style="color:var(--red)">${e.message}</td></tr>`; }
  try {
    const trades = await api('/portfolio/trades?limit=50');
    const list = Array.isArray(trades) ? trades : (trades.trades ?? trades.history ?? []);
    const tbody2 = document.getElementById('tradeHistoryTbody');
    if (!list.length) { tbody2.innerHTML = '<tr><td colspan="6" class="loading-row">No trades yet</td></tr>'; return; }
    tbody2.innerHTML = '';
    list.forEach(t => {
      const action = t.action ?? t.trade_type ?? t.type ?? '—';
      const ts     = t.executed_at ?? t.timestamp ?? t.created_at ?? null;
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${fmtDate(ts)}</td><td class="${action === 'BUY' ? 'tag-buy' : 'tag-sell'}">${action}</td><td><strong>${t.ticker}</strong></td><td>${t.quantity}</td><td>${fmtMoney(t.price)}</td><td>${fmtMoney(t.total_value ?? t.total ?? (t.price * t.quantity))}</td>`;
      tbody2.appendChild(tr);
    });
  } catch(e) { document.getElementById('tradeHistoryTbody').innerHTML = `<tr><td colspan="6" style="color:var(--red);padding:12px">${e.message}</td></tr>`; }
}
function drawAllocationChart(holdings, cash) {
  const ctx = document.getElementById('allocationChart')?.getContext('2d');
  if (!ctx) return;
  if (allocationChartInstance) allocationChartInstance.destroy();
  const colors = ['#00d4aa','#0099ff','#f5c842','#ff4560','#a855f7','#f97316','#22d3ee','#84cc16','#ec4899','#6366f1'];
  const labels = [...holdings.map(h => h.ticker)];
  const data   = [...holdings.map(h => h.current_value ?? h.market_value ?? 0)];
  if (cash > 0) { labels.push('CASH'); data.push(cash); }
  allocationChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors, borderColor: '#0a0c0f', borderWidth: 3, hoverOffset: 6 }] },
    options: { responsive: false, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#0f1217', callbacks: { label: ctx => ` ${fmtMoney(ctx.parsed)} (${((ctx.parsed/data.reduce((a,b)=>a+b,0))*100).toFixed(1)}%)` } } } }
  });
  const legend = document.getElementById('allocationLegend');
  legend.innerHTML = '';
  const total = data.reduce((a,b)=>a+b,0);
  labels.forEach((l, i) => {
    const div = document.createElement('div');
    div.className = 'al-item';
    div.innerHTML = `<span class="al-dot" style="background:${colors[i%colors.length]}"></span><span class="al-name">${l}</span><span class="al-pct">${((data[i]/total)*100).toFixed(1)}%</span>`;
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
  set('modalTitle', `Sell all ${ticker}?`);
  set('modalMessage', `This will sell all ${qty} shares of ${ticker} at market price.`);
  pendingModalAction = async () => {
    toast(`Selling ${qty} shares of ${ticker}...`, 'info');
    try {
      const res = await apiQuery('/trade/sell', { ticker, quantity: qty });
      toast(res?.message || `Sold ${qty} shares of ${ticker}!`, 'success');
      cachedWalletBalance = null;
      loadPortfolio(); loadDashboard();
    } catch(e) {
      toast(`Sell failed: ${e.message}`, 'error');
    }
  };
  document.getElementById('modal').classList.remove('hidden');
}
function confirmReset() {
  set('modalTitle', 'Reset Portfolio?');
  set('modalMessage', 'Clears all holdings and restores 100,000 SimBucks. Cannot be undone.');
  pendingModalAction = resetPortfolio;
  document.getElementById('modal').classList.remove('hidden');
}
function confirmDeleteAccount() {
  set('modalTitle', '⚠ Delete Account?');
  set('modalMessage', 'This permanently deletes your account, portfolio, trade history and wallet. This CANNOT be undone.');
  // Override modal buttons for this action
  const confirmBtn = document.querySelector('#modal .btn-danger');
  const cancelBtn  = document.querySelector('#modal .btn-ghost');
  confirmBtn.textContent = 'YES, DELETE EVERYTHING';
  confirmBtn.style.background = '#ff1a1a';
  cancelBtn.textContent = 'CANCEL';
  pendingModalAction = deleteAccount;
  document.getElementById('modal').classList.remove('hidden');
}

async function deleteAccount() {
  try {
    await api('/auth/account', 'DELETE');
    toast('Account deleted. Goodbye!', 'info');
    // Clear all local data and return to splash
    localStorage.removeItem('stocksim_token');
    localStorage.removeItem('stocksim_region');
    token = null;
    currentUser = null;
    setTimeout(() => {
      document.getElementById('app').classList.add('hidden');
      document.getElementById('splash').classList.remove('hidden');
      document.getElementById('splash').classList.add('active');
    }, 1500);
  } catch(e) {
    toast(`Delete failed: ${e.message}`, 'error');
  }
}

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
    const list = Array.isArray(items) ? items : (items.watchlist ?? items.items ?? []);
    if (!list.length) { el.innerHTML = '<div class="empty-state">Watchlist is empty. Add tickers above.</div>'; return; }
    el.innerHTML = '';
    list.forEach(item => {
      const div = document.createElement('div');
      div.className = 'watchlist-item';
      div.innerHTML = `
        <div>
          <div class="wi-ticker" style="cursor:pointer" onclick="openChartFor('${item.ticker}')">${item.ticker}</div>
          <div class="wi-added">Added ${fmtDate(item.added_at)}</div>
        </div>
        <div style="display:flex;align-items:center;gap:16px">
          <div class="wi-price">${item.current_price > 0 ? getCurrency() + item.current_price.toFixed(2) : '—'}</div>
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
    // Backend: POST /watchlist?ticker=AAPL
    await apiQuery('/watchlist', { ticker });
    document.getElementById('watchlistInput').value = '';
    toast(`${ticker} added to watchlist`, 'success');
    loadWatchlist();
  } catch(e) {
    toast(e.message.includes('Already') ? `${ticker} already on watchlist` : e.message, 'error');
  }
}
async function removeFromWatchlist(ticker) {
  try {
    // Try DELETE endpoint first, fallback to POST with remove action
    try { await api(`/watchlist/${ticker}`, 'DELETE'); }
    catch(e) { await apiQuery(`/watchlist/${ticker}`, {}, true); }
    toast(`${ticker} removed from watchlist`, 'info');
    loadWatchlist();
  } catch(e) { toast(`Could not remove ${ticker}: ${e.message}`, 'error'); }
}

// ── EDUCATION — ENHANCED ──────────────────────────────────────────────
const LEARNING_PATHS = {
  beginner: {
    id: 'beginner', name: 'Beginner Path', icon: '🌱',
    description: 'Start from zero — understand what stocks are and how markets work',
    color: '#00d4aa', lessons: [1, 2, 3, 5],
  },
  intermediate: {
    id: 'intermediate', name: 'Analyst Path', icon: '📊',
    description: 'Read charts, understand ratios, and analyze companies like a pro',
    color: '#f5c842', lessons: [4, 6, 8],
  },
  advanced: {
    id: 'advanced', name: 'Strategist Path', icon: '🏆',
    description: 'Master market cycles, compound growth, and avoid common mistakes',
    color: '#ff4560', lessons: [7, 9, 10],
  },
};

let selectedPath = null;
let completedLessonIds = new Set();

async function loadLessons() {
  document.getElementById('lessonsList').classList.remove('hidden');
  document.getElementById('lessonDetail').classList.add('hidden');
  const el = document.getElementById('lessonsList');
  el.innerHTML = '<div class="loading-row">Loading...</div>';
  try {
    const [lessons, progress] = await Promise.all([
      api('/education/lessons', 'GET', null, false),
      api('/education/progress').catch(() => [])
    ]);
    completedLessonIds = new Set(progress.filter(p => p.completed).map(p => p.lesson_id));
    const completedCount = completedLessonIds.size;
    document.getElementById('progressFill').style.width = (completedCount / 10 * 100) + '%';
    set('progressLabel', `${completedCount} / 10 lessons completed`);
    set('xpBadge', `⭐ ${currentUser?.xp_points ?? 0} XP`);
    el.innerHTML = '';

    // ── Learning paths section ──
    const pathsDiv = document.createElement('div');
    pathsDiv.className = 'learning-paths';
    pathsDiv.innerHTML = `<div class="paths-title">CHOOSE YOUR LEARNING PATH</div>`;
    const pathsGrid = document.createElement('div');
    pathsGrid.className = 'paths-grid';
    Object.values(LEARNING_PATHS).forEach(path => {
      const completedInPath = path.lessons.filter(id => completedLessonIds.has(id)).length;
      const card = document.createElement('div');
      card.className = `path-card ${selectedPath === path.id ? 'path-active' : ''}`;
      card.style.borderColor = selectedPath === path.id ? path.color : '';
      card.innerHTML = `
        <div class="path-icon">${path.icon}</div>
        <div class="path-name">${path.name}</div>
        <div class="path-desc">${path.description}</div>
        <div class="path-progress">
          <div class="path-prog-bar"><div class="path-prog-fill" style="width:${(completedInPath/path.lessons.length)*100}%;background:${path.color}"></div></div>
          <span>${completedInPath}/${path.lessons.length}</span>
        </div>`;
      card.onclick = () => { selectedPath = selectedPath === path.id ? null : path.id; loadLessons(); };
      pathsGrid.appendChild(card);
    });
    pathsDiv.appendChild(pathsGrid);
    el.appendChild(pathsDiv);

    // ── Lesson cards ──
    const grid = document.createElement('div');
    grid.className = 'lessons-grid';
    const filteredLessons = selectedPath
      ? lessons.filter(l => LEARNING_PATHS[selectedPath].lessons.includes(l.id))
      : lessons;

    filteredLessons.forEach(l => {
      const done = completedLessonIds.has(l.id);
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
      grid.appendChild(card);
    });
    el.appendChild(grid);
  } catch(e) { el.innerHTML = `<div class="empty-state">${e.message}</div>`; }
}

async function openLesson(id) {
  document.getElementById('lessonsList').classList.add('hidden');
  document.getElementById('lessonDetail').classList.remove('hidden');
  currentLessonId = id;
  set('lessonBody', '<div class="loading-row">Loading lesson...</div>');
  document.getElementById('quizSection').classList.add('hidden');
  document.getElementById('quizResult').classList.add('hidden');
  document.getElementById('submitQuizBtn')?.classList.remove('hidden');
  try {
    const l = await api(`/education/lessons/${id}`, 'GET', null, false);
    currentLesson = l;
    const diffClass = `diff-${l.difficulty.toLowerCase()}`;
    document.getElementById('lessonDifficulty').className = `difficulty-badge ${diffClass}`;
    set('lessonDifficulty', l.difficulty.toUpperCase());
    set('lessonXP', `+${l.xp_reward} XP on completion`);
    set('lessonTitle', l.title);

    // Related stocks for this lesson
    const relatedTickers = getRelatedTickers(l.title);

    document.getElementById('lessonBody').innerHTML = renderMarkdown(l.content || '') + 
      (relatedTickers.length ? `<div class="lesson-try-it"><div class="lesson-try-title">🎯 TRY IT NOW</div><p>Practice what you learned — look up these stocks:</p><div class="lesson-tickers">${relatedTickers.map(t => `<button class="lesson-ticker-btn" onclick="goTradeStock('${t}')">${t}</button>`).join('')}</div></div>` : '');

    // Build progress steps
    buildLessonProgress(id);

    if (l.quiz?.length) { buildQuiz(l.quiz); document.getElementById('quizSection').classList.remove('hidden'); }
  } catch(e) { toast('Could not load lesson', 'error'); }
}

function getRelatedTickers(title) {
  const t = title.toLowerCase();
  const r = REGIONS[currentRegion];
  if (t.includes('stock') || t.includes('market')) return Object.values(r.stocks).flat().slice(0,3).map(s => s.v);
  if (t.includes('dividend')) return currentRegion === 'IN' ? ['ITC.NS','HINDUNILVR.NS'] : ['KO','JNJ','PG'];
  if (t.includes('p/e') || t.includes('earnings')) return currentRegion === 'IN' ? ['TCS.NS','INFY.NS'] : ['AAPL','MSFT'];
  if (t.includes('bear') || t.includes('bull')) return currentRegion === 'IN' ? ['NIFTYBEES.NS'] : ['SPY','QQQ'];
  return [];
}

function goTradeStock(ticker) {
  showPanel('trade');
  document.getElementById('tradeTickerInput').value = ticker;
  selectTicker(ticker);
}

function buildLessonProgress(currentId) {
  const el = document.getElementById('lessonProgressSteps');
  if (!el) return;
  const allIds = [1,2,3,4,5,6,7,8,9,10];
  el.innerHTML = allIds.map(lessonId => `
    <div class="lp-step ${lessonId === currentId ? 'lp-current' : ''} ${completedLessonIds.has(lessonId) ? 'lp-done' : ''}" onclick="openLesson(${lessonId})" title="Lesson ${lessonId}">
      ${completedLessonIds.has(lessonId) ? '✓' : lessonId}
    </div>`).join('');
}

function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^✅ (.+)$/gm, '<p class="md-good">✅ $1</p>')
    .replace(/^❌ (.+)$/gm, '<p class="md-bad">❌ $1</p>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hpuolb])(.+)$/gm, '<p>$1</p>');
}

function buildQuiz(questions) {
  const el = document.getElementById('quizQuestions');
  el.innerHTML = '';
  questions.forEach((q, qi) => {
    const div = document.createElement('div');
    div.className = 'quiz-q';
    div.innerHTML = `<div class="quiz-q-text"><span class="quiz-num">Q${qi+1}</span>${q.question}</div>`;
    q.options.forEach((opt, oi) => {
      const label = document.createElement('label');
      label.className = 'quiz-option';
      label.innerHTML = `<input type="radio" name="q${qi}" value="${oi}"><span class="quiz-opt-letter">${'ABCD'[oi]}</span>${opt}`;
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
  const total = currentLesson?.quiz?.length || 0;
  const answers = [];
  let unanswered = 0;
  for (let i = 0; i < total; i++) {
    const sel = document.querySelector(`[name="q${i}"]:checked`);
    if (!sel) unanswered++;
    answers.push(sel ? parseInt(sel.value) : -1);
  }
  if (unanswered > 0) {
    const proceed = confirm(`You have ${unanswered} unanswered question${unanswered > 1 ? 's' : ''}. Submit anyway? Unanswered questions will be marked wrong.`);
    if (!proceed) return;
  }
  try {
    const result = await api(`/education/lessons/${currentLessonId}/quiz`, 'POST', { answers });
    const el = document.getElementById('quizResult');
    el.className = result.passed ? 'quiz-pass' : 'quiz-fail';
    el.innerHTML = `
      <div class="quiz-score-ring">
        <div class="quiz-score-num">${result.score_pct}%</div>
        <div class="quiz-score-label">${result.passed ? '🎉 PASSED' : '📚 TRY AGAIN'}</div>
      </div>
      <p style="margin:12px 0;color:var(--text2)">${result.message}</p>
      ${result.passed ? `<div class="xp-earned">+${result.xp_earned} XP earned!</div>` : ''}
      ${(result.feedback || []).map(f => `
        <div class="feedback-item ${f.is_correct ? 'fb-correct' : 'fb-wrong'}">
          <div class="fb-header">${f.is_correct ? '✅' : '❌'} ${f.question}</div>
          <div class="fb-explanation">${f.explanation}</div>
        </div>`).join('')}
      ${!result.passed ? `<button class="btn-primary-sm" onclick="retryQuiz()" style="margin-top:16px">↻ RETRY QUIZ</button>` : ''}`;
    el.classList.remove('hidden');
    document.getElementById('submitQuizBtn').classList.add('hidden');
    if (result.passed) {
      completedLessonIds.add(currentLessonId);
      const xp = (currentUser?.xp_points || 0) + result.xp_earned;
      if (currentUser) currentUser.xp_points = xp;
      set('xpBadge', `⭐ ${xp} XP`);
      buildLessonProgress(currentLessonId);
      // Suggest next lesson
      const nextId = currentLessonId + 1;
      if (nextId <= 10) {
        setTimeout(() => {
          el.innerHTML += `<div class="next-lesson-prompt"><p>Ready for the next lesson?</p><button class="btn-primary-sm" onclick="openLesson(${nextId})">→ LESSON ${nextId}</button></div>`;
        }, 1000);
      }
    }
  } catch(e) { toast(e.message, 'error'); }
}

function retryQuiz() {
  document.getElementById('quizResult').classList.add('hidden');
  document.getElementById('submitQuizBtn').classList.remove('hidden');
  document.querySelectorAll('.quiz-option').forEach(o => o.classList.remove('selected'));
  document.querySelectorAll('input[type="radio"]').forEach(r => r.checked = false);
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
  if (!terms.length) { el.innerHTML = '<div class="empty-state">No results found</div>'; return; }
  el.innerHTML = '';
  terms.forEach(t => {
    const div = document.createElement('div');
    div.className = 'glossary-item';
    div.innerHTML = `<div class="glossary-term">${t.term}</div><div class="glossary-def">${t.definition}</div>${t.example ? `<div class="glossary-example">💡 ${t.example}</div>` : ''}`;
    el.appendChild(div);
  });
}
function searchGlossary() {
  const q = document.getElementById('glossarySearch').value.toLowerCase();
  renderGlossary(allGlossaryTerms.filter(t => t.term.toLowerCase().includes(q) || t.definition.toLowerCase().includes(q)));
}


// ── PROFILE ───────────────────────────────────────────────────────────
async function loadProfile() {
  buildProfileMarketCards(); // always render market switcher immediately
  try {
    const [p] = await Promise.all([api('/portfolio')]);
    const total = p.total_value ?? p.portfolio_value ?? 0;
    const gl = p.total_gain_loss ?? p.gain_loss ?? 0;
    set('profTotalValue', fmtMoney(total));
    set('profCash', fmtMoney(p.cash ?? p.cash_balance ?? 0));
    const profPnl = document.getElementById('profPnl');
    if (profPnl) { profPnl.textContent = `${gl>=0?'+':''}${fmtMoney(gl)}`; profPnl.style.color = gl>=0?'var(--green)':'var(--red)'; }
      const badges = [];
    if ((currentUser?.lessons_completed||0) >= 1)  badges.push({ icon:'📚', label:'First Lesson' });
    if ((currentUser?.lessons_completed||0) >= 5)  badges.push({ icon:'🎓', label:'Halfway There' });
    if ((currentUser?.lessons_completed||0) >= 10) badges.push({ icon:'🏆', label:'Graduate' });
    if (gl > 0)                                    badges.push({ icon:'📈', label:'In the Green' });
    if ((p.holdings?.length||0) >= 3)              badges.push({ icon:'🌍', label:'Diversified' });
    badges.push({ icon: REGIONS[currentRegion].flag, label: REGIONS[currentRegion].name + ' Trader' });
    document.getElementById('profileBadges').innerHTML = badges.map(b => `<div class="badge-chip"><span>${b.icon}</span><span>${b.label}</span></div>`).join('');
  } catch(e) {}
}

// ── UTILS ─────────────────────────────────────────────────────────────
// Windows Chrome renders emoji flags as ¤ when Space Mono is the active font.
// Always wrap flags in an emoji-font span for innerHTML contexts.
const EMOJI_STYLE = `font-family:'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',sans-serif`;
function ef(flag) { return `<span style="${EMOJI_STYLE}">${flag}</span>`; }
function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function fmt(n) { return parseFloat(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function fmtBig(n) {
  if (!n) return '—';
  if (n>=1e12) return (n/1e12).toFixed(1)+'T';
  if (n>=1e9)  return (n/1e9).toFixed(1)+'B';
  if (n>=1e6)  return (n/1e6).toFixed(1)+'M';
  return n.toLocaleString();
}
function fmtDate(d) {
  if (!d) return '—';
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return '—';
  return dt.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
}

function initTickerTape() {
  const r = REGIONS[currentRegion];
  const tickerObjs = Object.values(r.stocks).flat().slice(0, 10);
  const tape = document.getElementById('tickerTape');
  if (!tape) return;
  const render = arr => {
    const joined = arr.join('  ·  ');
    tape.innerHTML = '<div class="ticker-tape-inner">' + joined + '  ·  ' + joined + '</div>';
  };
  // Show placeholders immediately
  render(tickerObjs.map(s => s.l.split(' — ')[0] + ' ...'));
  // Fetch real prices in background
  Promise.allSettled(tickerObjs.map(s =>
    fetch(API + '/market/price/' + s.v).then(r => r.json()).catch(() => null)
  )).then(results => {
    render(tickerObjs.map((s, i) => {
      const name = s.l.split(' — ')[0];
      const res = results[i];
      return (res.status === 'fulfilled' && res.value && res.value.price)
        ? name + ' ' + getCurrency() + res.value.price.toFixed(2)
        : name;
    }));
  });
}

// ── REGION SWITCHER UI ────────────────────────────────────────────────
function buildRegionSwitcher() {
  // Splash page small flag row (above login form)
  const splash = document.getElementById('regionSwitcher');
  if (splash) {
    splash.innerHTML = Object.entries(REGIONS).map(([code, r]) =>
      `<button class="region-btn ${code === currentRegion ? 'active' : ''}" data-region="${code}" onclick="setRegion('${code}')" title="${r.name}">${ef(r.flag)}</button>`
    ).join('');
  }
  // Sidebar compact flags
  const sidebar = document.getElementById('regionSwitcherSidebar');
  if (sidebar) {
    sidebar.innerHTML = Object.entries(REGIONS).map(([code, r]) =>
      `<button class="region-btn-sidebar ${code === currentRegion ? 'active' : ''}" data-region="${code}" onclick="setRegion('${code}')">${ef(r.flag)} ${r.name}</button>`
    ).join('');
  }
  // Registration full-card market picker
  buildRegMarketPicker();
  // Update detect banner
  updateDetectBanner();
}

function updateDetectBanner() {
  const r = REGIONS[currentRegion];
  const banner = document.getElementById('regionDetectText');
  if (banner) banner.textContent = `${r.flag} Auto-detected: ${r.name} (${r.exchange}) — change below`;
}

function buildRegMarketPicker() {
  const el = document.getElementById('regMarketPicker');
  if (!el) return;
  el.innerHTML = Object.entries(REGIONS).map(([code, r]) => `
    <button class="market-pick-btn ${code === currentRegion ? 'selected' : ''}" data-region="${code}" onclick="selectRegMarket('${code}')">
      <span class="mpb-flag">${ef(r.flag)}</span>
      <span class="mpb-name">${r.name}</span>
      <span class="mpb-ex">${r.exchange}</span>
      <span class="mpb-cur">${r.currency}</span>
    </button>`).join('');
  // Update hint
  const hint = document.getElementById('regMarketHint');
  if (hint) {
    const r = REGIONS[currentRegion];
    hint.textContent = `${r.flag} ${r.name} · ${r.exchange} · ${r.currency} · Market hours: ${r.marketHours}`;
  }
}

function selectRegMarket(code) {
  document.querySelectorAll('.market-pick-btn').forEach(b => b.classList.remove('selected'));
  document.querySelectorAll(`[data-region="${code}"].market-pick-btn`).forEach(b => b.classList.add('selected'));
  currentRegion = code; // preview — will be saved on actual register
  const r = REGIONS[code];
  const hint = document.getElementById('regMarketHint');
  if (hint) hint.textContent = `${r.flag} ${r.name} · ${r.exchange} · ${r.currency} · Market hours: ${r.marketHours}`;
}

function buildProfileMarketCards() {
  const el = document.getElementById('profileMarketCards');
  if (!el) return;
  el.innerHTML = Object.entries(REGIONS).map(([code, r]) => `
    <div class="market-card ${code === currentRegion ? 'market-card-active' : ''}" onclick="switchMarketFromProfile('${code}')">
      <div class="mc-flag">${ef(r.flag)}</div>
      <div class="mc-info">
        <div class="mc-name">${r.name}</div>
        <div class="mc-exchange">${r.exchange} · ${r.currency}</div>
        <div class="mc-hours">${r.marketHours}</div>
      </div>
      <div class="mc-check">${code === currentRegion ? '✓ ACTIVE' : 'SWITCH'}</div>
    </div>`).join('');
}

function switchMarketFromProfile(code) {
  if (code === currentRegion) return;
  const r = REGIONS[code];
  set('modalTitle', `Switch to ${r.name}?`);
  set('modalMessage', `Your stock dropdown, currency (${r.currency}) and featured stocks will update to ${r.name} (${r.exchange}). Existing holdings are unaffected.`);
  pendingModalAction = () => { setRegion(code); buildProfileMarketCards(); loadDashboard(); };
  document.getElementById('modal').classList.remove('hidden');
}

// ── INIT ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  currentRegion = detectRegion();
  initTickerTape();
  buildRegionSwitcher();
  if (token) {
    enterApp().catch(() => { localStorage.removeItem('stocksim_token'); token = null; });
  }
});
