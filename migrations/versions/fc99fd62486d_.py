"""empty message

Revision ID: fc99fd62486d
Revises: c1846b77f4ca
Create Date: 2019-09-20 14:31:24.745272

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc99fd62486d'
down_revision = 'c1846b77f4ca'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flights', sa.Column('end_at', sa.DateTime(), nullable=True))
    op.add_column('flights', sa.Column('start_at', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'profiles', 'users', ['id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'profiles', type_='foreignkey')
    op.drop_column('flights', 'start_at')
    op.drop_column('flights', 'end_at')
    # ### end Alembic commands ###