from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Float, Integer, DateTime, Index, ColumnElement, ForeignKey
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from typing import Optional
from extension import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name : Mapped[str]= mapped_column(String(100), nullable=False)
    last_name : Mapped[str]= mapped_column(String(100), nullable=False)
    email : Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    acc_type: Mapped[str] = mapped_column(String(100), nullable=False,default='client')
    company: Mapped[str] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False,default=True)

    tickets: Mapped[list[Ticket]] = relationship('Ticket',
                                                 back_populates='user',
                                                 lazy='select',
                                                 foreign_keys='Ticket.user_id')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:

        return check_password_hash(str(self.password_hash), password)

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'

    @property
    def initials(self) -> str:
        return f'{self.first_name[0]}, {self.last_name[0]}'.upper()

    @property
    def is_admin(self):
        return str(self.acc_type) == 'admin'

    @property
    def role(self) -> str:
        return self.acc_type

    @role.setter
    def role(self, value: Optional[str]) -> None:
        self.acc_type = value or 'client'

    def touch(self) -> None:
        self.last_seen = datetime.now(timezone.utc)
        db.session.commit()

    def __repr__(self) -> str:
        return f'<User {self.email} ({self.acc_type})>'

class Ticket(UserMixin, db.Model):
    __tablename__ = 'tickets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(80), nullable=False, default='General')
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    environment: Mapped[str] = mapped_column(String(80), nullable=False, default='Production')
    status: Mapped[str] = mapped_column(String(30), default='open', nullable=False, index=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    assign_to: Mapped[str] = mapped_column(String(80), nullable=True)
    admin_response: Mapped[str] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index('idx_priority_created', 'priority', 'created_at'),
                      Index('idx_status_updated', 'status', 'updated_at'),)

    PIRORITY_ORDER= {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
    STATUS_MAP= {
        'open': 'Open',
        'inprogress': 'In Progress',
        'resolved': 'Resolved',
        'closed': 'Closed',

    }

    user: Mapped[User] = relationship(User,
                                      back_populates='tickets',
                                      foreign_keys=[user_id])

    @property
    def status_display(self) -> str:
        status = str(self.status)
        return self.STATUS_MAP.get(status, self.status.title())

    @property
    def priority_display(self) -> str:
        return self.priority.title()

    @property
    def assigned_to(self) -> Optional[str]:
        return self.assign_to

    @assigned_to.setter
    def assigned_to(self, value: Optional[str]) -> None:
        self.assign_to = value

    def __repr__(self):
        return f'<Ticket {self.ticket_id} [{self.status}]>'

class Performance(db.Model):
    __tablename__ = 'performance_log'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    db_type: Mapped[str] = mapped_column(String(20), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    ticket_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True,
                                                 default=lambda: datetime.now(timezone.utc))

    @property
    def duration_ms(self) -> float:
        return self.duration

    def __repr__(self):
        return f'<Perflog {self.db_type} {self.operation} {self.duration}>'
