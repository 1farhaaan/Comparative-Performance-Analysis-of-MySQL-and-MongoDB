/**
 * auth.js — ResolvIQ Login & Signup Pages
 *
 * Handles:
 *  - Role / account-type selector toggle
 *  - Password visibility toggle
 *  - Password strength meter (signup)
 *  - Basic client-side form validation
 *
 * Flask notes:
 *  - All form submission is handled server-side via POST
 *  - Flash messages are rendered by Jinja2 (see templates)
 *  - Remove onsubmit="return handleLogin(event)" if using
 *    pure Flask form submission (no AJAX)
 */

'use strict';

/* ══════════════════════════════════════════
   SHARED — Role / Account-type selector
   Used on: login.html, signup.html
   ══════════════════════════════════════════ */

/**
 * Highlight the clicked role button and update the hidden input.
 * @param {string} role  - 'client' | 'admin'
 * @param {HTMLElement} btn - The clicked button element
 * @param {string} inputId  - ID of the hidden <input> to update
 */
function selectRole(role, btn, inputId = 'accountType') {
  const parent = btn.closest('.role-select');
  if (parent) {
    parent.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
  }
  btn.classList.add('active');
  const hiddenInput = document.getElementById(inputId);
  if (hiddenInput) hiddenInput.value = role;
}

/* ══════════════════════════════════════════
   LOGIN PAGE
   ══════════════════════════════════════════ */

/**
 * Toggle password field visibility.
 * @param {string} fieldId - ID of the password input
 * @param {HTMLElement} toggleBtn - The eye icon button
 */
function togglePassword(fieldId, toggleBtn) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  const isHidden = field.type === 'password';
  field.type     = isHidden ? 'text' : 'password';
  if (toggleBtn) toggleBtn.textContent = isHidden ? '🙈' : '👁';
}

/* ══════════════════════════════════════════
   SIGNUP PAGE — Password Strength Meter
   ══════════════════════════════════════════ */

const STRENGTH_COLORS = ['#f43f5e', '#f59e0b', '#3b82f6', '#10b981'];
const STRENGTH_LABELS = ['Weak', 'Fair', 'Strong', 'Very Strong'];

/**
 * Score a password 0–4 based on length, case, numbers, symbols.
 * @param {string} val
 * @returns {number} 0–4
 */
function scorePassword(val) {
  let score = 0;
  if (val.length >= 8)          score++;
  if (/[A-Z]/.test(val))        score++;
  if (/[0-9]/.test(val))        score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;
  return score;
}

/**
 * Update the 4-segment strength bar and label text.
 * Call this from oninput on the password field.
 * @param {string} val - Current password value
 */
function checkPasswordStrength(val) {
  const segs     = [1, 2, 3, 4].map(n => document.getElementById('s' + n));
  const labelEl  = document.getElementById('strengthText');
  if (!segs[0] || !labelEl) return;

  if (!val) {
    segs.forEach(s => { if (s) s.style.background = 'var(--border)'; });
    labelEl.textContent  = 'Enter a password';
    labelEl.style.color  = 'var(--muted)';
    return;
  }

  const score = scorePassword(val);
  const color = STRENGTH_COLORS[score - 1] || STRENGTH_COLORS[0];

  segs.forEach((s, i) => {
    if (!s) return;
    s.style.background = i < score ? color : 'var(--border)';
  });

  labelEl.textContent = STRENGTH_LABELS[score - 1] || 'Weak';
  labelEl.style.color = color;
}

/* ══════════════════════════════════════════
   CLIENT-SIDE VALIDATION HELPERS
   (Flask handles server-side validation;
    these just give instant UI feedback)
   ══════════════════════════════════════════ */

/**
 * Validate the login form before submit.
 * Flask will also validate — this is just UX.
 * @param {Event} e
 * @returns {boolean}
 */
function validateLoginForm(e) {
  const email = document.querySelector('#loginForm [name="email"]');
  const pass  = document.querySelector('#loginForm [name="password"]');

  if (!email || !email.value.trim()) {
    showFormError('Please enter your email address.');
    e.preventDefault();
    return false;
  }
  if (!pass || !pass.value) {
    showFormError('Please enter your password.');
    e.preventDefault();
    return false;
  }
  // Let Flask handle the actual POST
  return true;
}

/**
 * Validate the signup form before submit.
 * @param {Event} e
 * @returns {boolean}
 */
function validateSignupForm(e) {
  const pass    = document.querySelector('#signupForm [name="password"]');
  const confirm = document.querySelector('#signupForm [name="confirm_password"]');
  const terms   = document.querySelector('#signupForm [name="terms"]');

  if (pass && confirm && pass.value !== confirm.value) {
    showFormError('Passwords do not match.');
    e.preventDefault();
    return false;
  }
  if (pass && scorePassword(pass.value) < 2) {
    showFormError('Please choose a stronger password.');
    e.preventDefault();
    return false;
  }
  if (terms && !terms.checked) {
    showFormError('You must agree to the Terms of Service.');
    e.preventDefault();
    return false;
  }
  return true;
}

/**
 * Show an error banner at the top of the form.
 * @param {string} msg
 */
function showFormError(msg) {
  let banner = document.getElementById('formErrorBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id        = 'formErrorBanner';
    banner.className = 'flash flash-error';
    const form = document.querySelector('form');
    if (form) form.prepend(banner);
  }
  banner.textContent = '⚠ ' + msg;
  banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ══════════════════════════════════════════
   INIT — wire up events on DOMContentLoaded
   ══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Login form validation
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', validateLoginForm);
  }

  // Signup form validation
  const signupForm = document.getElementById('signupForm');
  if (signupForm) {
    signupForm.addEventListener('submit', validateSignupForm);

    // Live password strength
    const pwdField = signupForm.querySelector('[name="password"]');
    if (pwdField) {
      pwdField.addEventListener('input', () => checkPasswordStrength(pwdField.value));
    }
  }
});