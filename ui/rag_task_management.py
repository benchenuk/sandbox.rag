# ui/rag_task_management.py
import streamlit as st
import logging
from datetime import datetime
from ui.rag_utils import reset_task_inputs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('task_database.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

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

def update_task(db, task_id, title, description, tags_string, chain_initialize_func):
    """
    Update an existing task in the database and reinitialize the RAG system.

    Args:
    db (TaskDatabase): An instance of the TaskDatabase class.
    task_id: The ID of the task to update.
    title (str): The updated title of the task.
    description (str): The updated description of the task.
    tags_string (str): A comma-separated string of updated tags.
    chain_initialize_func (callable): A function to reinitialize the RAG system.

    Returns:
    bool: True if the task was updated successfully, False otherwise.
    """
    # Create updated task data
    updated_task = {
        "title": title,
        "description": description,
        "tags": [tag.strip() for tag in tags_string.split(",") if tag.strip()],
        # Keep the original timestamp
        "timestamp": st.session_state.selected_task["timestamp"]
    }

    # Update the task in DB
    updated = db.update_task(task_id, updated_task)
    logger.info("Task with ID %s updated: %s.", task_id, updated)

    # Reinitialize the RAG system with updated data
    st.session_state.chain, _ = chain_initialize_func()
    return True

def task_management(db, chain_initialize_func):
    """
    Manage existing tasks, add new ones and display the UI.
    """
    # Initialize session state for unified panel
    if 'task_panel_mode' not in st.session_state:
        st.session_state.task_panel_mode = "collapsed"  # collapsed, add, view, edit

    if 'selected_task' not in st.session_state:
        st.session_state.selected_task = None

    # Task Management Section
    st.header("Tasks")

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
        if not filtered_tasks:
            st.info("No tasks found.")

        for i, task in enumerate(filtered_tasks):
            # Create a unique key for each checkbox
            checkbox_key = f"task_checkbox_{task['title']}_{i}"
            # Create a row with checkbox and task title
            col1, col2 = st.columns([1, 20])
            with col1:
                is_completed = st.checkbox("", key=checkbox_key)
            with col2:
                # Replace expander with clickable button
                if st.button(f"{task['title']}", key=f"task_title_{task['title']}_{i}", use_container_width=True):
                    st.session_state.selected_task = task
                    st.session_state.task_panel_mode = "edit"  # Changed from "view" to "edit"
                    st.rerun()

            # Show completion message if needed
            if is_completed:
                st.success("Task completed!")
                # Here you could add code to update the task status in the database

    # Add Task Section - Replace with button
    if st.button("+ Add Task", use_container_width=True, help="Click to create new task"):
        st.session_state.task_panel_mode = "add"
        reset_task_inputs()  # Clear any previous input
        st.rerun()

    # Unified Task Panel
    if st.session_state.task_panel_mode != "collapsed":
        with st.container(border=True):
            if st.session_state.task_panel_mode == "add":
                # Task creation form
                task_title = st.text_input(
                    "Task",
                    placeholder="Enter task title",
                    key=f"task_title_{st.session_state.task_title_key}"
                )
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

                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    if st.button("Save", use_container_width=True):
                        if not task_title:
                            st.error("Task title is required!")
                        else:
                            # Use empty string for description if not provided
                            description = task_description if task_description else ""
                            # Use "general" as default tag if none provided
                            tags = task_tags if task_tags else "general"

                            success = add_new_task(db, task_title, description, tags, chain_initialize_func)
                            if success:
                                st.success(f"Task '{task_title}' added successfully!")
                                st.session_state.task_panel_mode = "collapsed"
                                reset_task_inputs()
                                st.rerun()
                with col2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.task_panel_mode = "collapsed"
                        reset_task_inputs()
                        st.rerun()

            elif st.session_state.task_panel_mode == "edit":
                # Task editing interface (replacing the view interface)
                task = st.session_state.selected_task

                # Pre-fill form with existing task data
                task_title = st.text_input("Task Title", value=task['title'])
                task_description = st.text_area("Task Description", value=task['description'])
                task_tags = st.text_input("Tags (comma-separated)", value=task['tags'])

                # Display the creation timestamp (read-only)
                # timestamp = datetime.fromisoformat(task['timestamp'])
                # st.write(f"**Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}")

                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    if st.button("Save", use_container_width=True):
                        if not task_title:
                            st.error("Task title is required!")
                        else:
                            # Update the task
                            success = update_task(db, task['id'], task_title, task_description, task_tags, chain_initialize_func)
                            if success:
                                st.success(f"Task '{task_title}' updated successfully!")
                                st.session_state.task_panel_mode = "collapsed"
                                st.session_state.selected_task = None
                                st.rerun()
                with col2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.task_panel_mode = "collapsed"
                        st.session_state.selected_task = None
                        st.rerun()

            st.divider()