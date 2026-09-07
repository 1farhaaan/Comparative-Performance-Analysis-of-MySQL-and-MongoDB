from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import Ticket
from forms import TicketForm
from utils import dual_write_ticket

client_bp = Blueprint('client', __name__, url_prefix='/client')

@client_bp.route('/')
@client_bp.route('/tickets')
@login_required
def tickets():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    user_tickets = (
        Ticket.query.filter_by(
            user_id=current_user.id).
        order_by(Ticket.created_at.desc()).all()
    )

    total = len(user_tickets)
    open_tickets = sum(1 for i in user_tickets if i.status in ('open', 'inprogress'))
    resolved_tickets = sum(1 for i in user_tickets if i.status in ('resolved'))

    resolved = [i for i in user_tickets if i.status =='resolved' and i.updated_at]
    if resolved:
        diffs = [(i.updated_at - i.created_at).total_seconds() / 3600 for i in resolved]
        avg_response = f'{sum(diffs) / len(diffs):.1f}h'
    else:
        avg_response = '-'

    notif_count = 0
    return render_template('raise_ticket.html', tickets=user_tickets, total_tickets=total,
                           open_tickets=open_tickets,
                           resolved_tickets=resolved_tickets,
                           avg_response=avg_response,
                           open_count=open_tickets,
                           notif_count=notif_count,
                           active_nav='tickets',
                           ticket_form=TicketForm()
                           )

@client_bp.route('/ticket/create', methods=['GET','POST'])
@login_required
def create_ticket():
    if current_user.is_admin:
        flash('Admin cannot raise tickets.', 'error')
        return redirect(url_for('admin.dashboard'))

    form = TicketForm()
    if form.validate_on_submit():
        raw_priority = (form.priority.data or 'medium').strip().lower()
        priority = raw_priority if raw_priority in ('low', 'medium', 'high', 'critical') else 'medium'

        ticket_data = {
            'title': form.title.data.strip(),
            'description': form.description.data.strip(),
            'steps': form.steps.data.strip() if form.steps.data else '',
            'attachments': form.attachments.data.strip() if form.attachments.data else '',
            'category': form.category.data,
            'priority': priority,
            'environment': form.environment.data
        }

        mongodb = current_app.mongo_db
        mysql_ticket, _ = dual_write_ticket(mongodb, ticket_data, current_user.id)

        flash(f'Ticket {mysql_ticket.ticket_id} raised successfully!', 'success')
        return redirect(url_for('client.tickets'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{error}', error)
    return redirect(url_for('client.tickets'))

@client_bp.route('/notification')
@login_required
def client_notification():
    flash('Notification coming soon.', 'info')
    return redirect(url_for('client.tickets'))

@client_bp.route('/profile')
@login_required
def client_profile():
    flash('Profile page coming soon.', 'info')
    return redirect(url_for('client.tickets'))

@client_bp.route('/settings')
@login_required
def client_settings():
    flash('Settings page coming soon.', 'info')
    return redirect(url_for('client.tickets'))