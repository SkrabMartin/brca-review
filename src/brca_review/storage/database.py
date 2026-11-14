"""Environment-only PostgreSQL configuration; never create tables implicitly."""
import os
from sqlalchemy import URL, create_engine


def database_url():
    if os.environ.get('BRCA_DATABASE_URL'):
        value = os.environ['BRCA_DATABASE_URL']
        if not value.startswith('postgresql+psycopg://'):
            raise ValueError('BRCA_DATABASE_URL must use postgresql+psycopg://')
        return value
    return URL.create('postgresql+psycopg', username=os.environ['BRCA_POSTGRES_USER'],
        password=os.environ['BRCA_POSTGRES_PASSWORD'], database=os.environ['BRCA_POSTGRES_DB'],
        host=os.environ.get('BRCA_POSTGRES_HOST','127.0.0.1'), port=int(os.environ.get('BRCA_POSTGRES_PORT','5433')))


def get_engine():
    return create_engine(database_url(), pool_pre_ping=True, hide_parameters=True,
                         connect_args={'connect_timeout':5})
