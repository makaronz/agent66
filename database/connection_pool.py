
import sqlite3
from queue import Queue, Empty, Full
import threading
import os

class SQLiteConnectionPool:
    def __init__(self, database_path, max_connections=10):
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool = Queue(max_connections)
        self._local = threading.local()

        # Ensure the database directory exists
        db_dir = os.path.dirname(database_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        for _ in range(max_connections):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
            except sqlite3.Error as e:
                print(f"Error creating SQLite connection: {e}")
                # Handle connection creation failure if necessary

    def _create_connection(self):
        """Creates a new SQLite connection."""
        return sqlite3.connect(self.database_path, check_same_thread=False)

    def get_conn(self):
        """Gets a connection from the pool."""
        if hasattr(self._local, 'conn'):
            return self._local.conn

        try:
            self._local.conn = self._pool.get(block=True, timeout=5)
            return self._local.conn
        except Empty:
            raise Exception("Timeout waiting for a database connection.")

    def release_conn(self, conn):
        """Releases a connection back to the pool."""
        if hasattr(self._local, 'conn'):
            try:
                self._pool.put(self._local.conn, block=False)
                del self._local.conn
            except Full:
                # If the pool is full, just close the connection
                self._local.conn.close()
                del self._local.conn

    def close_all(self):
        """Closes all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break

# Example of a global pool instance
# This would be initialized in your application's startup sequence
# with the path from the config.
db_pool = None

def initialize_pool(db_path, max_connections=10):
    """Initializes the global database pool."""
    global db_pool
    if db_pool is None:
        db_pool = SQLiteConnectionPool(database_path=db_path, max_connections=max_connections)
    return db_pool

def get_db_connection():
    """Provides a simple way to get a connection from the global pool."""
    if db_pool is None:
        raise Exception("Database pool is not initialized. Call initialize_pool() first.")
    return db_pool.get_conn()

def release_db_connection(conn):
    """Releases a connection back to the global pool."""
    if db_pool:
        db_pool.release_conn(conn)

def close_all_connections():
    """Closes all connections in the global pool."""
    if db_pool:
        db_pool.close_all()

