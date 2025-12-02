"""add_interface_type_to_model_provider

Revision ID: fda5b75141d5
Revises: 9331e7620e25
Create Date: 2025-09-15 03:20:59.716225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import fastapi_users_db_sqlalchemy.generics


# revision identifiers, used by Alembic.
revision: str = 'fda5b75141d5'
down_revision: Union[str, Sequence[str], None] = '9331e7620e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add interface_type column to model_providers table as string type
    op.add_column('model_providers', sa.Column(
        'interface_type', 
        sa.String(50),
        nullable=False,
        server_default='CUSTOM'
    ))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove interface_type column from model_providers table
    op.drop_column('model_providers', 'interface_type')
