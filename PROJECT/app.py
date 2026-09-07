import os
import time
from datetime import datetime, timezone
from flask import Flask, render_template
from typing import Optional

from utils import timesince, dual_write_user, log_performance
from extension import db, login_manager, csrf, init_mongo
from models import User, Ticket
from config import ProductionConfig, DevelopmentConfig

from routes.main import main_bp
from routes.auth import auth_bp
from routes.client import client_bp
from routes.admin import admin_bp, public_stats
"""
config.py — ResolvIQ Flask Configuration
"""

def _get_config(env: Optional[str]):
    """Return a guaranteed config class — never None."""
    if env == 'production':
        return ProductionConfig
    return DevelopmentConfig

def _wait_for_mysql(app: Flask, retries: int = 20, delay: float = 3.0) -> None:
    """
30    Block until MySQL accepts connections or raise after max retries.
31    Called inside app_context so SQLAlchemy URI is already configured.
    Uses a raw pymysql connection so it never touches the ORM session pool.
    """
    import pymysql
    from urllib.parse import urlparse

    uri    = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    parsed = urlparse(uri.replace('mysql+pymysql://', 'mysql://'))
    host   = parsed.hostname or 'mysql'
    port   = parsed.port     or 3306
    user   = parsed.username or 'root'
    pwd    = parsed.password or ''
    dbname = (parsed.path or '/resolviq').lstrip('/')

    for attempt in range(1, retries + 1):
        try:
            conn = pymysql.connect(
                host=host, port=port, user=user,
                password=pwd, database=dbname,
                connect_timeout=5,
            )
            conn.close()
            app.logger.info(f'MySQL ready after {attempt} attempt(s).')
            return
        except Exception as exc:
            app.logger.warning(
                f'MySQL not ready (attempt {attempt}/{retries}): {exc}  — '
                f'retrying in {delay}s…'
            )
            time.sleep(delay)

    raise RuntimeError(
        f'MySQL did not become available after {retries} attempts. '
        'Check that the mysql container is healthy and the MYSQL_URI is correct.'
    )

def create_app(env: Optional[str] = None) -> Flask:

    app: Flask = Flask(__name__,
                static_folder='static',
                template_folder='templates'
                )

    env = env or os.environ.get('FLASK_ENV', 'development')

    cfg_env: str = env if isinstance(env, str) else os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(_get_config(cfg_env))

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = '7079524c97b71208ff1deb54addab8192896080ae7cb708192d686b4a92708ba'

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)


    @login_manager.user_loader
    def load_user(user_id: int):
        return db.session.get(User, int(user_id))

    app.jinja_env.filters['timesince'] = timesince

    @app.context_processor
    def inject_globals() -> dict:
        """Makes these variables available in every template automatically."""
        return {'now': datetime.now(timezone.utc) }


    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)

    app.add_url_rule('/api/stats', 'api_stats', public_stats)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error/500.html'), 500

    with app.app_context():
        try:
            init_mongo(app)
            app.logger.info('✅ MongoDB connected')
        except Exception as e:
            app.logger.warning(f'⚠️  MongoDB not available: {e}')
            app.mongo_db = None

        _wait_for_mysql(app)
        db.create_all()
        _seed_demo_data(app)
    return app

def _seed_demo_data(app: Flask):
    """Seed demo admin, client and tickets on first run only."""
    if User.query.count() > 0:
        return
        # ── Admin ────────────────────────────────────────────────────
    admin = User()
    admin.first_name = 'Admin'

    admin.last_name = 'User'
    admin.email = 'admin@resolviq.com'
    admin.acc_type = 'admin'
    admin.company = 'ResolvIQ Inc.'
    admin.department = 'Operations'
    admin.set_password('admin123')
    db.session.add(admin)

      # ── Client ───────────────────────────────────────────────────

    client = User()

    client.first_name = 'John'
    client.last_name = 'Smith'

    client.email = 'client@resolviq.com'
    client.role = 'client'

    client.company = 'TechNova'
    client.department = 'Engineering'

    client.set_password('client123')

    db.session.add(client)

    db.session.commit()

    if app.mongo_db:
        dual_write_user(app.mongo_db, admin)

    dual_write_user(app.mongo_db, client)

    demo_tickets = [
        {
            'tid': 'TK-1000',
            'title': 'Login page returning 500 Internal Server Error',
            'description': 'When attempting to log in with valid credentials the server '
            'returns a 500 error consistently across all browsers.',
            'category': 'Authentication',
            'priority': 'critical',
            'environment': 'Production',
            'status': 'inprogress',
            'admin_response': 'Identified a misconfigured environment variable. Fix in progress.',
            'assigned_to': 'Dev Team',
        },
        {
            'tid': 'TK-1001',
            'title': 'Dashboard charts not rendering on mobile devices',
            'description': 'Chart widgets fail on screens under 768px. Desktop is fine.',
            'category': 'UI/UX',
            'priority': 'high',
            'environment': 'Production',
            'status': 'open',
            'admin_response': None,
            'assigned_to': None,
        },
        {
            'tid': 'TK-1002',
            'title': 'Unable to export reports as PDF',
            'description': 'Clicking Export PDF does nothing — no error, no download.',
            'category': 'Data / Reports',
            'priority': 'medium',
            'environment': 'Staging',
            'status': 'resolved',
            'admin_response': 'Fixed missing PDF renderer dependency. Please clear cache.',
            'assigned_to': 'Dev Team',
        },
        ]
    for data in demo_tickets:
        tid: str = data['tid']

        t0 = time.perf_counter()
        ticket = Ticket()
        ticket.ticket_id = tid
        ticket.title = data['title']
        ticket.description = data['description']
        ticket.category = data['category']
        ticket.priority = data['priority']
        ticket.environment = data['environment']
        ticket.status = data['status']
        ticket.user_id = client.id
        ticket.admin_response = data['admin_response']
        ticket.assigned_to = data['assigned_to']
        db.session.add(ticket)
        db.session.commit()
        log_performance('insert_ticket', 'mysql', (time.perf_counter() - t0) * 1000, tid)

        if app.mongo_db:
            t0 = time.perf_counter()
            app.mongo_db.tickets.insert_one({
                'ticket_id': tid,
                'title': data['title'],
                'description': data['description'],
                'category': data['category'],
                'priority': data['priority'],
                'environment': data['environment'],
                'status': data['status'],
                'user_id': client.id,
                'admin_response': data['admin_response'],
                'assigned_to': data['assigned_to'],
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
            })
    log_performance('insert_ticket', 'mongodb', (time.perf_counter() - t0) * 1000, tid)
    app.logger.info('NexusDesk ready')


app: Flask = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


