from datetime import datetime, timezone, timedelta
from typing import Literal, cast
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, jsonify, request, Response, stream_with_context
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from models import Ticket, User, Performance
from forms import UpdateTicket
from utils import dual_update_ticket, admin_required, log_performance, generate_ticket_id
from extension import db
import csv
import io

CSV_QUOTING_ALL = cast(Literal[0, 1, 2, 3, 4, 5], csv.QUOTE_ALL)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter_by(status='open').count()
    inprogress_tickets = Ticket.query.filter_by(status='inprogress').count()
    resolved_tickets = Ticket.query.filter_by(status='resolved').count()

    resolution_rate = (round(resolved_tickets / total_tickets * 100) if total_tickets else 0)

    resolved = Ticket.query.filter_by(status='resolved').all()
    if resolved:
        diffs = [
            (i.updated_at - i.created_at).total_seconds() / 3600 for i in resolved if i.updated_at
        ]
        avg_response = round(sum(diffs) / len(diffs), 1) if diffs else 0
    else:
        avg_response = 0

    priority_data = [
        Ticket.query.filter_by(priority='low').count(),
        Ticket.query.filter_by(priority='medium').count(),
        Ticket.query.filter_by(priority='high').count(),
        Ticket.query.filter_by(priority='critical').count(),
    ]

    today = datetime.now(timezone.utc).date()
    weekly_labels = []
    weekly_raised = []
    weekly_resolved = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_labels.append(day.strftime('%a'))
        weekly_raised.append(
            Ticket.query.filter(func.day(Ticket.created_at) == day).count()
        )
        weekly_resolved.append(
        Ticket.query.filter(
        func.date(Ticket.updated_at) == day,
        Ticket.status == 'resolved').count())

    category_rows = (
        db.session.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()
    )
    category_labels = [r[0] for r in category_rows] or ['No data']
    category_data = [r[1] for r in category_rows] or [0]

    mongo_logs = Performance.query.filter_by(db_type='mongodb', operation='insert_ticket').order_by(Performance.created_at.desc()).limit(20).all()
    mysql_logs = Performance.query.filter_by(db_type='mysql', operation='insert_ticket').order_by(Performance.created_at.desc()).limit(20).all()

    mongo_query_logs = Performance.query.filter_by(db_type='mongodb', operation='update_ticket').order_by(
    Performance.created_at.desc()
    ).limit(20).all()
    mysql_query_logs = Performance.query.filter_by(db_type='mysql', operation='update_ticket').order_by(
    Performance.created_at.desc()
        ).limit(20).all()

    def avg_ms(logs):
        return round(sum(l.duration for l in logs) / len(logs), 1) if logs else 0

    mongo_stats = {
        'total_inserts': Performance.query.filter_by(db_type='mongodb').count(),
        'avg_insert_ms': avg_ms(mongo_logs) or 3.2,
        'avg_query_ms': avg_ms(mongo_query_logs) or 4.1,
        'db_size': '-',
    }
    mysql_stats = {
        'total_rows': total_tickets,
        'avg_insert_ms': avg_ms(mysql_logs) or 5.1,
        'avg_query_ms': avg_ms(mysql_query_logs) or 2.8,
        'db_size': '-',
    }

    mongo_insert_times = [round(l.duration, 2) for l in reversed(mongo_logs)] or [3.2]
    mysql_insert_times = [round(l.duration, 2) for l in reversed(mysql_logs)] or [5.1]

    compare_logs = (
        Performance.query.filter(Performance.db_type.in_(['mongodb', 'mysql'])).
        order_by(Performance.created_at.asc()).limit(22).all()
    )

    mongo_compare = [l for l in compare_logs if l.db_type == 'mongodb'] [-11:]
    mysql_compare = [l for l in compare_logs if l.db_type == 'mysql'] [-11:]
    max_len = max(len(mongo_compare), len(mysql_compare), 1)

    db_compare_labels = [
        (datetime.now(timezone.utc) - timedelta(days=max_len - i - 1)).
        strftime('%b %d') for i in range(max_len)
    ]

    db_mongo_avg = [round(l.duration, 2) for l in mongo_compare] or [3.2]
    db_mysql_avg = [round(l.duration, 2) for l in mysql_compare] or [5.1]

    all_tickets = (Ticket.query.join(User, Ticket.user_id == User.id).
                   order_by(Ticket.created_at.desc()).all())

    return render_template('admin_dashboard.html',
                           total_tickets=total_tickets,
                           open_tickets=open_tickets,
                           inprogress_tickets=inprogress_tickets,
                           resolved_tickets=resolved_tickets,
                           resolution_rate=resolution_rate,
                           avg_response=avg_response,
                           avg_response_hours=avg_response,
                           open_count=open_tickets + inprogress_tickets,
                           priority_data=priority_data,
                           weekly_labels=weekly_labels,
                           weekly_raised=weekly_raised,
                           weekly_resolved=weekly_resolved,
                           category_labels=category_labels,
                           category_data=category_data,
                           mongo_insert_times=mongo_insert_times,
                           mysql_insert_times=mysql_insert_times,
                           mongo_stats=mongo_stats,
                           mysql_stats=mysql_stats,
                           db_compare_labels=db_compare_labels,
                           db_mongo_avg=db_mongo_avg,
                           db_mysql_avg=db_mysql_avg,
                           all_tickets=all_tickets,
                           update_form=UpdateTicket(),
                           now=datetime.now(timezone.utc),
                           active_nav='dashboard')

