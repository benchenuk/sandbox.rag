# database/rag_db.py
import logging
import configparser
from pathlib import Path
import sqlite3
from .base_db import BaseDatabase
from .rag_task_db import TaskDatabase
from .rag_user_db import UserDatabase

class DatabaseHelper:
    """
    Main entry point for the application database, coordinating 
    task and user database operations with shared connection.
    """
    def __init__(self, db_name="tasks.db"):
        """
        Initializes the RAGDatabase with a specified database name.
        """
        # super().__init__(db_name)  # Initialize BaseDatabase
        self.base_db = BaseDatabase(db_name)
        # self.conn = self.base_db.connect()
        # self.task_db = None
        # self.user_db = None
        self.logger = logging.getLogger(__name__)

    def initialize_db(self):
        """
        Initializes the database components in the correct order:
        1. Establishes connection (via BaseDatabase)
        2. Initializes specialized database handlers
        3. Handles repopulation if configured
        """
        
        # Create new connection
        self.conn = self.base_db.connect()
        
        # Create specialized database handlers with shared connection
        task_db = TaskDatabase(self.conn)
        user_db = UserDatabase(self.conn)
        
        # Initialize tables
        task_db.initialize_tables()
        user_db.initialize_tables()
        
        # Check if repopulation is needed (using base method)
        if self._should_repopulate():
            self.logger.info("Repopulation flag is set. Truncating and populating data.")
            
            # Truncate all tables
            task_db.truncate_tables()
            user_db.truncate_tables()
            
            # Populate from JSON files
            task_db.populate_from_json("todo.rag.test_data.json")
            user_db.populate_from_json("users.json")
            
            self.logger.info("Database repopulation complete.")
        
        # Done database initialization
        # self.base_db.close()
        
    def _should_repopulate(self):
        """
        Checks configuration file (config.ini) to determine if the 
        database should be repopulated on initialization.
        
        Returns:
            bool: True if repopulation is configured, False otherwise.
        """
        config = configparser.ConfigParser()
        config_path = Path(__file__).parent.parent / 'config.ini' 
        
        if not config_path.exists():
            self.logger.warning(f"Configuration file not found at {config_path}. Defaulting to no repopulation.")
            return False
        
        try:
            config.read(config_path)
            # Ensure DATABASE section and REPOPULATE_DB key exist
            if 'DATABASE' in config and 'REPOPULATE_DB' in config['DATABASE']:
                 repopulate = config.getboolean('DATABASE', 'REPOPULATE_DB', fallback=False)
                 self.logger.info(f"Repopulate flag read from config: {repopulate}")
                 return repopulate
            else:
                 self.logger.warning("'DATABASE' section or 'REPOPULATE_DB' key not found in config.ini. Defaulting to no repopulation.")
                 return False
        except configparser.Error as e:
            self.logger.error(f"Error reading configuration file {config_path}: {e}")
            return False
        except ValueError as e:
             self.logger.error(f"Error parsing REPOPULATE_DB value in {config_path}: {e}. Should be True/False.")
             return False