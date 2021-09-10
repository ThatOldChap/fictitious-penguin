"""Updated channel  approval field names

Revision ID: fcd72ac00f6d
Revises: c26a3b11787e
Create Date: 2021-09-09 20:22:56.746518

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcd72ac00f6d'
down_revision = 'c26a3b11787e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    """ op.add_column('channel', sa.Column('required_client_approval', sa.Boolean(), nullable=True))
    op.add_column('channel', sa.Column('required_supplier_approval', sa.Boolean(), nullable=True))
    op.drop_column('channel', 'supplier_approval')
    op.drop_column('channel', 'client_approval') """
    # ### end Alembic commands ###

    with op.batch_alter_table('channel') as batch_op:
        batch_op.alter_column('supplier_approval', new_column_name='required_supplier_approval')
        batch_op.alter_column('client_approval', new_column_name='required_client_approval')


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    """ op.add_column('channel', sa.Column('client_approval', sa.BOOLEAN(), nullable=True))
    op.add_column('channel', sa.Column('supplier_approval', sa.BOOLEAN(), nullable=True))
    op.drop_column('channel', 'required_supplier_approval')
    op.drop_column('channel', 'required_client_approval') """
    # ### end Alembic commands ###

    with op.batch_alter_table('channel') as batch_op:
        batch_op.alter_column('required_supplier_approval', new_column_name='supplier_approval')
        batch_op.alter_column('required_client_approval', new_column_name='client_approval')

