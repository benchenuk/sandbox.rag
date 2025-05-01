import streamlit as st
from pathlib import Path
import os
import datetime
import logging

logger = logging.getLogger(__name__)

def kb_file_view():
    """Display the knowledge base files in a simple list view."""
    st.header("Knowledge Base Files")
    
    # Get KB files info from session state (populated during RAG initialization)
    if "kb_files_info" in st.session_state and st.session_state["kb_files_info"]:
        files_info = st.session_state["kb_files_info"]
        
        # Create a container with fixed height and scrolling for the file list
        file_container = st.container(height=400, border=True)
        
        with file_container:
            if not files_info:
                st.info("No files found in the knowledge base.")
                return
            
            # Get the KB directory path from the same location used in rag_system.py
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent
            kb_directory = project_root / "kb"
            
            # Track selected file in session state
            if 'selected_kb_file' not in st.session_state:
                st.session_state.selected_kb_file = None
            
            # Display files with icons and metadata
            for file_info in files_info:
                file_name = file_info["name"]
                file_path = kb_directory / file_name
                
                # Get file metadata
                try:
                    file_size = os.path.getsize(file_path)
                    file_size_str = format_file_size(file_size)
                    mod_time = os.path.getmtime(file_path)
                    mod_date = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
                except Exception as e:
                    logger.error(f"Error getting metadata for {file_name}: {e}")
                    file_size_str = "Unknown"
                    mod_date = "Unknown"
                
                # Determine if this file is selected
                is_selected = st.session_state.selected_kb_file == file_name
                
                # Create a button with file info
                button_style = "background-color: #f0f2f6;" if is_selected else ""
                
                # Display file with icon and metadata
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if st.button(f"📄 {file_name}", key=f"file_{file_name}", 
                                use_container_width=True, 
                                help=f"Click to select {file_name}"):
                        # Update selected file
                        st.session_state.selected_kb_file = file_name if not is_selected else None
                        st.rerun()
                
                with col2:
                    st.text(file_size_str)
                
                with col3:
                    st.text(mod_date)
    else:
        st.info("Knowledge base information not available. Please initialize the system first.")

def format_file_size(size_bytes):
    """Format file size from bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"