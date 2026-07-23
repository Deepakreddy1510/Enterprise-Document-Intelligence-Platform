"""add indexes matching the ORM ownership and lookup paths

Revision ID: 002_add_query_indexes
Revises: 001_initial
"""

from alembic import op

revision = "002_add_query_indexes"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_documents_user_status", "documents", ["user_id", "status"])
    op.create_index("ix_chunks_document", "document_chunks", ["document_id"])
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )
    op.create_index("ix_message_sources_message", "message_sources", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_message_sources_message", table_name="message_sources")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
    op.drop_index("ix_chunks_document", table_name="document_chunks")
    op.drop_index("ix_documents_user_status", table_name="documents")