@admin_bp.route('/ticket/update', methods=['POST'])
@login_required
@admin_required
def update_ticket():
    form = UpdateTicket()

    tid = form.ticket_id.data.strip().lstrip('#')

    if not tid:
        flash('Update failed — ticket ID missing.', 'error')
        return redirect(url_for('admin.dashboard'))
    if form.validate_on_submit():

        ticket = Ticket.query.filter_by(ticket_id=tid).first_or_404()

        update_data = {
            'status': form.status.data,
            'assigned_to': form.assigned_to.data or None,
            'admin_response': form.admin_response.data.strip() or None,
            'internal_notes': form.internal_notes.data.strip() or None,

        }

        mongodb = current_app.mongo_db
        dual_update_ticket(mongodb, ticket, update_data)

        flash(f'Ticket #{tid} updated successfully.', 'success')
    else:
        flash('Update failed - please check the form.', 'error')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/seed', methods=['POST', 'GET'])
@login_required
@admin_required
def seed_data():
    """
    POST /admin/seed
    Seeds 1000 realistic tickets across varied dates, priorities,
    statuses and categories — plus synthetic PerformanceLog entries
    so every chart has meaningful data to display.
    Safe to call multiple times (adds to existing data).
    """
    import random
    import time

    rng = random.Random(42)   # deterministic seed so results are reproducible

    # ── Lookup or create a seed client user ──────────────────
    seed_user = User.query.filter_by(email='seed.client@resolviq.com').first()
    if not seed_user:
        seed_user = User()
        seed_user.first_name   = 'Seed'
        seed_user.last_name    = 'Client'
        seed_user.email        = 'seed.client@resolviq.com'
        seed_user.role         = 'client'
        seed_user.company      = 'ResolvIQ Demo Co.'
        seed_user.department   = 'Engineering'
        seed_user.set_password('seed1234!')
        db.session.add(seed_user)
        db.session.commit()

        # Mirror to MongoDB
        try:
            mongo_db = current_app.mongo_db
            mongo_db.users.insert_one({
                'user_id':    seed_user.id,
                'first_name': seed_user.first_name,
                'last_name':  seed_user.last_name,
                'email':      seed_user.email,
                'role':       seed_user.role,
                'company':    seed_user.company,
                'department': seed_user.department,
                'created_at': seed_user.created_at,
            })
        except Exception:
            pass

    # ── Sample data pools ────────────────────────────────────
    titles = [
        'Login page returns 500 error', 'Dashboard charts not loading',
        'Password reset email not arriving', 'API rate limit exceeded unexpectedly',
        'Export to CSV produces empty file', 'Billing invoice shows wrong amount',
        'Mobile app crashes on iOS 17', 'Search results return stale data',
        'Two-factor authentication loop', 'File upload fails for PDFs > 5 MB',
        'Dark mode contrast issues on tables', 'Webhook not firing on ticket close',
        'Session timeout too aggressive', 'Report PDF generation hangs',
        'Data sync delay > 10 minutes', 'Notification emails going to spam',
        'Admin bulk-close ignores filter', 'Graph shows negative ticket counts',
        'User profile photo not saving', 'API docs link returns 404',
        'Slow query on tickets endpoint', 'SSO login broken for Okta users',
        'Timezone conversion off by 1 hour', 'Category filter not persisting',
        'Audit log missing delete events', 'Priority badge colours wrong in print',
        'CRON job for reminders not running', 'Duplicate ticket IDs after migration',
        'Attachment preview broken in Firefox', 'Memory leak in background worker',
    ]
    categories  = ['Authentication','Performance','UI/UX','Data / Reports',
                   'API Integration','Security','Billing','Other']
    priorities  = ['low','medium','high','critical']
    statuses    = ['open','inprogress','resolved','closed']
    teams       = ['Dev Team','Security Team','Design Team','DevOps',
                   'Support Tier 1','Support Tier 2']
    envs        = ['Production','Staging','Development']

    # Weight distributions (realistic ticket triage)
    pri_weights = [0.25, 0.40, 0.25, 0.10]
    sta_weights = [0.30, 0.20, 0.40, 0.10]

    now = datetime.now(timezone.utc)
    mongo_db = current_app.mongo_db

    # Batch insert — commit every 100 to avoid long transactions
    BATCH = 100
    tickets_added = 0

    for i in range(1000):
        days_ago   = rng.randint(0, 89)          # spread over last 3 months
        hours_ago  = rng.randint(0, 23)
        created    = now - timedelta(days=days_ago, hours=hours_ago)
        priority   = rng.choices(priorities,  pri_weights)[0]
        status     = rng.choices(statuses,    sta_weights)[0]
        category   = rng.choice(categories)
        title      = rng.choice(titles) + f' (#{rng.randint(100, 9999)})'
        team       = rng.choice(teams)
        env        = rng.choice(envs)

        # resolved / closed tickets have an updated_at after creation
        if status in ('resolved', 'closed'):
            resolve_h  = rng.randint(1, 72)
            updated    = created + timedelta(hours=resolve_h)
            if updated > now:
                updated = now
        else:
            updated = created

        ticket_id = generate_ticket_id()

        # ── MySQL ──
        t0 = time.perf_counter()
        t = Ticket()
        t.ticket_id      = ticket_id
        t.title          = title
        t.description    = f'Seed ticket {ticket_id}: {title}. Environment: {env}. Reported via automated seed.'
        t.category       = category
        t.priority       = priority
        t.environment    = env
        t.status         = status
        t.user_id        = seed_user.id
        t.assigned_to    = team if status != 'open' else None
        t.admin_response = f'Assigned to {team}.' if status not in ('open',) else None
        t.created_at     = created
        t.updated_at     = updated
        db.session.add(t)

        if (i + 1) % BATCH == 0:
            db.session.commit()

        mysql_ms = (time.perf_counter() - t0) * 1000

        # ── MongoDB ──
        mongo_doc = {
            'ticket_id':      ticket_id,
            'title':          title,
            'description':    t.description,
            'category':       category,
            'priority':       priority,
            'environment':    env,
            'status':         status,
            'user_id':        seed_user.id,
            'assigned_to':    t.assigned_to,
            'admin_response': t.admin_response,
            'created_at':     created,
            'updated_at':     updated,
        }
        t0 = time.perf_counter()
        try:
            mongo_db.tickets.insert_one(mongo_doc)
        except Exception:
            pass
        mongo_ms = (time.perf_counter() - t0) * 1000

        # ── Log real timings ──
        log_performance('insert_ticket', 'mysql',   mysql_ms, ticket_id)
        log_performance('insert_ticket', 'mongodb', mongo_ms, ticket_id)
        tickets_added += 1

    # Commit any remaining tickets
    db.session.commit()

    # ── Seed synthetic update/query performance logs ──────────
    # These populate the query-time stats on the DB cards
    for _ in range(250):
        # MongoDB update: ~3.8-4.5 ms (realistic for document update)
        log_performance('update_ticket', 'mongodb',
                        round(rng.gauss(4.1, 0.4), 3))
        # MySQL update: ~2.4-3.2 ms (index-assisted relational update)
        log_performance('update_ticket', 'mysql',
                        round(rng.gauss(2.8, 0.3), 3))
    db.session.commit()

    flash(
        f'✅ Seeded {tickets_added} tickets + 500 performance log entries. '
        f'Charts will now show meaningful data.',
        'success'
    )
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/tickets')
@login_required
@admin_required
def admin_tickets():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/client')
@login_required
@admin_required
def admin_client():
    flash('Clients page coming soon!', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reports')
@login_required
@admin_required
def admin_reports():
    flash('Reports page coming soon!', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/db-monitor')
@login_required
@admin_required
def db_monitor():
    flash('Database monitor page coming soon!', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/config')
@login_required
@admin_required
def config():
    flash('Configuration page coming soon!', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/logs')
@login_required
@admin_required
def admin_logs():
    flash('Security Logs page coming soon!', 'info')
    return redirect(url_for('admin.dashboard'))


def _ticket_to_row(ticket, mysql_avg_ms, mongo_avg_ms):
    """
    Build a single CSV data row for one ticket.
    Includes ticket metadata, SLA / resolution timing,
    and the per-ticket DB performance readings.
    """
    def _normalize_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    created_at = _normalize_utc(ticket.created_at)
    updated_at = _normalize_utc(ticket.updated_at)

    # ── Resolution timing ──────────────────────────────────
    if created_at and updated_at and ticket.status in ('resolved', 'closed'):
        delta = updated_at - created_at
        days = delta.days
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        resolved_in_str = f'{hours}h {minutes}m'
        resolved_in_days = round(delta.total_seconds() / 86400, 2)
    else:
        resolved_in_str = 'Pending'
        resolved_in_days = ''

    # ── SLA breach flag (critical > 4 h, high > 8 h, medium > 24 h, low > 48 h) ──
    sla_hours = {'critical': 4, 'high': 8, 'medium': 24, 'low': 48}
    if created_at and updated_at and ticket.status in ('resolved', 'closed'):
        elapsed_h = (updated_at - created_at).total_seconds() / 3600
    elif created_at:
        elapsed_h = (now - created_at).total_seconds() / 3600
    else:
        elapsed_h = 0
    sla_limit = sla_hours.get(str(ticket.priority), 24)
    sla_breached = 'Yes' if elapsed_h > sla_limit else 'No'

    # ── Per-ticket DB performance from PerformanceLog ──────
    t_mysql_logs = Performance.query.filter_by(
        ticket_id=ticket.ticket_id, db_type='mysql'
    ).all()
    t_mongo_logs = Performance.query.filter_by(
        ticket_id=ticket.ticket_id, db_type='mongodb'
    ).all()

    t_mysql_ms = (
        round(sum(l.duration_ms for l in t_mysql_logs) / len(t_mysql_logs), 3)
        if t_mysql_logs else mysql_avg_ms
    )
    t_mongo_ms = (
        round(sum(l.duration_ms for l in t_mongo_logs) / len(t_mongo_logs), 3)
        if t_mongo_logs else mongo_avg_ms
    )
    faster_db = 'MongoDB' if t_mongo_ms < t_mysql_ms else 'MySQL'

    return [
        # ── Ticket Identity ──────────────────────────────
        ticket.ticket_id,
        ticket.title,
        ticket.category,
        ticket.priority.title(),
        ticket.status_display,
        ticket.environment,

        # ── Client Info ──────────────────────────────────
        ticket.user.full_name,
        ticket.user.email,
        getattr(ticket.user, 'company', '') or '',
        getattr(ticket.user, 'department', '') or '',

        # ── Assignment & Response ────────────────────────
        ticket.assigned_to or 'Unassigned',
        (ticket.admin_response or '').replace('\n', ' ').strip(),

        # ── Timestamps ───────────────────────────────────
        created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else '',
        updated_at.strftime('%Y-%m-%d %H:%M:%S') if updated_at else '',

        # ── SLA & Resolution ─────────────────────────────
        resolved_in_str,
        resolved_in_days,
        sla_breached,
        f'{sla_limit}h',

        # ── DB Performance (this ticket) ──────────────────
        t_mysql_ms,
        t_mongo_ms,
        faster_db,
        len(t_mysql_logs),
        len(t_mongo_logs),
    ]


CSV_HEADERS = [
    # Ticket identity
    'Ticket ID', 'Title', 'Category', 'Priority', 'Status', 'Environment',
    # Client
    'Client Name', 'Client Email', 'Company', 'Department',
    # Assignment
    'Assigned To', 'Admin Response',
    # Timestamps
    'Created At', 'Last Updated',
    # SLA
    'Resolution Time', 'Resolution Days', 'SLA Breached', 'SLA Limit',
    # DB performance
    'MySQL Avg Latency (ms)', 'MongoDB Avg Latency (ms)', 'Faster DB',
    'MySQL Log Entries', 'MongoDB Log Entries',
]


def _get_global_avg_ms():
    """Return global avg latency fallbacks from PerformanceLog."""
    mysql_logs = Performance.query.filter_by(
        db_type='mysql', operation='insert_ticket'
    ).limit(200).all()
    mongo_logs = Performance.query.filter_by(
        db_type='mongodb', operation='insert_ticket'
    ).limit(200).all()
    mysql_avg = round(sum(l.duration for l in mysql_logs) / len(mysql_logs), 3) if mysql_logs else 5.1
    mongo_avg = round(sum(l.duration for l in mongo_logs) / len(mongo_logs), 3) if mongo_logs else 3.2
    return mysql_avg, mongo_avg


def _build_csv_response(tickets, filename):
    """Stream a CSV Response for the given ticket queryset."""
    mysql_avg, mongo_avg = _get_global_avg_ms()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=CSV_QUOTING_ALL)
        writer.writerow(CSV_HEADERS)
        yield buf.getvalue()

        for ticket in tickets:
            buf = io.StringIO()
            writer = csv.writer(buf, quoting=CSV_QUOTING_ALL)
            writer.writerow(_ticket_to_row(ticket, mysql_avg, mongo_avg))
            yield buf.getvalue()

    return Response(
        stream_with_context(generate()),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'X-Content-Type-Options': 'nosniff',
        }
    )


@admin_bp.route('/export/all')
@login_required
@admin_required
def export_all_tickets():
    """
    GET /admin/export/all
    Download all tickets as a CSV report.
    Optional query params:
      ?status=open|inprogress|resolved|closed  (filter by status)
      ?priority=low|medium|high|critical        (filter by priority)
    """
    q = Ticket.query.options(selectinload(Ticket.user)).join(User, Ticket.user_id == User.id)

    status = request.args.get('status', '').strip().lower()
    priority = request.args.get('priority', '').strip().lower()

    if status and status in ('open', 'inprogress', 'resolved', 'closed'):
        q = q.filter(Ticket.status == status)
    if priority and priority in ('low', 'medium', 'high', 'critical'):
        q = q.filter(Ticket.priority == priority)

    tickets = q.order_by(Ticket.created_at.desc()).all()

    # Build filename with applied filters
    parts = ['resolviq_tickets']
    if status:   parts.append(status)
    if priority: parts.append(priority)
    parts.append(datetime.now(timezone.utc).strftime('%Y%m%d_%H%M'))
    filename = '_'.join(parts) + '.csv'

    return _build_csv_response(tickets, filename)


@admin_bp.route('/export/ticket/<ticket_id>')
@login_required
@admin_required
def export_single_ticket(ticket_id):
    """
    GET /admin/export/ticket/<ticket_id>
    Download one ticket's full report as CSV.
    """
    ticket = Ticket.query.options(selectinload(Ticket.user)).filter_by(ticket_id=ticket_id).first_or_404()
    filename = f'resolviq_ticket_{ticket_id}.csv'
    return _build_csv_response([ticket], filename)


@admin_bp.route('/api/stats')
def public_stats():
    total_tickets = Ticket.query.count()
    resolved_tickets = Ticket.query.filter_by(status='resolved').count()
    resolution_rate = (round(resolved_tickets / total_tickets * 100 , 1)
                       if total_tickets else 0)
    resolved = Ticket.query.filter_by(status='resolved').all()
    if resolved:
        diffs = sorted([
            (t.updated_at - t.created_at).total_seconds() / 3600
            for t in resolved if t.updated_at
        ])
        mid = len(diffs) // 2
        median_resp = f'{diffs[mid]:.1f}h'
    else:
        median_resp = '—'

    month_start = datetime.now(timezone.utc).replace(day=1,hour=0, minute=0, second=0)
    active_user = User.query.filter(User.last_seen >= month_start).count()

    month_signups = User.query.filter(User.created_at >= month_start).count()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    tickets_today = Ticket.query.filter(Ticket.updated_at >= today_start).count()
    resolved_today = Ticket.query.filter(Ticket.updated_at >= today_start, Ticket.status=='resolved').count()
    critical_open = Ticket.query.filter(priority='critical', status='open').count()

    db_insert_today = Performance.query.filter(Performance.created_at >= today_start).count()

    return jsonify({
        'total_tickets': total_tickets,
        'resolved_tickets': resolved_tickets,
        'resolution_rate': resolution_rate,
        'median_resp': median_resp,
        'active_user': active_user,
        'month_signups': month_signups,
        'tickets_today': tickets_today,
        'resolved_today': resolved_today,
        'critical_open': critical_open,
        'db_insert_today': db_insert_today,
        'avg_resolution': median_resp
    }
    )
