from database import get_connection

connection = None

try:
    connection = get_connection()

    if connection.is_connected():
        print("MySQL connection successful!")

except Exception as error:
    print("MySQL connection failed:", error)

finally:
    if connection is not None and connection.is_connected():
        connection.close()