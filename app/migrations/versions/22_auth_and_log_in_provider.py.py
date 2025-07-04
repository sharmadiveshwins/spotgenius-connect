"""22_auth_and_log_in_provider

Revision ID: 16cd17eacf57
Revises: 96fe2b5639be
Create Date: 2024-06-11 17:18:03.241815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '16cd17eacf57'
down_revision: Union[str, None] = '96fe2b5639be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('provider', sa.Column('logo', sa.String(), nullable=True))
    op.add_column('provider', sa.Column('auth_level', sa.String(), nullable=True))
    op.execute("CREATE TYPE authlevel AS ENUM ('GLOBAL', 'CUSTOMER', 'PARKING_LOT')")
    op.execute(''' ALTER TABLE provider ALTER COLUMN auth_level TYPE authlevel USING auth_level::authlevel ''')
    op.execute("UPDATE provider SET auth_level = 'GLOBAL' WHERE auth_level IS NULL")
    op.alter_column('provider', 'auth_level',
                    existing_type=sa.VARCHAR(),
                    type_=sa.Enum('GLOBAL', 'CUSTOMER', 'PARKING_LOT', name='authlevel'),
                    existing_nullable=True)
    op.drop_column('provider', 'description')
    op.drop_column('provider_creds', 'logo')
    op.alter_column('sessions', 'not_paid_counter',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('sub_task', 'fk_provider_creds_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sub_task', 'fk_provider_creds_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('sessions', 'not_paid_counter',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.add_column('provider_creds', sa.Column('logo', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('provider', sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.alter_column('provider', 'auth_level',
                    existing_type=sa.Enum('GLOBAL', 'CUSTOMER', 'PARKING_LOT', name='authlevel'),
                    type_=sa.VARCHAR(),
                    existing_nullable=True)
    op.drop_column('provider', 'logo')
    # ### end Alembic commands ###
