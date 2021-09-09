"""Added approval fields to channel

Revision ID: dc7f456feed9
Revises: 6b9e3134e630
Create Date: 2021-09-08 20:40:58.111684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc7f456feed9'
down_revision = '6b9e3134e630'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('channel', sa.Column('client_approval', sa.Boolean(), nullable=True))
    op.add_column('channel', sa.Column('supplier_approval', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('channel', 'supplier_approval')
    op.drop_column('channel', 'client_approval')
    # ### end Alembic commands ###
