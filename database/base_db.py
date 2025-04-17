# database/base_db.py
import sqlite3
import logging
from pathlib import Path

class BaseDatabase:
    """
    Base class for database interactions, handling connection 
    and configuration checks.
    """
    def __init__(self, db_name="tasks.db"):
        """
        Initializes the BaseDatabase with a specified database name.

        Args:
            db_name (str): The name of the database file.
        """
        self.logger = logging.getLogger(self.__class__.__name__) # Use specific class name
        self.db_name = db_name
        self.conn = None
        self.logger.info(f"BaseDatabase initialized for {db_name}")

    def connect(self):
        """
        Establishes the database connection.
        Returns:
            bool: True if connection successful, False otherwise.
        """
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False) # TODO check thread
                self.logger.info(f"Database connection established to {self.db_name}")
                return True
            except sqlite3.Error as e:
                self.logger.error(f"Error connecting to database {self.db_name}: {e}")
                self.conn = None # Ensure conn is None if connection failed
                return False
        return True # Already connected

    def close(self):
        """Closes the database connection if it is open."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info(f"Database connection closed for {self.db_name}")

    def get_connection(self):
        """
        Returns the active database connection, establishing it if necessary.
        Returns:
            sqlite3.Connection or None: The connection object or None if connection fails.
        """
        if self.conn is None:
            if not self.connect():
                return None # Connection failed
        return self.conn

    def __del__(self):
        """Ensures the database connection is closed when the object is destroyed."""
        self.close()