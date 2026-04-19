// ═══════════════════════════════════════════════════════
// FindIt — Frontend JavaScript
// Talks to Flask backend at same origin
// ═══════════════════════════════════════════════════════

// ── STATE ─────────────────────────────────────────────
const AppState = { token: null, user: null, activeMatchId: null };

// ── ANIMATED BACKGROUND ───────────────────────────────
(function initCanvas() {
  const canvas = document.getElementById('bgCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [], connections = [];
  const PARTICLE_COUNT = 55, MAX_DIST = 140, COLORS = ['#2563eb','#7c3aed','#10b981','#f59e0b'];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function createParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - .5) * .45,
      vy: (Math.random() - .5) * .45,
      r:  Math.random() * 2.5 + 1,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      alpha: Math.random() * .4 + .15,
    };
  }

  function initParticles() {
    particles = Array.from({length: PARTICLE_COUNT}, createParticle);
  }

  function drawFrame() {
    ctx.clearRect(0, 0, W, H);
    // Subtle gradient overlay
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0,  'rgba(240,245,255,0.85)');
    grad.addColorStop(.5, 'rgba(248,250,255,0.8)');
    grad.addColorStop(1,  'rgba(245,240,255,0.85)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < MAX_DIST) {
          const opacity = (1 - dist/MAX_DIST) * 0.18;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(37,99,235,${opacity})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }
    // Draw particles
    for (const p of particles) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color.replace(')', `,${p.alpha})`).replace('rgb','rgba').replace('#','');
      // Use hex directly
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.fill();
      ctx.globalAlpha = 1;
      // Move
      p.x += p.vx; p.y += p.vy;
      if (p.x < -10) p.x = W + 10;
      if (p.x > W+10) p.x = -10;
      if (p.y < -10) p.y = H + 10;
      if (p.y > H+10) p.y = -10;
    }
    requestAnimationFrame(drawFrame);
  }

  resize();
  initParticles();
  drawFrame();
  window.addEventListener('resize', () => { resize(); });
})();

// ── API CLIENT ─────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (AppState.token) opts.headers['Authorization'] = 'Bearer ' + AppState.token;
  if (body) opts.body = JSON.stringify(body);
  const res  = await fetch(path, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || 'Request failed');
  return json.data;
}

// ── HELPERS ────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function timeAgo(ts) {
  if (!ts) return '';
  const s = Math.floor((Date.now() - new Date(ts)) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s/60) + ' min ago';
  if (s < 86400) return Math.floor(s/3600) + ' hr ago';
  if (s < 2592000) return Math.floor(s/86400) + ' days ago';
  return new Date(ts).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});
}

function fmtTime(ts) {
  if (!ts) return '';
  return new Date(ts).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
}

