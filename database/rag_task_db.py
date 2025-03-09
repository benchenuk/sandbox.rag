# database/rag_task_database.py
import sqlite3
import json
from datetime import datetime

class TaskDatabase:
    """
    Manages the task database, including connection, schema, and operations.
    """
    def __init__(self, db_name="tasks.db"):
        """
        Initializes the TaskDatabase with a specified database name.

        Args:
            db_name (str): The name of the database file (default: "tasks.db").
        """
        self.db_name = db_name
        self.conn = None

    def initialize_db(self):
        """
        Initializes the database and creates the 'tasks' table if it doesn't exist.
        """
        self.conn = sqlite3.connect(self.db_name)
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
        self.conn.commit()

    def add_task(self, task):
        """
        Adds a new task to the database.

        Args:
            task (dict): A dictionary representing the task with 'title', 'description',
                         'tags' (list of strings), and 'timestamp' (ISO 8601 format) keys.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, description, tags, timestamp)
            VALUES (?, ?, ?, ?)
        """, (task['title'], task['description'], ','.join(task['tags']), task['timestamp']))
        self.conn.commit()

    def get_all_tasks(self):
        """
        Retrieves all tasks from the database.

        Returns:
            list: A list of dictionaries, where each dictionary represents a task.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, description, tags, timestamp FROM tasks")
        rows = cursor.fetchall()
        return [{'title': row[0], 'description': row[1], 'tags': row[2], 'timestamp': row[3]} for row in rows]

    def get_tasks_by_tags(self, tag):
        """
        Retrieves tasks filtered by a specific tag.

        Args:
            tag (str): The tag to filter tasks by.

        Returns:
            list: A list of dictionaries, where each dictionary represents a task matching the tag.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, description, tags, timestamp FROM tasks WHERE tags LIKE ?", ('%' + tag + '%',))
        rows = cursor.fetchall()
        return [{'title': row[0], 'description': row[1], 'tags': row[2], 'timestamp': row[3]} for row in rows]

    def truncate_tables(self):
        """
        Truncates the 'tasks' table (removes all rows).
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks")
        self.conn.commit()

    def populate_from_json(self, file_path="todo.rag.test_data.json"):
        """
        Populates the 'tasks' table from a JSON file.

        Args:
            file_path (str): The path to the JSON file (default: "todo.rag.test_data.json").
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Iterate through the top-level array directly
                for task in data:
                    self.add_task(task)
        except FileNotFoundError:
            print(f"Error: JSON file not found at {file_path}")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {file_path}")

        
    def __del__(self):
        """
        Close db connection
        """
        if self.conn:
            self.conn.close()
