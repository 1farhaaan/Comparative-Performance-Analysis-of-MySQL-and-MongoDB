"""
utils.py — ResolvIQ Helper Utilities

- generate_ticket_id()   — create unique #TK-XXXX id
- dual_write_ticket()    — write to MongoDB AND MySQL, log timings
- dual_write_user()      — write new user to both DBs
- log_performance()      — save timing to PerformanceLog table
- timesince()            — Jinja2 filter: "2 hours ago"
- admin_required()       — route decorator for admin-only pages
"""
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Optional
from flask import abort
from flask_login import current_user
from models import Ticket, Performance
from extension import db

# ── Ticket ID ──────────────────────────────────────────────────

def generate_ticket_id() -> str:
    """
    Generate a unique ticket ID like TK-1042.
    Queries MySQL for the highest existing numeric suffix and increments.
    Falls back to 1000 if no tickets exist yet.
    """
    last = Ticket.query.order_by(Ticket.id.desc()).first()
    if last and last.ticket_id:
        try:
            num = int(last.ticket_id.split('-')[1]) + 1
        except (IndexError, ValueError):
            num = 1000
    else:
        num = 1000
    return f'TK-{num}'


# ── Performance Logging ────────────────────────────────────────

def log_performance(operation: str, db_type: str, duration_ms: float, ticket_id: Optional[str] = None) -> None:
    """
    Save a timing record to the performance_log MySQL table.
    Called after every MongoDB or MySQL operation for research data.
    """
    try:
        log = Performance(
            operation=operation,
            db_type=db_type,
            duration=round(duration_ms, 3),
            ticket_id=ticket_id,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        # Do not fail the request path if telemetry write fails.
        try:
            from flask import current_app
            current_app.logger.warning(f'Failed to write performance log: {exc}')
        except Exception:
            pass


# ── Dual Write — Ticket ────────────────────────────────────────

def dual_write_ticket(mongo_db, ticket_data: dict, user_id: int) -> tuple[Ticket, dict]:
    """
    Write a new ticket to BOTH MongoDB and MySQL simultaneously.
    Times each operation separately for research logging.

    Returns:
        mysql_ticket  — SQLAlchemy Ticket object
        mongo_doc     — dict of what was inserted into MongoDB
    """
    ticket_id = generate_ticket_id()

    # ── 1. MongoDB insert ──
    mongo_doc = {
        'ticket_id':   ticket_id,
        'title':       ticket_data['title'],
        'description': ticket_data['description'],
        'steps':       ticket_data.get('steps', ''),
        'attachments': ticket_data.get('attachments', ''),
        'category':    ticket_data['category'],
        'priority':    ticket_data.get('priority', 'medium'),
        'environment': ticket_data.get('environment', 'Production'),
        'status':      'open',
        'user_id':     user_id,
        'assign_to':   None,
        'admin_response': None,
        'created_at':  datetime.now(timezone.utc),
        'updated_at':  datetime.now(timezone.utc),
    }
    t0 = time.perf_counter()
    mongo_db.tickets.insert_one(mongo_doc)
    mongo_ms = (time.perf_counter() - t0) * 1000
    log_performance('insert_ticket', 'mongodb', mongo_ms, ticket_id)

    # Return a clean copy without the _id ObjectId that insert_one injects
    # (ObjectId is not JSON serialisable and should not leak to callers)
    mongo_doc_clean = {k: v for k, v in mongo_doc.items() if k != '_id'}

    # ── 2. MySQL insert — timer starts before object creation for accurate measurement ──
    t0 = time.perf_counter()
    mysql_ticket = Ticket()
    mysql_ticket.ticket_id = ticket_id
    mysql_ticket.title = ticket_data['title']
    mysql_ticket.description = ticket_data['description']
    mysql_ticket.steps = ticket_data.get('steps')
    mysql_ticket.attachments = ticket_data.get('attachments')
    mysql_ticket.category = ticket_data['category']
    mysql_ticket.priority = ticket_data.get('priority', 'medium')
    mysql_ticket.environment = ticket_data.get('environment', 'Production')
    mysql_ticket.status = 'open'
    mysql_ticket.user_id = user_id
    db.session.add(mysql_ticket)
    db.session.commit()
    mysql_ms = (time.perf_counter() - t0) * 1000
    log_performance('insert_ticket', 'mysql', mysql_ms, ticket_id)

    return mysql_ticket, mongo_doc_clean


def dual_write_user(mongo_db, user) -> None:
    """
    Mirror a newly registered user into MongoDB.
    MySQL write happens in the route via db.session.add(user).
    This function handles the MongoDB side.
    """
    t0 = time.perf_counter()
    mongo_db.users.insert_one({
        'user_id':    user.id,
        'first_name': user.first_name,
        'last_name':  user.last_name,
        'email':      user.email,
        'role':       user.acc_type,
        'company':    user.company,
        'department': user.department,
        'created_at': user.created_at,
    })
    mongo_ms = (time.perf_counter() - t0) * 1000
    log_performance('insert_user', 'mongodb', mongo_ms)


def dual_update_ticket(mongo_db, ticket: Ticket, update_data: dict) -> None:
    """
    Update a ticket in BOTH databases and log timing.
    """
    tk: str = str(ticket.ticket_id)
    now = datetime.now(timezone.utc)

    # ── MongoDB update ──
    t0 = time.perf_counter()
    mongo_db.tickets.update_one(
        {'ticket_id': ticket.ticket_id},
        {'$set': {**update_data, 'updated_at': now}}
    )
    mongo_ms = (time.perf_counter() - t0) * 1000
    log_performance('update_ticket', 'mongodb', mongo_ms, tk)

    # ── MySQL update ──
    t0 = time.perf_counter()
    for key, value in update_data.items():
        if hasattr(ticket, key):
            setattr(ticket, key, value)
    ticket.updated_at = now
    db.session.commit()
    mysql_ms = (time.perf_counter() - t0) * 1000
    log_performance('update_ticket', 'mysql', mysql_ms, tk)


# ── Jinja2 Filter ─────────────────────────────────────────────

def timesince(dt) -> str:
    """
    Convert a datetime to a human-readable "X ago" string.
    Registered as a Jinja2 filter in create_app().
    """
    if dt is None:
        return '—'
    now  = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt

    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        m = seconds // 60
        return f'{m} minute{"s" if m != 1 else ""} ago'
    elif seconds < 86400:
        h = seconds // 3600
        return f'{h} hour{"s" if h != 1 else ""} ago'
    elif seconds < 604800:
        d = seconds // 86400
        return f'{d} day{"s" if d != 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')


# ── Admin-only Route Decorator ─────────────────────────────────

def admin_required(f):
    """
    Use on routes that only admins should access.
    Usage: @admin_required above the route function (after @login_required).

    Example:
        @app.route('/admin')
        @login_required
        @admin_required
        def admin_dashboard():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated