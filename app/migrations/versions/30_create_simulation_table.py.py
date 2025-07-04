"""30_create_simulation_table

Revision ID: feb340f7daed
Revises: 5ae0c1c7ee27
Create Date: 2024-08-15 15:29:48.851835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'feb340f7daed'
down_revision: Union[str, None] = '5ae0c1c7ee27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('simulation',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('fk_provider_id', sa.Integer(), nullable=False),
    sa.Column('input_data', sa.JSON(), nullable=False),
    sa.Column('api_type', sa.Enum('reservation', 'monthly_pass', 'guest_info', name='api_type'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['fk_provider_id'], ['provider.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_table('simulation')

    # Then drop the enum type to allow re-creation on future upgrades
    op.execute(f"DROP TYPE IF EXISTS api_type CASCADE")
