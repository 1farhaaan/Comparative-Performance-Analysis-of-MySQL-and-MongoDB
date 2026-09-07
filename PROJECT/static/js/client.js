/**
 * client.js — ResolvIQ Client Ticket Dashboard
 *
 * Handles:
 *  - Raise Ticket modal (open / close)
 *  - Priority selector in the modal
 *  - Ticket accordion expand / collapse
 *  - Filter buttons (All / Open / In Progress / Resolved)
 *  - Demo ticket insertion into DOM (replace with Flask POST)
 *
 * Flask integration points are marked with // FLASK:
 */

'use strict';

/* ══════════════════════════════════════════
   MODAL — Raise New Ticket
   ══════════════════════════════════════════ */

function openModal() {
  const overlay = document.getElementById('modalOverlay');
  if (overlay) overlay.classList.add('open');
  // Clear any previous error banner when reopening
  const err = document.getElementById('ticketErrorBanner');
  if (err) err.style.display = 'none';
}

function closeModal() {
  const overlay = document.getElementById('modalOverlay');
  if (overlay) overlay.classList.remove('open');
}

/** Close modal when clicking outside the inner box */
function handleOverlayClick(e) {
  if (e.target && e.target.id === 'modalOverlay') closeModal();
}

/* ══════════════════════════════════════════
   PRIORITY SELECTOR
   ══════════════════════════════════════════ */

/**
 * Highlight the selected priority button and update hidden input.
 * @param {string} priority - 'low'|'medium'|'high'|'critical'
 * @param {HTMLElement} btn
 */
function setPriority(priority, btn) {
  document.querySelectorAll('.priority-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const input = document.getElementById('priorityInput');
  if (input) input.value = priority;
}

/* ══════════════════════════════════════════
   ACCORDION — expand / collapse ticket rows
   ══════════════════════════════════════════ */

/**
 * Toggle expanded state on a ticket item.
 * @param {HTMLElement} head - The .ticket-head that was clicked
 */
function toggleTicket(head) {
  const item = head.closest('.ticket-item');
  if (item) item.classList.toggle('expanded');
}

/* ══════════════════════════════════════════
   FILTER — show/hide tickets by status
   ══════════════════════════════════════════ */

/**
 * @param {string} status - 'all'|'open'|'inprogress'|'resolved'
 * @param {HTMLElement} btn - The clicked filter button
 */
function filterTickets(status, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  document.querySelectorAll('.ticket-item').forEach(item => {
    const show = status === 'all' || item.dataset.status === status;
    item.style.display = show ? '' : 'none';
  });
}

/* ══════════════════════════════════════════
   SUBMIT TICKET
   (Demo — replace body with Flask POST)
   ══════════════════════════════════════════ */

/**
 * Handle "Submit Ticket" click.
 *
 * FLASK: Replace this entire function body with a real form
 * POST. In Flask, the form action should be:
 *   action="{{ url_for('create_ticket') }}" method="POST"
 * Then remove the onclick="submitTicket()" on the button
 * and use type="submit" instead.
 *
 * Flask route (app.py):
 * ────────────────────────────────────────────
 *  @app.route('/tickets/create', methods=['POST'])
 *  @login_required
 *  def create_ticket():
 *      title       = request.form.get('title')
 *      category    = request.form.get('category')
 *      priority    = request.form.get('priority', 'medium')
 *      description = request.form.get('description')
 *      environment = request.form.get('environment', 'Production')
 *      steps       = request.form.get('steps', '')
 *      attachment  = request.form.get('attachment', '')
 *
 *      # Write to MongoDB
 *      mongo.db.tickets.insert_one({
 *          'title': title, 'category': category,
 *          'priority': priority, 'description': description,
 *          'status': 'open', 'user_id': str(current_user.id),
 *          'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()
 *      })
 *
 *      # Write to MySQL
 *      ticket = Ticket(title=title, category=category, priority=priority,
 *                      description=description, status='open',
 *                      user_id=current_user.id)
 *      db.session.add(ticket)
 *      db.session.commit()
 *
 *      flash('Ticket raised successfully!', 'success')
 *      return redirect(url_for('client_dashboard'))
 * ────────────────────────────────────────────
 */
function submitTicket() {
  const form = document.getElementById('ticketForm');
  if (!form) return;
  // ── Client-side validation ──────────────────────────────
  const title    = form.querySelector('[name="title"]')?.value?.trim();
  const category = form.querySelector('[name="category"]')?.value;
  const desc     = form.querySelector('[name="description"]')?.value?.trim();

  if (!title) {
    showTicketError('Please enter an issue title.');
    return;
  }
  if (!category) {
    showTicketError('Please select a category.');
    return;
  }
  if (!desc) {
    showTicketError('Please enter an issue description.');
    return;
  }

  // ── Ensure priority hidden input is set ─────────────────
  const priorityInput = document.getElementById('priorityInput');
  if (priorityInput && !priorityInput.value) {
    priorityInput.value = 'medium';
  }

  // ── Submit to Flask ──────────────────────────────────────
  form.submit();
}

  // ── Demo: inject a new ticket card into the accordion ──
function showTicketError(msg) {
  let el = document.getElementById('ticketErrorBanner');
  if (!el) {
    el = document.createElement('div');
    el.id        = 'ticketErrorBanner';
    el.className = 'flash flash-error';
    el.style.cssText = 'margin:0 0 12px;border-radius:8px;padding:10px 14px';
    const body = document.querySelector('.modal-body');
    if (body) body.prepend(el);
  }
  el.textContent = '⚠ ' + msg;
  el.style.display = 'block';
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ── Utility helpers ── */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
function capitalise(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/* ══════════════════════════════════════════
   INIT
   ══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Default priority to medium on load
  const defaultPrio = document.querySelector('.priority-btn[data-p="medium"]');
  if (defaultPrio) defaultPrio.classList.add('active');
});
