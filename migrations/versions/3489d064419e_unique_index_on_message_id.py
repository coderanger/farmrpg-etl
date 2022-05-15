"""Unique index on message id

Revision ID: 3489d064419e
Revises: 3d5a4f21a517
Create Date: 2022-05-15 00:38:16.026366

"""
from alembic import op
import sqlalchemy as sa  # noqa


# revision identifiers, used by Alembic.
revision = "3489d064419e"
down_revision = "3d5a4f21a517"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("message", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_message_id"), ["id"], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("message", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_message_id"))

    # ### end Alembic commands ###
