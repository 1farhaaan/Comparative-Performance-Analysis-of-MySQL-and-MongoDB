from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError, AnyOf
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    acc_type = HiddenField(default='client')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(1,100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1,100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    company = StringField('Company', validators=[Optional(), Length(max=100)])
    department = SelectField('Department', choices=[
        ('', 'Select department'),
        ('Engineering', 'Engineering'),
        ('Product', 'Product'),
        ('Design', 'Design'),
        ('Sales', 'Sales'),
        ('Finance', 'Finance'),
        ('Operations', 'Operations'),
        ('HR', 'HR'),
        ('Other', 'Other'),
    ], validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    terms = BooleanField('I agree to the Terms', validators=[DataRequired(
            message = 'You must accept the Terms of Service.'
    )])
    submit = SubmitField('Create Account')


    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered')

CATEGORIES = [
    ('', 'Select category'),
    ('Authentication', 'Authentication'),
    ('Performance', 'Performance'),
    ('UI/UX', 'UI/UX'),
    ('Data / Reports', 'Data / Reports'),
    ('API Integration', 'API Integration'),
    ('Security', 'Security'),
    ('Billing', 'Billing'),
    ('Other', 'Other'),
]

ENVIRONMENTS = [
    ('Production',  'Production'),
    ('Staging',     'Staging'),
    ('Development', 'Development'),
]

PRIORITIES = [
    ('low',      'Low'),
    ('medium',   'Medium'),
    ('high',     'High'),
    ('critical', 'Critical'),
]

class TicketForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1,100)])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired()])
    environment = SelectField('Environment', choices=ENVIRONMENTS)
    priority = HiddenField('Priority', default='medium')
    description = TextAreaField('Description', validators=[DataRequired()])
    steps = TextAreaField('Steps to reproduces', validators=[Optional()])
    attachments = StringField('Attach URL', validators=[Optional(), Length(max=500)])

STATUSES = [
    ('open', 'Open'),
    ('inprogress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]

Teams = [
    ('Dev Team', 'Dev Team'),
    ('Security Team', 'Security Team'),
    ('Design Team', 'Design Team'),
    ('DevOps', 'DevOps'),
    ('Support Tier 1', 'Tier 1'),
    ('Support Tier 2', 'Tier 2'),
]

class UpdateTicket(FlaskForm):
    ticket_id = HiddenField()
    status = SelectField('Status', choices=STATUSES)
    assigned_to = SelectField('Assigned To', choices=Teams, validators=[Optional()])
    admin_response = TextAreaField('Admin Response', validators=[Optional()])
    internal_notes = TextAreaField('Internal Notes', validators=[Optional()])
    submit = SubmitField('Save Update')
