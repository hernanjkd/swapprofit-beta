"""empty message

Revision ID: bf9472725765
Revises: 5943b3f65984
Create Date: 2020-12-17 19:14:23.736014

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf9472725765'
down_revision = '5943b3f65984'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('confirmed_ata', sa.DateTime(), nullable=True))
    op.drop_column('swaps', 'confirmed_at')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('confirmed_at', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('swaps', 'confirmed_ata')
    # ### end Alembic commands ###
