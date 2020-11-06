"""empty message

Revision ID: 323565c5286d
Revises: 4ae15110ee2a
Create Date: 2020-11-05 17:32:06.361911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '323565c5286d'
down_revision = '4ae15110ee2a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('confirmed', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('swaps', 'confirmed')
    # ### end Alembic commands ###