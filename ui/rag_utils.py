# ui/rag_utils.py
import streamlit as st

# Function to reset the question input field
def reset_question_input():
    """Resets the question input field by incrementing its key."""
    # Increment the key to force a reset of the input widget
    st.session_state.question_key += 1

# Function to reset task input fields
def reset_task_inputs():
    """Resets the task input fields by incrementing their keys."""
    # Increment the keys to force a reset of the input widgets
    st.session_state.task_title_key += 1
    st.session_state.task_description_key += 1
    st.session_state.task_tags_key += 1
