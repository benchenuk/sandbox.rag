# rag/rag_system.py
import os
import streamlit as st
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document

def create_documents(data):
    """
    Creates LangChain Document objects from task data.

    Args:
        data (list): A list of task dictionaries.

    Returns:
        list: A list of LangChain Document objects.
    """
    documents = []
    for i, task in enumerate(data):
        text = f"Title: {task['title']}\n"
        text += f"Description: {task['description']}\n"
        text += f"Tags: {task['tags']}\n"
        text += f"Timestamp: {task['timestamp']}\n\n"

        doc = Document(page_content=text, metadata=task)
        documents.append(doc)

    return documents

def initialize_rag_system(db, memory):
    """
    Initializes the RAG system, including embeddings, vector store, and retrieval chain.

    Args:
        db (TaskDatabase): An instance of the TaskDatabase class.
        memory (ConversationBufferMemory): The memory object for the conversational chain.

    Returns:
        tuple: A tuple containing the initialized ConversationalRetrievalChain and the task data.
               Returns (None, []) if the system cannot be initialized.
    """
    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        api_key = st.text_input("Please enter your Google API key:", type="password")
        if not api_key:
            st.warning("API key is required to proceed.")
            return None, []
        os.environ["GOOGLE_API_KEY"] = api_key

    genai.configure(api_key=api_key)

    # Load data from DB
    with st.spinner("Loading task data from db..."):
        task_data = db.get_all_tasks()

    if not task_data:
        st.error("No task data loaded. Please check your data file.")
        return None, []

    # Create documents from task data
    documents = create_documents([{'title': t['title'], 'description': t['description'], 'tags':t['tags'].split(','), 'timestamp': t['timestamp']} for t in task_data])

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
        memory=memory,
        verbose=True
    )

    return retrieval_chain, task_data
