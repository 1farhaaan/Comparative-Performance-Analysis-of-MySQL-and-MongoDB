/**
 * index.js — ResolvIQ Landing Page
 *
 * Handles:
 *  - Live stats fetch from Flask /api/stats
 *  - Smooth count-up animations for all live numbers
 *  - IntersectionObserver to trigger on scroll
 *
 * Flask connection:
 *   Uncomment fetch('/api/stats') block and remove DEMO object
 *   once your Flask route is ready.
 *
 * Flask route to create in app.py:
 * ─────────────────────────────────────────────
 *  @app.route('/api/stats')
 *  def public_stats():
 *      from datetime import date, datetime, timedelta
 *      from sqlalchemy import func, text
 *
 *      total    = Ticket.query.count()
 *      resolved = Ticket.query.filter_by(status='resolved').count()
 *      rate     = round(resolved / total * 100, 1) if total else 0
 *      avg_s    = db.session.query(
 *                   func.avg(func.timestampdiff(
 *                       text('SECOND'),
 *                       Ticket.created_at, Ticket.updated_at
 *                   ))
 *                 ).filter(Ticket.status == 'resolved').scalar()
 *      resp_hrs = round((avg_s or 0) / 3600, 1)
 *      today    = date.today()
 *
 *      return jsonify(
 *          total          = total,
 *          resolved       = resolved,
 *          rate           = rate,
 *          resp           = resp_hrs,
 *          signups_month  = User.query.filter(
 *                               User.created_at >= datetime.now() - timedelta(30)
 *                           ).count(),
 *          today_raised   = Ticket.query.filter(
 *                               func.date(Ticket.created_at) == today
 *                           ).count(),
 *          today_resolved = Ticket.query.filter(
 *                               func.date(Ticket.updated_at) == today,
 *                               Ticket.status == 'resolved'
 *                           ).count(),
 *          avg_mins       = round((avg_s or 0) / 60),
 *          critical_open  = Ticket.query.filter(
 *                               Ticket.priority == 'critical',
 *                               Ticket.status   != 'resolved'
 *                           ).count(),
 *          inserts_today  = PerformanceLog.query.filter(
 *                               func.date(PerformanceLog.created_at) == today
 *                           ).count(),
 *          s1 = total,
 *          s2 = rate,
 *          s3 = round((avg_s or 0) / 60),
 *          s4 = User.query.filter(
 *                   User.last_seen >= datetime.now() - timedelta(30)
 *               ).count()
 *      )
 * ─────────────────────────────────────────────
 */

'use strict';

/* ── Demo data — remove when Flask /api/stats is live ── */
const DEMO_STATS = {
  total:          218,
  resolved:       193,
  rate:           88.5,
  resp:           4.2,
  signups_month:  34,
  today_raised:   12,
  today_resolved: 9,
  avg_mins:       47,
  critical_open:  3,
  inserts_today:  24,
  s1: 15400,
  s2: 94.2,
  s3: 4,
  s4: 2400,
};

/**
 * Animate a number from 0 → target inside element #id.
 * @param {string} id       - DOM element id
 * @param {number} target   - Final number
 * @param {number} ms       - Animation duration in ms
 * @param {string} suffix   - Optional suffix e.g. '%', 'h', 'min'
 * @param {number} decimals - Decimal places (0 = integer)
 */
function countUp(id, target, ms, suffix = '', decimals = 0) {
  const el = document.getElementById(id);
  if (!el || target == null) return;

  let current = 0;
  const step  = target / (ms / 16);          // 16ms ≈ 60fps

  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    const display = decimals
      ? current.toFixed(decimals)
      : Math.floor(current).toLocaleString();
    el.textContent = display + suffix;
    if (current >= target) clearInterval(timer);
  }, 16);
}

/**
 * Apply a full stats payload to all counter elements on the page.
 * @param {Object} data - Stats object (matches Flask JSON keys)
 */
function applyStats(data) {
  // Hero counters
  countUp('cntTotal',    data.total,          1600);
  countUp('cntResolved', data.resolved,        1600);
  countUp('cntRate',     data.rate,            1800, '%', 1);
  countUp('cntResp',     data.resp,            1400, 'h', 1);

  // Stats bar
  countUp('s1', data.s1, 2000);
  countUp('s2', data.s2, 1700, '%', 1);
  countUp('s3', data.s3, 1400, 'min');
  countUp('s4', data.s4, 1900);

  // How It Works step live numbers
  countUp('hw1', data.signups_month,   1300);
  countUp('hw2', data.today_raised,    1100);
  countUp('hw3', data.today_resolved,  1100);
  countUp('hw4', data.avg_mins,        1300, 'min');

  // Feature card numbers
  countUp('fc1', data.critical_open,  900);
  countUp('fc2', data.inserts_today,  1100);
}

/**
 * Fetch live stats from Flask, fall back to demo data if unavailable.
 */
async function loadStats() {
  /* ── Uncomment the block below once Flask /api/stats is ready ──
  try {
    const res = await fetch('/api/stats');
    if (res.ok) {
      applyStats(await res.json());
      return;
    }
  } catch (err) {
    console.warn('[ResolvIQ] Stats API unavailable, using demo data:', err.message);
  }
  ── End of Flask block ── */

  applyStats(DEMO_STATS);
}

/* ── Trigger animations when the stats bar scrolls into view ── */
(function initObserver() {
  const statsBar = document.querySelector('.stats-bar');
  if (!statsBar) return;

  let fired = false;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !fired) {
          fired = true;
          loadStats();
          observer.disconnect();
        }
      });
    },
    { threshold: 0.1 }
  );
  observer.observe(statsBar);
})();

/* ── Optional: auto-refresh every 60s when using live endpoint ──
setInterval(async () => {
  try {
    const res = await fetch('/api/stats');
    if (res.ok) applyStats(await res.json());
  } catch (e) {}
}, 60_000);
── */