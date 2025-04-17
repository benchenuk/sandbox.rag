# database/rag_db.py
import logging
import configparser
from pathlib import Path
import sqlite3
from .base_db import BaseDatabase
from .rag_task_db import TaskDatabase
from .rag_user_db import UserDatabase

class RAGDatabase(BaseDatabase):
    """
    Main entry point for the application database, coordinating 
    task and user database operations with shared connection.
    """
    def __init__(self, db_name="tasks.db"):
        """
        Initializes the RAGDatabase with a specified database name.
        """
        super().__init__(db_name)  # Initialize BaseDatabase
        self.task_db = None
        self.user_db = None
        self.logger = logging.getLogger(__name__)

    def initialize_db(self):
        """
        Initializes the database components in the correct order:
        1. Establishes connection (via BaseDatabase)
        2. Initializes specialized database handlers
        3. Handles repopulation if configured
        """
        # Connect using base class method
        if not self.connect():
            self.logger.error("Failed to establish database connection")
            raise ConnectionError(f"Could not connect to database: {self.db_name}")
        
        # Create specialized database handlers with shared connection
        self.task_db = TaskDatabase(self.conn)
        self.user_db = UserDatabase(self.conn)
        
        # Initialize tables
        self.task_db.initialize_tables()
        self.user_db.initialize_tables()
        
        # Check if repopulation is needed (using base method)
        if self._should_repopulate():
            self.logger.info("Repopulation flag is set. Truncating and populating data.")
            
            # Truncate all tables
            self.task_db.truncate_tables()
            self.user_db.truncate_tables()
            
            # Populate from JSON files
            self.task_db.populate_from_json("todo.rag.test_data.json")
            self.user_db.populate_from_json("users.json")
            
            self.logger.info("Database repopulation complete.")
        
    def get_task_db(self):
        """Returns the TaskDatabase instance."""
        return self.task_db
        
    def get_user_db(self):
        """Returns the UserDatabase instance."""
        return self.user_db
        
    def get_authenticator_credentials(self):
        """
        Convenience method to get credentials for Streamlit Authenticator.
        """
        if self.user_db:
            return self.user_db.get_authenticator_credentials()
        return {'usernames': {}}  # Empty credentials if user_db not initialized
    
    def _should_repopulate(self):
        """
        Checks configuration file (config.ini) to determine if the 
        database should be repopulated on initialization.
        
        Returns:
            bool: True if repopulation is configured, False otherwise.
        """
        config = configparser.ConfigParser()
        # Assume config.ini is in the parent directory of the 'database' directory
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