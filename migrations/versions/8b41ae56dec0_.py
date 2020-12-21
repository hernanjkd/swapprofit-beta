"""empty message

Revision ID: 8b41ae56dec0
Revises: bf9472725765
Create Date: 2020-12-17 19:15:03.836850

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8b41ae56dec0'
down_revision = 'bf9472725765'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('confirmed_at', sa.DateTime(), nullable=True))
    op.drop_column('swaps', 'confirmed_ata')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('confirmed_ata', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_column('swaps', 'confirmed_at')
    # ### end Alembic commands ###