let _toastTimer;
function showToast(msg, type = 'info') {
  const el = $('toast'); if (!el) return;
  el.innerHTML = `<i class="fas fa-${type==='success'?'check-circle':type==='error'?'exclamation-circle':'info-circle'}"></i> ${msg}`;
  el.className = `toast show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.className = 'toast', 3600);
}

function setBusy(id, busy, label) {
  const el = $(id); if (!el) return;
  el.disabled = busy;
  if (label !== undefined) el.innerHTML = busy ? `<i class="fas fa-spinner fa-spin"></i> Please wait…` : label;
}

function requireAuth(action = 'do this') {
  if (AppState.user) return true;
  showToast(`Please sign in to ${action}.`, 'error');
  openModal('otpModal');
  return false;
}

function showLoading(state = true) {
  const el = $('loadingOverlay');
  if (el) el.classList.toggle('active', state);
}

// ── MODAL SYSTEM ──────────────────────────────────────
function openModal(id) {
  closeAllModals();
  const el = $(id);
  if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const el = $(id);
  if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
}
function closeAllModals() {
  document.querySelectorAll('.modal-backdrop').forEach(el => { el.classList.remove('open'); });
  document.body.style.overflow = '';
}
function switchModal(from, to) { closeModal(from); openModal(to); }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-backdrop')) closeAllModals();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAllModals(); });

// ── NAVIGATION ────────────────────────────────────────
function toggleMobileMenu() {
  const ham = $('hamburger'), drawer = $('mobileDrawer');
  if (ham && drawer) {
    ham.classList.toggle('open');
    drawer.classList.toggle('open');
  }
}
function closeMobileMenu() {
  const ham = $('hamburger'), drawer = $('mobileDrawer');
  if (ham) ham.classList.remove('open');
  if (drawer) drawer.classList.remove('open');
}
function toggleUserMenu() {
  $('userDropdown')?.classList.toggle('open');
  $('notifDropdown')?.classList.remove('open');
}
function toggleNotifDropdown() {
  $('notifDropdown')?.classList.toggle('open');
  $('userDropdown')?.classList.remove('open');
  loadNotifications();
}
// Close dropdowns on outside click
document.addEventListener('click', e => {
  if (!e.target.closest('.user-chip') && !e.target.closest('.user-dropdown'))
    $('userDropdown')?.classList.remove('open');
  if (!e.target.closest('.notif-wrapper') && !e.target.closest('.notif-dropdown'))
    $('notifDropdown')?.classList.remove('open');
  if (!e.target.closest('.hamburger') && !e.target.closest('.mobile-drawer'))
    closeMobileMenu();
});

// ── AUTH — OTP FLOW ───────────────────────────────────
let _otpContact = '';

async function sendOTP(resend = false) {
  const contact = ($('otpContact')?.value || '').trim();
  if (!contact) { showFormErr('otpError', 'Please enter your email or phone.'); return; }
  setBusy('sendOtpBtn', true);
  try {
    const d = await api('POST', '/api/auth/send-otp', { contact, purpose: 'login' });
    _otpContact = contact;
    $('otpStep1').style.display = 'none';
    $('otpStep2').style.display = '';
    $('otpMasked').textContent  = d.masked;
    $('otpVerifyError').style.display = 'none';
    document.querySelectorAll('.otp-digit').forEach(el => el.value = '');
    document.querySelector('.otp-digit')?.focus();
    startOtpTimer();
    if (resend) showToast('OTP resent!', 'success');
  } catch(e) { showFormErr('otpError', e.message); }
  finally { setBusy('sendOtpBtn', false, '<i class="fas fa-paper-plane"></i> Send OTP'); }
}

function otpDigitInput(el, idx) {
  el.value = el.value.replace(/\D/g,'').slice(-1);
  if (el.value && idx < 5) {
    document.querySelectorAll('.otp-digit')[idx+1]?.focus();
  }
}
function otpDigitKey(e, idx) {
  if (e.key === 'Backspace') {
    const el = document.querySelectorAll('.otp-digit')[idx];
    if (!el.value && idx > 0) document.querySelectorAll('.otp-digit')[idx-1]?.focus();
  }
  if (e.key === 'Enter') verifyOTP();
}

let _otpTimerInterval;
function startOtpTimer() {
  clearInterval(_otpTimerInterval);
  let secs = 600; // 10 min
  const el = $('otpTimer');
  _otpTimerInterval = setInterval(() => {
    if (secs <= 0) { clearInterval(_otpTimerInterval); if(el) el.textContent='(expired)'; return; }
    const m = Math.floor(secs/60), s = secs%60;
    if(el) el.textContent = `(${m}:${String(s).padStart(2,'0')})`;
    secs--;
  }, 1000);
}

async function verifyOTP() {
  const digits = document.querySelectorAll('.otp-digit');
  const otp    = Array.from(digits).map(d=>d.value).join('');
  if (otp.length < 6) { showFormErr('otpVerifyError', 'Please enter the 6-digit OTP.'); return; }

  setBusy('verifyOtpBtn', true);
  try {
    const full_name = ($('otpName')?.value || '').trim();
    const d = await api('POST', '/api/auth/verify-otp', { contact: _otpContact, otp, full_name });

    if (d.needs_name) {
      $('otpNameGroup').style.display = '';
      showFormErr('otpVerifyError', 'OTP verified! Please enter your name to complete registration.');
      setBusy('verifyOtpBtn', false, '<i class="fas fa-check"></i> Verify OTP');
      return;
    }
    onAuthSuccess(d.token, d.user);
    closeModal('otpModal');
    clearInterval(_otpTimerInterval);
    showToast(`Welcome, ${d.user.full_name || 'User'}! 🎉`, 'success');
    $('otpStep1').style.display = '';
    $('otpStep2').style.display = 'none';
    $('otpContact').value = '';
  } catch(e) { showFormErr('otpVerifyError', e.message); }
  finally { setBusy('verifyOtpBtn', false, '<i class="fas fa-check"></i> Verify OTP'); }
}

// ── AUTH — PASSWORD LOGIN ──────────────────────────────
async function doLogin() {
  const email    = ($('loginEmail')?.value    || '').trim();
  const password =  $('loginPassword')?.value || '';
  if (!email || !password) { showFormErr('loginError', 'Please fill in all fields.'); return; }
  setBusy('loginBtn', true);
  try {
    const d = await api('POST', '/api/auth/login', { email, password });
    onAuthSuccess(d.token, d.user);
    closeModal('loginModal');
    showToast(`Welcome back, ${d.user.full_name}!`, 'success');
  } catch(e) { showFormErr('loginError', e.message); }
  finally { setBusy('loginBtn', false, '<i class="fas fa-sign-in-alt"></i> Sign In'); }
}

// ── AUTH — REGISTER ───────────────────────────────────
async function doRegister() {
  const full_name = ($('regName')?.value     || '').trim();
  const email     = ($('regEmail')?.value    || '').trim();
  const phone     = ($('regPhone')?.value    || '').trim();
  const password  =  $('regPassword')?.value || '';
  if (!full_name || !email || !password) { showFormErr('registerError', 'Please fill in required fields.'); return; }
  if (password.length < 8) { showFormErr('registerError', 'Password must be at least 8 characters.'); return; }
  setBusy('registerBtn', true);
  try {
    await api('POST', '/api/auth/register', { full_name, email, phone, password });
    showToast('Account created! Please sign in.', 'success');
    switchModal('registerModal', 'loginModal');
    if($('loginEmail')) $('loginEmail').value = email;
  } catch(e) { showFormErr('registerError', e.message); }
  finally { setBusy('registerBtn', false, '<i class="fas fa-user-plus"></i> Create Account'); }
}

// ── AUTH — LOGOUT ─────────────────────────────────────
async function doLogout() {
  try { await api('POST', '/api/auth/logout'); } catch(_) {}
  AppState.token = null; AppState.user = null;
  localStorage.removeItem('fi_token');
  updateNavUI();
  showToast('Signed out.', 'info');
  closeAllModals();
  window.location.href = '/';
}

// ── AUTH STATE ────────────────────────────────────────
function onAuthSuccess(token, user) {
  AppState.token = token; AppState.user = user;
  localStorage.setItem('fi_token', token);
  updateNavUI();
  loadMatchBadge();
  if (typeof window._onAuthChange === 'function') window._onAuthChange();
}

function updateNavUI() {
  const u = AppState.user;
  if (u) {
    const initials = (u.full_name||'?').split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);
    const avatar = $('navAvatar'); if(avatar) avatar.textContent = initials;
    const name = $('navUserName'); if(name) name.textContent = (u.full_name||'').split(' ')[0];
    $('guestNav')  && ($('guestNav').style.display    = 'none');
    $('userNav')   && ($('userNav').style.display     = '');
    $('mobileGuestAuth') && ($('mobileGuestAuth').style.display = 'none');
    $('mobileUserAuth')  && ($('mobileUserAuth').style.display  = '');
  } else {
    $('guestNav')  && ($('guestNav').style.display    = '');
    $('userNav')   && ($('userNav').style.display     = 'none');
    $('mobileGuestAuth') && ($('mobileGuestAuth').style.display = '');
    $('mobileUserAuth')  && ($('mobileUserAuth').style.display  = 'none');
  }
}

function updateNavUser() { updateNavUI(); }

// ── BOOT ──────────────────────────────────────────────
(async function boot() {
  const saved = localStorage.getItem('fi_token');
  if (!saved) return;
  try {
    const res = await fetch('/api/users/me', { headers: { Authorization: 'Bearer ' + saved } });
    if (res.ok) {
      const json = await res.json();
      AppState.token = saved; AppState.user = json.data;
      updateNavUI();
      loadMatchBadge();
      if (typeof window._onAuthChange === 'function') window._onAuthChange();
    } else { localStorage.removeItem('fi_token'); }
  } catch(_) { localStorage.removeItem('fi_token'); }
})();

// ── MATCH BADGE ───────────────────────────────────────
async function loadMatchBadge() {
  if (!AppState.user) return;
  try {
    const matches = await api('GET', '/api/matches');
    const pending = matches.filter(m => !['returned'].includes(m.match_status)).length;
    const nb = $('matchNavBadge');
    if (nb) { nb.textContent = pending; nb.style.display = pending ? '' : 'none'; }
  } catch(_) {}
}

// ── NOTIFICATIONS ─────────────────────────────────────
async function loadNotifications() {
  if (!AppState.user) return;
  try {
    const notifs = await api('GET', '/api/notifications');
    const el = $('notifList'); if (!el) return;
    const unread = notifs.filter(n=>!n.is_read).length;
    const dot = $('notifDot');
    if (dot) dot.style.display = unread ? '' : 'none';
    if (!notifs.length) { el.innerHTML = '<div class="notif-empty">No notifications yet</div>'; return; }
    el.innerHTML = notifs.slice(0,8).map(n=>`
      <div class="notif-item${!n.is_read?' unread':''}" onclick="markOneRead('${n.id}',this)">
        ${!n.is_read?'<div class="ni-dot"></div>':'<div style="width:8px"></div>'}
        <div>
          <div class="ni-title">${esc(n.title)}</div>
          <div class="ni-body">${esc(n.body)}</div>
          <div class="ni-time">${timeAgo(n.created_at)}</div>
        </div>
      </div>`).join('');
  } catch(_) {}
}

async function markOneRead(id, el) {
  try {
    await api('PATCH', `/api/notifications/${id}/read`);
    el.classList.remove('unread');
    el.querySelector('.ni-dot')?.remove();
  } catch(_) {}
}

async function markAllRead() {
  try {
    await api('POST', '/api/notifications/read-all');
    showToast('All notifications marked as read.', 'success');
    loadNotifications();
  } catch(_) {}
}

// ── ITEM CARDS (shared across pages) ──────────────────
function makeCard(item) {
  const isLost = item.report_type === 'lost';
  return `
  <div class="item-card ${item.report_type}">
    <div class="ic-header">
      <span class="ic-badge ${item.report_type}">${isLost?'Lost':'Found'}</span>
      <span class="badge badge-${item.status}">${item.status}</span>
    </div>
    <div class="ic-body">
      <div class="ic-title">${esc(item.title)}</div>
      <div class="ic-meta"><i class="fas fa-tag"></i> ${esc(item.category_name||item.category||'')}</div>
      ${item.location_label?`<div class="ic-meta"><i class="fas fa-map-marker-alt"></i> ${esc(item.location_label)}</div>`:''}
      ${item.event_time   ?`<div class="ic-meta"><i class="fas fa-calendar"></i> ${esc(item.event_time)}</div>`:''}
      <div class="ic-meta"><i class="fas fa-user"></i> ${esc(item.reporter_name||'Anonymous')}</div>
      <div class="ic-desc">${esc(item.description||'')}</div>
      ${item.reward?`<div class="ic-reward"><i class="fas fa-gift"></i> Reward: ${esc(item.reward)}</div>`:''}
    </div>
    <div class="ic-footer">
      <button class="btn btn-ghost btn-sm" onclick="viewItem('${item.id}')">
        <i class="fas fa-eye"></i> Details
      </button>
      ${isLost
        ? `<button class="btn btn-outline btn-sm" onclick="openContactModal('${item.id}')"><i class="fas fa-comment"></i> Contact</button>`
        : `<button class="btn btn-primary btn-sm" onclick="openClaimItem('${item.id}')"><i class="fas fa-hand-holding"></i> Claim</button>`}
    </div>
  </div>`;
}

async function viewItem(id) {
  try {
    const item = await api('GET', `/api/reports/${id}`);
    const isLost = item.report_type === 'lost';
    $('itemModalTitle').innerHTML = `<i class="fas fa-${isLost?'search':'gift'}"></i> ${esc(item.title)}`;
    $('itemModalBody').innerHTML = `
      <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.25rem">
        <span class="ic-badge ${item.report_type}">${isLost?'Lost':'Found'}</span>
        <span class="badge badge-active">${esc(item.category_name||item.category||'')}</span>
        ${item.is_high_value?'<span class="badge badge-muted"><i class="fas fa-star"></i> High Value</span>':''}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-bottom:1.25rem">
        <div class="detail-block"><div class="db-label"><i class="fas fa-map-marker-alt"></i> Location</div>
             <div class="db-val">${esc(item.location_label||'—')}</div></div>
        <div class="detail-block"><div class="db-label"><i class="fas fa-calendar"></i> Date</div>
             <div class="db-val">${esc(item.event_time||'—')}</div></div>
        <div class="detail-block"><div class="db-label"><i class="fas fa-user"></i> Reporter</div>
             <div class="db-val">${esc(item.reporter_name||'—')}</div></div>
        <div class="detail-block"><div class="db-label"><i class="fas fa-clock"></i> Reported</div>
             <div class="db-val">${timeAgo(item.created_at)}</div></div>
        ${item.reward?`<div class="detail-block"><div class="db-label"><i class="fas fa-gift"></i> Reward</div>
             <div class="db-val">${esc(item.reward)}</div></div>`:''}
      </div>
      <div style="background:var(--gray0);border-radius:var(--r-lg);padding:1rem;margin-bottom:1.25rem;font-size:.9rem;color:var(--gray8);line-height:1.6">
        ${esc(item.description||'')}
      </div>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap;padding-top:1rem;border-top:2px solid var(--gray1)">
        ${isLost
          ? `<button class="btn btn-primary" onclick="openContactModal('${item.id}');closeModal('itemModal')"><i class="fas fa-comment"></i> Contact Reporter</button>`
          : `<button class="btn btn-primary" onclick="openClaimItem('${item.id}');closeModal('itemModal')"><i class="fas fa-hand-holding"></i> Claim This Item</button>`}
        <button class="btn btn-ghost" onclick="closeModal('itemModal')">Close</button>
      </div>`;
    openModal('itemModal');
  } catch(e) { showToast('Could not load item details.', 'error'); }
}

function openClaimItem(itemId) {
  if (!requireAuth('claim an item')) return;
  AppState.activeItemId = itemId;
  $('verifyAnswer').value = '';
  $('verifyError').style.display = 'none';
  AppState.activeMatchId = null;
  openModal('verifyModal');
}

function openContactModal(itemId) {
  if (!requireAuth('contact the reporter')) return;
  showToast('Use the Matches page to chat securely after your report matches.', 'info');
}

async function submitVerify() {
  const answer = ($('verifyAnswer')?.value || '').trim().toLowerCase();
  if (!answer) return;
  if (!AppState.activeMatchId) {
    showToast('Please go to the Matches page to verify ownership.', 'info');
    closeModal('verifyModal');
    return;
  }
  setBusy('verifyBtn', true);
  try {
    const r = await api('POST', `/api/matches/${AppState.activeMatchId}/verify`, { answer });
    closeModal('verifyModal');
    showToast(r.message || 'Verified!', 'success');
    loadMatchBadge();
  } catch(e) {
    $('verifyError').textContent = e.message;
    $('verifyError').style.display = '';
  } finally { setBusy('verifyBtn', false, '<i class="fas fa-check"></i> Verify'); }
}

// ── TOKEN ─────────────────────────────────────────────
function copyToken() {
  const text = $('tokenDisplay')?.textContent || '';
  navigator.clipboard.writeText(text)
    .then(() => showToast('Token copied!', 'success'))
    .catch(() => showToast('Copy failed — please copy manually.', 'error'));
}

// ── FORM ERRORS ───────────────────────────────────────
function showFormErr(id, msg) {
  const el = $(id); if (!el) return;
  el.textContent = msg;
  el.style.display = msg ? '' : 'none';
}

// ── INJECT CSS for detail blocks ──────────────────────
const _style = document.createElement('style');
_style.textContent = `.detail-block{background:var(--gray0);border-radius:var(--r);padding:.75rem 1rem}
.db-label{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--gray4);margin-bottom:.3rem;display:flex;align-items:center;gap:.3rem}
.db-label i{color:var(--primary)}
.db-val{font-size:.9rem;color:var(--dark);font-weight:500}`;
document.head.appendChild(_style);
