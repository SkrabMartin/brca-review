from alembic import context
from brca_review.storage.database import get_engine, database_url
from brca_review.storage.models import Base

if context.is_offline_mode():
    context.configure(url=database_url(),target_metadata=Base.metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction():context.run_migrations()
else:
    engine=get_engine()
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
    engine.dispose()
