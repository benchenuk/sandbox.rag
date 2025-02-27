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
    
    # Load test data
    with st.spinner("Loading task data..."):
        test_data = load_test_data()
        
        if not test_data:
            st.error("No task data loaded. Please check your data file.")
            return None, []
        
        # Create documents from test data
        documents = create_documents(test_data)
        
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
        
        return retrieval_chain, test_data

# Main UI layout
st.title("✅ Task Recommendation System")

# Initialize the system if not already done
if st.session_state.chain is None:
    st.session_state.chain, task_data = initialize_rag_system()
else:
    task_data = load_test_data()

# Split the screen into two columns
col1, col2 = st.columns([2, 3])

# Left column: Task list
with col1:
    st.header("Your Tasks")
    
    # Filter options
    filter_options = ["All"]
    if task_data:
        # Extract unique project tags
        all_tags = set()
        for task in task_data:
            all_tags.update(task['tags'])
        filter_options.extend(sorted(all_tags))
    
    selected_filter = st.selectbox("Filter by tag:", filter_options)
    
    # Display tasks based on filter
    if task_data:
        filtered_tasks = task_data
        if selected_filter != "All":
            filtered_tasks = [task for task in task_data if selected_filter in task['tags']]
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(filtered_tasks)
        
        # Create a container with fixed height and scrolling
        task_container = st.container(height=500, border=True)
        
        with task_container:
            for i, task in enumerate(filtered_tasks):
                with st.expander(f"📌 {task['title']}"):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Tags:** {', '.join(task['tags'])}")
                    # Convert timestamp to a more readable format
                    timestamp = datetime.fromisoformat(task['timestamp'])
                    st.write(f"**Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}")

# Right column: Chat interface
with col2:
    st.header("Task Assistant")
    st.write("Ask me anything about your tasks!")
    
    # Display chat history
    chat_container = st.container(height=400, border=True)
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