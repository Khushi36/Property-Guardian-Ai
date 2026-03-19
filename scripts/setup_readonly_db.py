import psycopg2
from sqlalchemy import make_url

from app.core.config import settings


def setup_readonly_user():
    url = make_url(settings.DATABASE_URL)

    # Connect as superuser (assuming current credentials have permission)
    conn = psycopg2.connect(
        dbname=url.database,
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Create user if not exists
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'read_only_user') THEN CREATE USER read_only_user WITH PASSWORD 'readonly_password'; END IF; END $$;"
        )

        # Grant permissions
        cur.execute("GRANT CONNECT ON DATABASE property_db TO read_only_user;")
        cur.execute("GRANT USAGE ON SCHEMA public TO read_only_user;")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only_user;")
        cur.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO read_only_user;"
        )

        print("Successfully created/updated read_only_user with SELECT permissions.")
    except Exception as e:
        print(f"Error setting up readout user: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    setup_readonly_user()
