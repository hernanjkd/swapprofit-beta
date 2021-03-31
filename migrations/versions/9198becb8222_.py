"""empty message

Revision ID: 9198becb8222
Revises: 882c5ff430d0
Create Date: 2021-03-31 12:18:12.143683

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9198becb8222'
down_revision = '882c5ff430d0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flights', sa.Column('custom', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('flights', 'custom')
    # ### end Alembic commands ###
