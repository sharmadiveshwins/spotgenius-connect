"""41_add_enforced_parking_rule_type_in_connect_parkinglot

Revision ID: 09b0357069cf
Revises: 485a8c672a7e
Create Date: 2024-11-26 17:18:05.366968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '09b0357069cf'
down_revision: Union[str, None] = '485a8c672a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Define the enum type
    enforced_parking_rule_type_enum = sa.Enum(
        'paid_time', 'twenty_four_hour_free_window', 'do_nothing',
        name='enforcedparkingruletype'
    )
    
    # Create the enum type in the database
    enforced_parking_rule_type_enum.create(op.get_bind())
    
    # Add the column with the enum type
    op.add_column(
        'connect_parkinglot',
        sa.Column(
            'enforced_parking_rule_type',
            enforced_parking_rule_type_enum,
            server_default='do_nothing',
            nullable=True
        )
    )

def downgrade() -> None:
    # Drop the column
    op.drop_column('connect_parkinglot', 'enforced_parking_rule_type')
    
    # Drop the enum type
    enforced_parking_rule_type_enum = sa.Enum(
        'paid_time', 'twenty_four_hour_free_window', 'do_nothing',
        name='enforcedparkingruletype'
    )
    enforced_parking_rule_type_enum.drop(op.get_bind())

