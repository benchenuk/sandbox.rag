import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

class TaskDatabase:
    """
    Manages task-related database operations.
    """
    def __init__(self, conn):
        """
        Initializes the TaskDatabase with a database connection.

        Args:
            conn: SQLite database connection
        """
        self.logger = logging.getLogger(__name__)
        self.conn = conn

    def initialize_tables(self):
        """
        Creates the tasks and cache_versions tables if they don't exist.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            tags TEXT,
            timestamp TEXT
        )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_versions (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO cache_versions (id, version)
            VALUES (1, 1)
        """)
        self.conn.commit()
        self.logger.info("Task tables initialized.")

    def get_cache_version(self):
        """Retrieve current cache version from DB"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT version FROM cache_versions WHERE id = 1")
        return cursor.fetchone()[0]

    def _increment_cache_version(self):
        """Atomically increment cache version"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE cache_versions 
            SET version = version + 1 
            WHERE id = 1
        """)
        self.logger.info("Incrementing cache version");
        self.conn.commit()
        return cursor.rowcount > 0

    def version_aware(original_method):
        """Decorator for version-controlled write operations"""
        def wrapper(self, *args, **kwargs):
            try:
                # Start transaction
                self.conn.execute("BEGIN")
                
                # Execute original method
                result = original_method(self, *args, **kwargs)
                
                # Only increment version if operation succeeded
                if result is not None and result is not False:
                    self._increment_cache_version()
                
                self.conn.commit()
                return result
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Versioned operation failed: {e}")
                raise
        return wrapper

    @version_aware
    def add_task(self, task):
        """
        Adds a new task to the database.

        Args:
            task (dict): A dictionary representing the task with 'title', 'description',
                         'tags' (list of strings), and 'timestamp' (ISO 8601 format) keys.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tasks (title, description, tags, timestamp)
                VALUES (?, ?, ?, ?)
            """, (task['title'], task['description'], ','.join(task['tags']), task['timestamp']))
            self.conn.commit()
            # Return the inserted row ID
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Error adding task: {e}")
            return None

    def get_all_tasks(self):
        """
        Retrieves all tasks from the database.

        Returns:
            list: A list of dictionaries, where each dictionary represents a task.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, description, tags, timestamp, id FROM tasks")
        rows = cursor.fetchall()
        logging.info(f"Retrieved {len(rows)} tasks from the database")
        return [{'title': row[0], 'description': row[1], 'tags': row[2], 'timestamp': row[3], 'id': row[4]} for row in rows]

    def get_tasks_by_tags(self, tag):
        """
        Retrieves tasks filtered by a specific tag.

        Args:
            tag (str): The tag to filter tasks by.

        Returns:
            list: A list of dictionaries, where each dictionary represents a task matching the tag.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, description, tags, timestamp, id FROM tasks WHERE tags LIKE ?", ('%' + tag + '%',))
        rows = cursor.fetchall()
        logging.info(f"Retrieved {len(rows)} tasks by tags from the database")
        return [{'title': row[0], 'description': row[1], 'tags': row[2], 'timestamp': row[3], 'id': row[4]} for row in rows]

    @version_aware
    def update_task(self, task_id, task):
        """
        Updates an existing task in the database.

        Args:
            task_id (int): The ID of the task to update
            task (dict): A dictionary containing the updated task information with
                        'title', 'description', 'tags', and 'timestamp' keys

        Returns:
            bool: True if update was successful, False if task not found
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE tasks 
                SET title = ?, 
                    description = ?, 
                    tags = ?,
                    timestamp = ?
                WHERE id = ?
            """, (
                task['title'],
                task['description'],
                ','.join(task['tags']),
                task['timestamp'],
                task_id
            ))
            self.conn.commit()
            
            if cursor.rowcount > 0:
                # Return full task object with updated values
                return {
                    'id': task_id,
                    'title': task['title'],
                    'description': task['description'],
                    'tags': task['tags'],
                    'timestamp': task['timestamp']
                }
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Error updating task: {e}")
            return False

    def truncate_tables(self):
        """
        Truncates the tasks table.
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks")
        self.conn.commit()

    def populate_from_json(self, file_path):
        """
        Populates the tasks table from a JSON file.

        Args:
            file_path (str): Path to the JSON file containing task data
        """
        self.logger.info("Populating tasks from JSON file: %s", file_path)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                for task in data:
                    self.add_task(task)
        except FileNotFoundError:
            self.logger.error(f"JSON file not found at {file_path}")
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON format in {file_path}")
