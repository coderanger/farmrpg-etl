"""Initial table create for chat messages

Revision ID: 076abff30c0c
Revises: 
Create Date: 2022-05-14 22:22:02.910899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "076abff30c0c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "message",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("json_data", sa.JSON(), nullable=False),
        sa.Column("room", sa.Text(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("flags", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_ts", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_message_deleted"), "message", ["deleted"], unique=False
    )
    op.create_index(
        op.f("ix_message_deleted_ts"), "message", ["deleted_ts"], unique=False
    )
    op.create_index(
        op.f("ix_message_flags"), "message", ["flags"], unique=False
    )
    op.create_index(op.f("ix_message_room"), "message", ["room"], unique=False)
    op.create_index(op.f("ix_message_ts"), "message", ["ts"], unique=False)
    op.create_index(
        op.f("ix_message_username"), "message", ["username"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_message_username"), table_name="message")
    op.drop_index(op.f("ix_message_ts"), table_name="message")
    op.drop_index(op.f("ix_message_room"), table_name="message")
    op.drop_index(op.f("ix_message_flags"), table_name="message")
    op.drop_index(op.f("ix_message_deleted_ts"), table_name="message")
    op.drop_index(op.f("ix_message_deleted"), table_name="message")
    op.drop_table("message")
    # ### end Alembic commands ###
