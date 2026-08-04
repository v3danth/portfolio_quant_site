from db import connect_database, connect_server, run_statements
from mysql.connector import errorcode
from schema import ALTER_TABLE_SQL, CREATE_DATABASE_SQL, INDEX_SQL, TABLE_SQL


def create_database():
    """Create the portfolio database."""
    connection = connect_server()
    run_statements(connection, [CREATE_DATABASE_SQL])
    connection.close()


def create_tables():
    """Create portfolio tables and apply schema migrations if needed."""
    connection = connect_database()
    run_statements(connection, TABLE_SQL)
    cursor = connection.cursor()
    for statement in ALTER_TABLE_SQL:
        try:
            cursor.execute(statement)
        except Exception as exc:
            if getattr(exc, "errno", None) != errorcode.ER_DUP_FIELDNAME:
                raise
    connection.commit()
    cursor.close()
    connection.close()


def create_indexes():
    """Create portfolio indexes."""
    connection = connect_database()
    cursor = connection.cursor()
    for statement in INDEX_SQL:
        try:
            cursor.execute(statement)
        except Exception as exc:
            if getattr(exc, "errno", None) != errorcode.ER_DUP_KEYNAME:
                raise
    connection.commit()
    cursor.close()
    connection.close()


def setup_database():
    """Create database objects."""
    create_database()
    create_tables()
    create_indexes()


if __name__ == "__main__":
    setup_database()
    print("Database setup complete")