import sqlite3
import json
import os
import streamlit as st

class TaskDatabase:
    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path
        self.conn = None

    def _get_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def _close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize_db(self):
        # Check if the database file exists, and drop the table if it does
        if os.path.exists(self.db_path):
          try:
              with self._get_connection() as conn:
                conn.execute("DROP TABLE IF EXISTS tasks")
          except Exception as e:
              st.error(f"An error occurred while dropping the table: {e}")
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    timestamp TEXT
                )
            """)
    
    def truncate_tables(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM tasks")
            try:
                conn.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
            except sqlite3.OperationalError:
                pass

    def populate_from_json(self, filepath="todo.rag.test_data.json"):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for task in data:
                    cursor.execute(
                        "INSERT INTO tasks (title, description, tags, timestamp) VALUES (?, ?, ?, ?)",
                        (task["title"], task["description"], ",".join(task["tags"]), task["timestamp"])
                    )
        except FileNotFoundError:
            st.error(f"Test data file not found: {filepath}")
        except json.JSONDecodeError:
            st.error(f"Invalid JSON format in {filepath}")
        except Exception as e:
            st.error(f"An error occurred while populating data from json: {e}")
    
    def add_task(self, task):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (title, description, tags, timestamp) VALUES (?, ?, ?, ?)",
                    (task["title"], task["description"], ",".join(task["tags"]), task["timestamp"])
                )
        except Exception as e:
            st.error(f"An error occurred while adding the task to db: {e}")

    def get_all_tasks(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks")
                columns = [col[0] for col in cursor.description]
                tasks = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return tasks
        except Exception as e:
            st.error(f"An error occurred while getting tasks from db: {e}")
            return []
        
    def get_tasks_by_tags(self, selected_tags):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE tags LIKE ?", ('%'+selected_tags+'%',))
                columns = [col[0] for col in cursor.description]
                tasks = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return tasks
        except Exception as e:
            st.error(f"An error occurred while getting tasks from db: {e}")
            return []

    def __del__(self):
        self._close_connection()
