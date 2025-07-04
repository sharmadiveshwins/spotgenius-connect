"""02_all_tables

Revision ID: 1fee494fd979
Revises: 431db80110fc
Create Date: 2024-03-26 14:33:04.555455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1fee494fd979'
down_revision: Union[str, None] = '431db80110fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('session_audit',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('entry_event', sa.JSON(), nullable=False),
    sa.Column('exit_event', sa.JSON(), nullable=True),
    sa.Column('lpr_number', sa.String(), nullable=False),
    sa.Column('spot_id', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('parking_lot_id', sa.Integer(), nullable=False),
    sa.Column('session_start_time', sa.TIMESTAMP(), nullable=False),
    sa.Column('session_end_time', sa.TIMESTAMP(), nullable=True),
    sa.Column('session_total_time', sa.Integer(), nullable=True),
    sa.Column('is_waiting_for_payment', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('session_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('fk_session_audit', sa.Integer(), nullable=False),
    sa.Column('action_type', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('provider', sa.Integer(), nullable=True),
    sa.Column('meta_info', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['fk_session_audit'], ['session_audit.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('audit_request_response', sa.Column('api_request', sa.Text(), nullable=False))
    op.add_column('audit_request_response', sa.Column('api_response', sa.Text(), nullable=True))
    op.add_column('audit_request_response', sa.Column('api_response_code', sa.Text(), nullable=True))
    op.add_column('audit_request_response', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('audit_request_response', sa.Column('fk_provider_connect', sa.Integer(), nullable=False))
    op.add_column('audit_request_response', sa.Column('fk_task', sa.Integer(), nullable=False))
    op.add_column('audit_request_response', sa.Column('fk_violation', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'audit_request_response', 'violation', ['fk_violation'], ['id'])
    op.create_foreign_key(None, 'audit_request_response', 'provider_connect', ['fk_provider_connect'], ['id'])
    op.create_foreign_key(None, 'audit_request_response', 'task', ['fk_task'], ['id'])
    op.drop_column('audit_request_response', 'request_schema')
    op.drop_column('audit_request_response', 'response_schema')
    op.add_column('provider', sa.Column('logo', sa.String(), nullable=True))
    op.add_column('push_payment', sa.Column('external_reference_id', sa.Integer(), nullable=True))
    op.add_column('sub_task', sa.Column('status', sa.String(), nullable=True))
    op.add_column('task', sa.Column('status', sa.String(), nullable=False))
    op.add_column('task', sa.Column('next_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('task', sa.Column('sgadmin_alerts_ids', sa.ARRAY(sa.Integer()), nullable=True))
    op.add_column('task', sa.Column('sg_event_response', sa.JSON(), nullable=True))
    op.add_column('task', sa.Column('session_id', sa.Integer(), nullable=True))
    op.drop_column('task', 'event_time')
    op.drop_column('task', 'event_status')
    op.drop_column('task', 'timestamp')
    op.add_column('violation', sa.Column('session', sa.String(), nullable=True))
    op.add_column('violation', sa.Column('session_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('violation', 'session_id')
    op.drop_column('violation', 'session')
    op.add_column('task', sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('task', sa.Column('event_status', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('task', sa.Column('event_time', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_column('task', 'session_id')
    op.drop_column('task', 'sg_event_response')
    op.drop_column('task', 'sgadmin_alerts_ids')
    op.drop_column('task', 'next_at')
    op.drop_column('task', 'status')
    op.drop_column('sub_task', 'status')
    op.drop_column('push_payment', 'external_reference_id')
    op.drop_column('provider', 'logo')
    op.add_column('audit_request_response', sa.Column('response_schema', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('audit_request_response', sa.Column('request_schema', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'audit_request_response', type_='foreignkey')
    op.drop_constraint(None, 'audit_request_response', type_='foreignkey')
    op.drop_constraint(None, 'audit_request_response', type_='foreignkey')
    op.drop_column('audit_request_response', 'fk_violation')
    op.drop_column('audit_request_response', 'fk_task')
    op.drop_column('audit_request_response', 'fk_provider_connect')
    op.drop_column('audit_request_response', 'description')
    op.drop_column('audit_request_response', 'api_response_code')
    op.drop_column('audit_request_response', 'api_response')
    op.drop_column('audit_request_response', 'api_request')
    op.drop_table('session_log')
    op.drop_table('session_audit')
    # ### end Alembic commands ###
