"""56_remove_onupdate_in_violation

Revision ID: edbfad4663bc
Revises: 96e7927862ff
Create Date: 2025-03-31 16:45:42.551647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edbfad4663bc'
down_revision: Union[str, None] = '96e7927862ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove default behavior and make it nullable
    op.alter_column('violation', 'timestamp',
                    existing_type=sa.TIMESTAMP(),
                    nullable=True,
                    server_default=None)  # Remove any default behavior

    # Optional: Ensure no triggers exist
    op.execute("""
        ALTER TABLE violation 
        ALTER COLUMN timestamp DROP DEFAULT;
    """)


def downgrade() -> None:
    # Revert to NOT NULL with default behavior
    op.alter_column('violation', 'timestamp',
                    existing_type=sa.TIMESTAMP(),
                    nullable=False,
                    server_default=sa.func.now())

    # Optional: Restore default
    op.execute("""
        ALTER TABLE violation 
        ALTER COLUMN timestamp SET DEFAULT now();
    """)
