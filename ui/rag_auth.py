# ui/rag_auth.py
import streamlit as st
from streamlit_authenticator import Authenticate
from database.rag_user_db import UserDatabase
from database.base_db import BaseDatabase
import logging

# Configure logging for auth setup
logger = logging.getLogger(__name__)

def authenticate_login():
    
    initialize_authentication_session()

    try:
        # Create UserDatabase instance to fetch credentials
        conn = BaseDatabase().connect()
        user_db = UserDatabase(conn)
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
            cookie_config['expiry_days']
        )
        logger.info("Streamlit Authenticator initialized successfully.")

        # Log in
        # authenticator.login(location="main")
        name, authentication_status, username = authenticator.login(location="main")
        

        # Update session state with authentication results
        st.session_state['authentication_status'] = authentication_status
        st.session_state['username'] = username
        st.session_state['name'] = name

        logger.info(f"Authentication attempt completed. Status: {authentication_status}")

        # return authenticator

    except Exception as e:
        logger.error(f"An unexpected error occurred during authenticator setup: {e}", exc_info=True)
        st.error(f"An error occurred during authentication setup: {e}")
        return None

def initialize_authentication_session():
    st.session_state.setdefault('authentication_status', None)
    st.session_state.setdefault('username', None)
    st.session_state.setdefault('name', None) 