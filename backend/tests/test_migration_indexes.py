from pathlib import Path


def test_corrective_migration_adds_query_indexes() -> None:
    migration = Path(__file__).parents[1] / "migrations/versions/002_add_query_indexes.py"
    content = migration.read_text()
    for index in (
        "ix_documents_user_status",
        "ix_chunks_document",
        "ix_conversations_user_updated",
        "ix_messages_conversation_created",
        "ix_message_sources_message",
    ):
        assert index in content
