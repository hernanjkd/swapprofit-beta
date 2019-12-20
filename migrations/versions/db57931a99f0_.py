"""empty message

Revision ID: db57931a99f0
Revises: 042fe98bc515
Create Date: 2019-12-15 15:25:21.840221

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db57931a99f0'
down_revision = '042fe98bc515'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transactions', sa.Column('coins', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('dollars', sa.Integer(), nullable=True))
    op.drop_column('transactions', 'amount_in_coins')
    op.drop_column('transactions', 'amount_in_dollars')
    op.drop_column('zip_codes', 'id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('zip_codes', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.add_column('transactions', sa.Column('amount_in_dollars', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('transactions', sa.Column('amount_in_coins', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('transactions', 'dollars')
    op.drop_column('transactions', 'coins')
    # ### end Alembic commands ###