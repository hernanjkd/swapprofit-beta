"""empty message

Revision ID: 8f5e5512929b
Revises: 3bf6eea9bf53
Create Date: 2019-09-15 21:19:33.738443

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8f5e5512929b'
down_revision = '3bf6eea9bf53'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('profiles_ibfk_1', 'profiles', type_='foreignkey')
    op.create_foreign_key(None, 'profiles', 'users', ['id'], ['id'])
    op.drop_column('profiles', 'user_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('profiles', sa.Column('user_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'profiles', type_='foreignkey')
    op.create_foreign_key('profiles_ibfk_1', 'profiles', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###
