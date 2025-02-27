import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document

# Page configuration
st.set_page_config(
    page_title="Task Recommendation System",
    page_icon="✅",
    layout="wide"
)

# Initialize session state for chat history if it doesn't exist
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

# Function to load test data
def load_test_data(filepath="todo.rag.test_data.json"):
    """Loads test data from a JSON file."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Test data file not found: {filepath}")
        return []
    except json.JSONDecodeError:
        st.error(f"Invalid JSON format in {filepath}")
        return []
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return []

# Function to create documents
def create_documents(data):
    documents = []
    for i, task in enumerate(data):
        text = f"Title: {task['title']}\n"
        text += f"Description: {task['description']}\n"
        text += f"Tags: {', '.join(task['tags'])}\n"
        text += f"Timestamp: {task['timestamp']}\n\n"

        doc = Document(page_content=text, metadata=task)
        documents.append(doc)

    return documents

# Function to add a new task
def add_new_task(title, description, tags_string):
    # Create a new task
    new_task = {
        "title": title,
        "description": description,
        "tags": [tag.strip() for tag in tags_string.split(",") if tag.strip()],
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to session state
    st.session_state.task_data.append(new_task)
    
    # Reinitialize the RAG system with updated data
    st.session_state.chain, _ = initialize_rag_system()
    return True

# Initialize the RAG system
def initialize_rag_system():
    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        api_key = st.text_input("Please enter your Google API key:", type="password")
        if not api_key:
            st.warning("API key is required to proceed.")
            return None, []
        os.environ["GOOGLE_API_KEY"] = api_key

    genai.configure(api_key=api_key)
    
    # Load test data if task_data is empty
    if not st.session_state.task_data:
        with st.spinner("Loading task data..."):
            test_data = load_test_data()
            
            if not test_data:
                st.error("No task data loaded. Please check your data file.")
                return None, []
            
            # Store in session state
            st.session_state.task_data = test_data
    
    # Create documents from task data
    documents = create_documents(st.session_state.task_data)
    
    # Create embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Create vector store
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
    
    # Create retrieval chain
    retrieval_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(),
        memory=st.session_state.memory,
        verbose=True
    )
    
    return retrieval_chain, st.session_state.task_data

# Main UI layout
st.title("✅ Task Recommendation System")

# Initialize the system if not already done
if st.session_state.chain is None:
    st.session_state.chain, _ = initialize_rag_system()

# Split the screen into two columns
col1, col2 = st.columns([2, 3])

# Left column: Task list and add task form
with col1:
    st.header("Your Tasks")
    
    # Filter options
    filter_options = ["All"]
    if st.session_state.task_data:
        # Extract unique project tags
        all_tags = set()
        for task in st.session_state.task_data:
            all_tags.update(task['tags'])
        filter_options.extend(sorted(all_tags))
    
    selected_filter = st.selectbox("Filter by tag:", filter_options)
    
    # Display tasks based on filter
    if st.session_state.task_data:
        filtered_tasks = st.session_state.task_data
        if selected_filter != "All":
            filtered_tasks = [task for task in st.session_state.task_data if selected_filter in task['tags']]
        
        # Create a container with fixed height and scrolling
        task_container = st.container(height=400, border=True)
        
        with task_container:
            for i, task in enumerate(filtered_tasks):
                with st.expander(f"📌 {task['title']}"):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Tags:** {', '.join(task['tags'])}")
                    # Convert timestamp to a more readable format
                    timestamp = datetime.fromisoformat(task['timestamp'])
                    st.write(f"**Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}")
    
    # Add new task section below the task list
    st.subheader("Add New Task")
    
    # Task title input (always visible)
    task_title = st.text_input("Task Title", placeholder="Enter task title")
    
    # Expandable section for description and tags
    with st.expander("Add Description and Tags", expanded=False):
        task_description = st.text_area("Task Description", placeholder="Enter task description")
        task_tags = st.text_input("Tags (comma-separated)", placeholder="e.g., Project A, development, frontend")
    
    # Add task button
    if st.button("Add Task"):
        if not task_title:
            st.error("Task title is required!")
        else:
            # Use empty string for description if not provided
            description = task_description if task_description else ""
            # Use "general" as default tag if none provided
            tags = task_tags if task_tags else "general"
            
            # Add the new task
            success = add_new_task(task_title, description, tags)
            if success:
                st.success(f"Task '{task_title}' added successfully!")
                # Clear the form fields by rerunning
                st.rerun()

# Right column: Chat interface
with col2:
    st.header("Task Assistant")
    st.write("Ask me anything about your tasks!")
    
    # Display chat history
    chat_container = st.container(height=500, border=True)
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**Assistant:** {message['content']}")
    
    # Chat input
    user_input = st.text_input("Your question:", placeholder="e.g., What tasks are related to Project A?")
    
    if st.button("Send") and user_input:
        if st.session_state.chain is None:
            st.error("System not initialized. Please provide your API key.")
        else:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Get response from the chain
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.chain.invoke({"question": user_input})
                    answer = response["answer"]
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    
                    # Rerun to update the UI
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

    # Add some example questions
    with st.expander("Example questions you can ask"):
        st.markdown("""
        - What tasks are related to Project A?
        - What should I work on next?
        - Do I have any reading tasks?
        - What are my highest priority tasks?
        - Show me all tasks related to development
        - What personal development tasks do I have?
        """)

# Footer
st.divider()
st.caption("Task Recommendation System powered by Gemini and LangChain")