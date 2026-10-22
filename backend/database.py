import os
from pathlib import Path
import mysql.connector

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError: 
    pass


class DatabaseConnectionError(Exception):
    """Raised when MySQL connection cannot be established or access is denied."""
    pass


def ensure_database_exists():
    """Ensure the target database exists in MySQL, creating it if necessary."""
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "1234")
    db_name = os.getenv("DB_NAME", "jobnex")

    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        if err.errno == 1045:
            raise DatabaseConnectionError(
                f"MySQL Access Denied for user '{user}'@'{host}'. Please verify DB_PASSWORD in .env"
            ) from err
        elif err.errno in (2003, 2002):
            raise DatabaseConnectionError(
                f"MySQL Connection Not Found at {host}:{port}. Ensure MySQL service is running."
            ) from err
        # If other error, pass through for get_connection to handle or log


def get_connection():
    """Get a connected MySQL connection, ensuring database exists with clear error messages."""
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "1234")
    db_name = os.getenv("DB_NAME", "jobnex")

    try:
        return mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )
    except mysql.connector.Error as err:
        if err.errno == 1049:  # Unknown database
            ensure_database_exists()
            return mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name
            )
        elif err.errno == 1045:
            raise DatabaseConnectionError(
                f"MySQL Access Denied for user '{user}'@'{host}'. Please verify DB_PASSWORD in backend/.env"
            ) from err
        elif err.errno in (2003, 2002):
            raise DatabaseConnectionError(
                f"MySQL Connection Not Found: cannot connect to MySQL server at {host}:{port}. Ensure MySQL is running."
            ) from err
        raise
