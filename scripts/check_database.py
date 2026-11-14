"""Check the optional local database without creating application tables.

Load BRCA_POSTGRES_* variables into the environment before running this script.
Credentials are passed as URL components so special characters are escaped.
"""

import os

from sqlalchemy import URL, create_engine, text


def main() -> None:
    password = os.environ["BRCA_POSTGRES_PASSWORD"]
    if password == "replace_with_a_unique_random_password":
        raise SystemExit("Replace the example password before connecting.")
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["BRCA_POSTGRES_USER"],
        password=password,
        host=os.environ.get("BRCA_POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("BRCA_POSTGRES_PORT", "5433")),
        database=os.environ["BRCA_POSTGRES_DB"],
    )
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            version, database, user = connection.execute(
                text("SELECT current_setting('server_version_num')::int, "
                     "current_database(), current_user")
            ).one()
            if not 170000 <= version < 180000:
                raise SystemExit("Expected PostgreSQL 17.")
            print(f"PostgreSQL 17 connection OK: database={database}, user={user}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
