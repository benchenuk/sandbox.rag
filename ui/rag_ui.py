
# ui/rag_ui.py
import streamlit as st
from database.rag_task_db import TaskDatabase
from database.rag_db import DatabaseHelper
from rag.rag_system import initialize_rag_system
# from .rag_auth import setup_authenticator
from ui.rag_auth import authenticate_login
from ui.rag_auth import initialize_authentication_session
from ui.rag_task_management import task_management
from ui.rag_task_assist import task_assistant
from ui.rag_cache import CacheService
from langchain.memory import ConversationBufferMemory

import logging
logger = logging.getLogger(__name__)

def run_app():
    """Main function to run the Streamlit application."""

    st.set_page_config(page_title="Sandbox To Do", layout="wide")

    initialize_session_state()
    initialize_authentication_session()

    # --- Database Initialization ---
    db_helper = DatabaseHelper()
    db_helper.initialize_db()

    # --- Authentication Check ---
    if st.session_state.get("authentication_status") is None:
        authenticate_login()
        st.stop()

    if st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
        st.stop() # Stop execution if login fails
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')
        st.stop() # Stop execution until logged in


    # Get task database instance
    task_db = TaskDatabase(db_helper.conn)

    # Initialize Cache Service
    if 'cache_service' not in st.session_state:
        st.session_state.cache_service = CacheService(task_db)
        st.session_state.cache_service.reset_cache_version()

    # Main UI layout
    # st.title("✅ Sandbox To Do")

    # Initialize the RAG system if not already done
    if st.session_state.chain is None:
        st.session_state.chain, task_data, processed_files_info = initialize_rag_system(
            task_db, 
            st.session_state.memory, 
            uploaded_files=None)
        st.session_state.task_data = task_data

    # Display and manage tasks
    task_management(task_db, lambda: initialize_rag_system(
        task_db, 
        st.session_state.memory, 
        uploaded_files=None))

    # Task assistant
    task_assistant(st.session_state.chain)
    
    # Footer
    st.divider()
    st.caption("Task Recommendation System powered by Gemini and LangChain")

def initialize_session_state():
    """Initialize session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    if "chain" not in st.session_state:
        st.session_state.chain = None

    if "task_data" not in st.session_state:
        st.session_state.task_data = []

    if "question_key" not in st.session_state:
        st.session_state.question_key = 0

    if "task_title_key" not in st.session_state:
        st.session_state.task_title_key = 0
    if "task_description_key" not in st.session_state:
        st.session_state.task_description_key = 0
    if "task_tags_key" not in st.session_state:
        st.session_state.task_tags_key = 0
    
    if 'task_cache' not in st.session_state:
        st.session_state.task_cache = {
            'version': 0,
            'tasks': {},
            'tags': set(),
            'loaded': False
        }
