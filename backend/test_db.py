# test_db.py
import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from database import get_connection  # type: ignore
except ImportError:
    try:
        from backend.database import get_connection  # type: ignore
    except ImportError:
        def get_connection():
            raise RuntimeError("Database module not available")


def test_connection():
    connection = None
    try:
        connection = get_connection()
        if connection and connection.is_connected():
            print("MySQL connection successful!")
    except Exception as error:
        print("MySQL connection failed:", error)
    finally:
        if connection is not None and getattr(connection, "is_connected", lambda: False)():
            connection.close()


if __name__ == "__main__":
    test_connection()