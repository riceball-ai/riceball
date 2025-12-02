"""merge multiple heads

Revision ID: abd5dbbceb93
Revises: 640b988b2062, b02dda4bcac1
Create Date: 2025-11-08 10:08:45.118349

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import fastapi_users_db_sqlalchemy.generics


# revision identifiers, used by Alembic.
revision: str = 'abd5dbbceb93'
down_revision: Union[str, Sequence[str], None] = ('640b988b2062', 'b02dda4bcac1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
