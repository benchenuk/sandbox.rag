# ui/rag_ui.py
import streamlit as st
from database.rag_task_db import TaskDatabase
from rag.rag_system import initialize_rag_system
from ui.rag_task_management import task_management
from ui.rag_task_assist import task_assistant
from ui.rag_cache import CacheService
from langchain.memory import ConversationBufferMemory

def run_app():
    """Main function to run the Streamlit application."""

    # Page configuration
    st.set_page_config(
        page_title="Task Recommendation System",
        page_icon="✅",
        layout="centered"
    )

    # Initialize session state
    initialize_session_state()

    # Initialize database
    db = TaskDatabase()
    db.initialize_db()

    # Initial cache load
    cache = CacheService(db)
    cache.load_cache();

    # Main UI layout
    st.title("✅ Sandbox To Do")

    # Initialize the RAG system if not already done
    if st.session_state.chain is None:
        st.session_state.chain, _ = initialize_rag_system(db, st.session_state.memory)
        st.session_state.task_data = _

    # Display and manage tasks
    task_management(db, lambda: initialize_rag_system(db, st.session_state.memory))

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
