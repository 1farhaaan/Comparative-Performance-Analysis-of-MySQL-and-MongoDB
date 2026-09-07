/**
 * admin.js — ResolvIQ Admin Dashboard  (UI logic only)
 *
 * Responsibilities:
 *  - Update Ticket modal  (open / close / save → Flask POST)
 *  - Quick-resolve button (POST to Flask via hidden form)
 *  - Table search and status filter
 *  - DOMContentLoaded init (calls initAllCharts from charts.js)
 *
 * Chart initialisation has been separated into:
 *   static/js/charts.js
 *
 * Load order in admin_dashboard.html:
 *   1. Chart.js  (CDN)
 *   2. charts.js (this project)
 *   3. admin.js  (this file)
 */

'use strict';

let _activeStatus = '';
let _activePriority = '';

/* ══════════════════════════════════════════
   UPDATE TICKET MODAL
   ══════════════════════════════════════════ */

/**
 * Open the Update Ticket modal, populate fields with
 * the ticket's current values.
 * @param {string} ticketId     — e.g. "TK-0042"
 * @param {string} currentStatus — e.g. "open"
 */
function openUpdateModal(ticketId, currentStatus) {
  document.getElementById('updateTidLabel').textContent = ticketId;
  document.getElementById('updateTicketId').value       = ticketId;
  document.getElementById('updateStatus').value         = currentStatus;
  document.getElementById('adminResponse').value        = '';

  // Clear any previous validation error
  const err = document.getElementById('updateErrorBanner');
  if (err) err.style.display = 'none';

  document.getElementById('updateOverlay').classList.add('open');
}

/** Close the Update Ticket modal. */
function closeUpdateModal() {
  document.getElementById('updateOverlay').classList.remove('open');
}

/**
 * Validate then submit the Update Ticket WTForms form to Flask.
 * Route: POST /admin/tickets/update
 */
function saveTicketUpdate() {
  const form   = document.getElementById('updateForm');
  if (!form) return;

  const tid    = document.getElementById('updateTicketId').value;
  const status = document.getElementById('updateStatus').value;

  if (!tid)    { showUpdateError('No ticket selected.');    return; }
  if (!status) { showUpdateError('Please select a status.'); return; }

  // Submit WTForms form — CSRF token is included via hidden_tag()
  form.submit();
}

/** Show an inline error banner inside the update modal. */
function showUpdateError(msg) {
  let el = document.getElementById('updateErrorBanner');
  if (!el) {
    el           = document.createElement('div');
    el.id        = 'updateErrorBanner';
    el.className = 'flash flash-error';
    el.style.cssText = 'margin:0 0 12px;border-radius:8px;padding:10px 14px;font-size:13px';
    const body = document.querySelector('#updateOverlay .modal-body');
    if (body) body.prepend(el);
  }
  el.textContent   = '⚠ ' + msg;
  el.style.display = 'block';
}

/* ══════════════════════════════════════════
   QUICK RESOLVE (table row button)
   ══════════════════════════════════════════ */

/**
 * One-click resolve directly from the tickets table.
 * Dynamically builds a hidden form and POSTs to the
 * existing update_ticket Flask route with status=resolved.
 *
 * Requires:  updateTicketUrl  (injected from template — see below)
 * @param {HTMLElement} btn — The "✓ Resolve" button clicked
 */
function resolveTicket(btn) {
  const row    = btn.closest('tr');
  const idCell = row ? row.querySelector('.t-id-cell') : null;
  const tid    = idCell ? idCell.textContent.trim() : null;
  if (!tid) { console.error('[admin.js] resolveTicket: could not find ticket ID'); return; }

  // Grab CSRF token from the WTForms hidden tag already on the page
  const csrf = document.querySelector('[name="csrf_token"]');
  if (!csrf) { console.error('[admin.js] CSRF token not found'); return; }

  // Build a transient hidden form — reuses update_ticket route
  const form    = document.createElement('form');
  form.method   = 'POST';
  form.action   = updateTicketUrl;   // var injected via <script> in template

  const fields = {
    csrf_token:     csrf.value,
    ticket_id:      tid,
    status:         'resolved',
    assigned_to:    '',
    admin_response: '',
    internal_notes: '',
  };

  Object.entries(fields).forEach(([name, value]) => {
    const input = document.createElement('input');
    input.type  = 'hidden';
    input.name  = name;
    input.value = value;
    form.appendChild(input);
  });

  document.body.appendChild(form);
  form.submit();
}

/* ══════════════════════════════════════════
   TABLE SEARCH & STATUS FILTER
   ══════════════════════════════════════════ */

/**
 * Live-filter the tickets table by text content.
 * @param {string} query
 */
function searchTickets(query) {
  const q    = query.toLowerCase();
  const rows = document.querySelectorAll('#ticketsBody tr');
  rows.forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

/**
 * Filter tickets table by status badge text.
 * @param {string} status — '' = show all
 */
function filterByStatus(status) {
  _activeStatus = (status || '').toLowerCase().trim();
  const rows = document.querySelectorAll('#ticketsBody tr');
  rows.forEach(row => {
    const badge = row.querySelector('.badge');
    const s     = badge ? badge.textContent.trim().toLowerCase().replace(/\s+/g, '') : '';
    row.style.display = (!_activeStatus || s === _activeStatus) ? '' : 'none';
  });
}

/* ══════════════════════════════════════════
   INIT
   ══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

  // Initialise all Chart.js charts (defined in charts.js)
  if (typeof initAllCharts === 'function') {
    initAllCharts();
  } else {
    console.warn('[admin.js] initAllCharts not found — ensure charts.js is loaded before admin.js');
  }

  // Close update modal when clicking the overlay background
  document.getElementById('updateOverlay')?.addEventListener('click', e => {
    if (e.target.id === 'updateOverlay') closeUpdateModal();
  });
});


/* ══════════════════════════════════════════
   EXPORT ALL TICKETS (CSV)
   ══════════════════════════════════════════ */
function exportAllTickets() {
  const params = new URLSearchParams();
  if (_activeStatus)   params.set('status',   _activeStatus);
  if (_activePriority) params.set('priority', _activePriority);
  const qs  = params.toString();
  window.location.href = exportAllUrl + (qs ? '?' + qs : '');
}

// ── Export dropdown toggle ────────────────────────────────────
function toggleExportMenu(e) {
  e.stopPropagation();
  document.getElementById('exportMenu').classList.toggle('open');
}

// Close export menu when clicking outside
document.addEventListener('click', () => {
  document.getElementById('exportMenu')?.classList.remove('open');
});
