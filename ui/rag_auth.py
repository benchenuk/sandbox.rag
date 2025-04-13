import streamlit as st
from streamlit_authenticator import Authenticate
from database.rag_user_db import UserDatabase
import logging

# Configure logging for auth setup
logger = logging.getLogger(__name__)

def setup_authenticator(db_connection):
    """
    Initializes and configures the Streamlit Authenticator component.

    Args:
        db_connection: An active sqlite3 connection object.

    Returns:
        Authenticate: An initialized Authenticate object or None if setup fails.
    """
    if db_connection is None:
        logger.error("Database connection is None, cannot set up authenticator.")
        st.error("Fatal Error: Database connection not available for authentication.")
        return None

    try:
        # Create UserDatabase instance to fetch credentials
        user_db = UserDatabase(db_connection)
        credentials = user_db.get_authenticator_credentials()

        # Check if credentials could be fetched
        if not credentials or 'usernames' not in credentials:
             logger.error("Failed to fetch credentials from the database.")
             st.error("Authentication setup failed: Could not load user credentials.")
             return None

        # Basic cookie configuration (Consider moving to config.ini or env vars for secrets)
        # IMPORTANT: Change the 'key' to a strong, unique secret in a real deployment!
        cookie_config = {
            'name': 'rag_todo_auth_cookie',
            'key': 'a_secure_secret_key_12345', # CHANGE THIS!
            'expiry_days': 7
        }

        authenticator = Authenticate(
            credentials,
            cookie_config['name'],
            cookie_config['key'],
            cookie_config['expiry_days'],
            # Pre-authorized emails (optional, could also be fetched from DB)
            {'emails': []}
        )
        logger.info("Streamlit Authenticator initialized successfully.")
        return authenticator

    except Exception as e:
        logger.error(f"An unexpected error occurred during authenticator setup: {e}", exc_info=True)
        st.error(f"An error occurred during authentication setup: {e}")
        return None