"""initial pgvector schema"""

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE users (
            id uuid PRIMARY KEY,
            email varchar(320) UNIQUE NOT NULL,
            password_hash varchar(255) NOT NULL,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            original_filename varchar(255) NOT NULL,
            stored_filename varchar(255) UNIQUE NOT NULL,
            file_size integer NOT NULL,
            checksum varchar(64) NOT NULL,
            status varchar(20) NOT NULL,
            processing_error text,
            page_count integer NOT NULL DEFAULT 0,
            chunk_count integer NOT NULL DEFAULT 0,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now(),
            UNIQUE(user_id, checksum)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE document_chunks (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            content text NOT NULL,
            page_number integer NOT NULL,
            token_count integer NOT NULL,
            character_count integer NOT NULL,
            embedding vector(384) NOT NULL,
            embedding_model varchar(160) NOT NULL,
            chunking_configuration varchar(255) NOT NULL,
            created_at timestamptz DEFAULT now(),
            UNIQUE(document_id, chunk_index)
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )

    op.execute(
        """
        CREATE TABLE conversations (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title varchar(200) NOT NULL,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE conversation_documents (
            conversation_id uuid REFERENCES conversations(id) ON DELETE CASCADE,
            document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
            PRIMARY KEY(conversation_id, document_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE messages (
            id uuid PRIMARY KEY,
            conversation_id uuid REFERENCES conversations(id) ON DELETE CASCADE,
            role varchar(12) NOT NULL,
            content text NOT NULL,
            created_at timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE message_sources (
            id uuid PRIMARY KEY,
            message_id uuid REFERENCES messages(id) ON DELETE CASCADE,
            chunk_id uuid REFERENCES document_chunks(id) ON DELETE CASCADE,
            citation_id varchar(10) NOT NULL,
            similarity float NOT NULL,
            page_number integer NOT NULL,
            content_snapshot text NOT NULL,
            created_at timestamptz DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS
            message_sources,
            messages,
            conversation_documents,
            conversations,
            document_chunks,
            documents,
            users
        CASCADE
        """
    )