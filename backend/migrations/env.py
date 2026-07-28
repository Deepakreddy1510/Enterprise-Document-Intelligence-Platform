from alembic import context
from app.core.config import get_settings

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("+asyncpg", ""))


def run_migrations_online():
    from sqlalchemy import create_engine

    engine = create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
