"""empty message

Revision ID: 4ae15110ee2a
Revises: a9e2ba5958fe
Create Date: 2020-11-01 20:56:33.121201

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ae15110ee2a'
down_revision = 'a9e2ba5958fe'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('buy_ins', sa.Column('tournament_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'buy_ins', 'tournaments', ['tournament_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'buy_ins', type_='foreignkey')
    op.drop_column('buy_ins', 'tournament_id')
    # ### end Alembic commands ###