"""05_added_citation_column_in_violation

Revision ID: 5d573bfe9dae
Revises: 1bd3801f7a39
Create Date: 2024-04-08 22:40:55.068321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5d573bfe9dae'
down_revision: Union[str, None] = '1bd3801f7a39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('violation', sa.Column('citation_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('violation', 'citation_id')
