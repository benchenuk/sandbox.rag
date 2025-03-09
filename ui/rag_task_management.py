# ui/rag_task_management.py
import streamlit as st
from datetime import datetime
from ui.rag_utils import reset_task_inputs

def add_new_task(db, title, description, tags_string, chain_initialize_func):
    """
    Add a new task to the database and reinitialize the RAG system.

    Args:
        db (TaskDatabase): An instance of the TaskDatabase class.
        title (str): The title of the new task.
        description (str): The description of the new task.
        tags_string (str): A comma-separated string of tags for the new task.
        chain_initialize_func (callable): A function to reinitialize the RAG system.

    Returns:
        bool: True if the task was added successfully, False otherwise.
    """
    # Create a new task
    new_task = {
        "title": title,
        "description": description,
        "tags": [tag.strip() for tag in tags_string.split(",") if tag.strip()],
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to DB
    db.add_task(new_task)
    
    # Reinitialize the RAG system with updated data
    st.session_state.chain, _ = chain_initialize_func()
    return True

def task_management(db, chain_initialize_func):
    """
    Manage existing tasks, add new ones and display the UI.

    Args:
        db (TaskDatabase): An instance of the TaskDatabase class.
        chain_initialize_func (callable): A function to reinitialize the RAG system.
    """
    # Task Management Section (Now at Top)
    st.header("Your Tasks")

    # Filter options
    filter_options = ["All"]

    # Extract unique project tags from db
    all_tags = set()
    tasks = db.get_all_tasks()
    for task in tasks:
        all_tags.update(task['tags'].split(','))

    filter_options.extend(sorted(all_tags))

    selected_filter = st.selectbox("Filter by tag:", filter_options)

    # Display tasks based on filter
    filtered_tasks = []
    if selected_filter == "All":
        filtered_tasks = db.get_all_tasks()
    else:
        filtered_tasks = db.get_tasks_by_tags(selected_filter)

    # Create a container with fixed height and scrolling
    task_container = st.container(height=300, border=True)

    with task_container:
        for i, task in enumerate(filtered_tasks):
            # Create a unique key for each checkbox
            checkbox_key = f"task_checkbox_{task['title']}_{i}"
            # Create a row with checkbox and task title
            col1, col2 = st.columns([1, 20])
            with col1:
                is_completed = st.checkbox("", key=checkbox_key)
            with col2:
                # Use regular expander without the pin icon
                with st.expander(f"{task['title']}", expanded=False):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Tags:** {task['tags']}")
                    # Convert timestamp to a more readable format
                    timestamp = datetime.fromisoformat(task['timestamp'])
                    st.write(f"**Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Add option to mark task as completed
                    if is_completed:
                        st.success("Task completed!")
                        # Here you could add code to update the task status in the database

    st.divider()

    # Add Task Section (Middle)
    st.header("Add New Task")

    # Task title input (always visible) with dynamic key
    task_title = st.text_input(
        "Task Title", 
        placeholder="Enter task title",
        key=f"task_title_{st.session_state.task_title_key}"
    )

    # Expandable section for description and tags
    with st.expander("Add Description and Tags", expanded=False):
        task_description = st.text_area(
            "Task Description", 
            placeholder="Enter task description",
            key=f"task_description_{st.session_state.task_description_key}"
        )
        task_tags = st.text_input(
            "Tags (comma-separated)", 
            placeholder="e.g., Project A, development, frontend",
            key=f"task_tags_{st.session_state.task_tags_key}"
        )

    # Add task button
    if st.button("Add Task", key="add_task_button"):
        if not task_title:
            st.error("Task title is required!")
        else:
            # Use empty string for description if not provided
            description = task_description if task_description else ""
            # Use "general" as default tag if none provided
            tags = task_tags if task_tags else "general"
            
            # Add the new task
            success = add_new_task(db, task_title, description, tags, chain_initialize_func)
            if success:
                st.success(f"Task '{task_title}' added successfully!")
                # Reset all task input fields
                reset_task_inputs()
                # Clear the form fields by rerunning
                st.rerun()

    st.divider()

