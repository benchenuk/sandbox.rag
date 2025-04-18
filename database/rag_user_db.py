import sqlite3
import json
import logging
from pathlib import Path
from streamlit_authenticator.utilities.hasher import Hasher

class UserDatabase:
    """
    Manages user-specific database operations with a shared connection.
    """
    def __init__(self, conn):
        """
        Initializes the UserDatabase with a shared database connection.

        Args:
            conn: An active SQLite database connection
        """
        self.logger = logging.getLogger(__name__)
        self.conn = conn

    def initialize_tables(self):
        """
        Creates user-specific tables if they don't exist.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            name TEXT,
            hashed_password TEXT
        )
        """)
        self.conn.commit()
        self.logger.info("User tables initialized.")

    def add_user(self, user_data):
        """
        Adds a new user to the database, hashing the password.

        Args:
            user_data (dict): Contains 'username', 'email', 'name', 'password'.
        """
        cursor = self.conn.cursor()
        try:
            hashed_password = Hasher.hash(user_data['password'])
            cursor.execute("""
            INSERT INTO users (username, email, name, hashed_password)
            VALUES (?, ?, ?, ?)
            """, (user_data['username'], user_data['email'], user_data['name'], hashed_password))
            self.conn.commit()
            self.logger.info(f"Added user: {user_data['username']}")
            return True
        except sqlite3.IntegrityError:
            self.logger.warning(f"Username '{user_data['username']}' already exists.")
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Error adding user {user_data['username']}: {e}")
            return False

    def get_authenticator_credentials(self):
        """
        Retrieves user credentials in the format required by Streamlit Authenticator.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT username, email, name, hashed_password FROM users")
            rows = cursor.fetchall()

            credentials = {'usernames': {}}
            for row in rows:
                username, email, name, hashed_password = row
                credentials['usernames'][username] = {
                    'email': email,
                    'name': name,
                    'password': hashed_password
                }
            self.logger.info(f"Retrieved credentials for {len(rows)} users.")
            return credentials
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving user credentials: {e}")
            return {'usernames': {}}

    def truncate_tables(self):
        """
        Removes all rows from the users table.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM users")
            self.conn.commit()
            self.logger.info("Truncated users table.")
        except sqlite3.Error as e:
            self.logger.error(f"Error truncating users table: {e}")
            self.conn.rollback()

    def populate_from_json(self, file_path="users.json"):
        """
        Populates the users table from a JSON file.

        Args:
            file_path (str): The path to the JSON file relative to project root.
        """
        self.logger.info(f"Populating users from JSON file: {file_path}")
        full_path = Path(__file__).parent.parent / file_path

        if not full_path.exists():
            self.logger.error(f"User JSON file not found at {full_path}")
            return

        try:
            with open(full_path, 'r') as f:
                data = json.load(f)

            count = 0
            for item in data:
                if self.add_user(item):
                    count += 1
            self.logger.info(f"Successfully populated {count} users.")
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON format in {full_path}")
        except Exception as e:
            self.logger.error(f"Error processing user JSON file {full_path}: {e}")