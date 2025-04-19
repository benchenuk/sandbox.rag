# /Users/benchen/Development/sandbox.todo.llm/rag/rag_system.py
import os
import streamlit as st
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io
import logging
from pathlib import Path # Import Path for easier path manipulation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Define the Knowledge Base directory relative to this script ---
# Assuming rag_system.py is in /rag, and kb is at the root level (../kb)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
KB_DIRECTORY = PROJECT_ROOT / "kb"

# --- Helper function for file processing (Focus on Markdown) ---
# This remains useful if uploads are ever used, but we'll read directly for KB files
def extract_text_from_md_file(uploaded_file):
    """Extracts text content from an uploaded Markdown file."""
    bytes_data = uploaded_file.getvalue()
    file_name = uploaded_file.name
    text = ""
    logger.info(f"Attempting to extract text from uploaded Markdown file: {file_name}")

    # Ensure it's actually a markdown file based on name (simple check)
    if not file_name.lower().endswith(".md"):
        logger.warning(f"Skipping uploaded file as it does not end with .md: {file_name}")
        return None

    try:
        # Attempt common encodings for text files
        try:
            text = bytes_data.decode("utf-8")
            logger.info(f"Successfully decoded uploaded '{file_name}' with UTF-8.")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decoding failed for uploaded '{file_name}', trying latin-1.")
            try:
                text = bytes_data.decode("latin-1") # Try another common encoding
                logger.info(f"Successfully decoded uploaded '{file_name}' with latin-1.")
            except Exception as decode_err:
                st.warning(f"Could not decode uploaded Markdown file '{file_name}' with UTF-8 or latin-1: {decode_err}. Skipping.")
                logger.error(f"Decoding failed for uploaded {file_name} with multiple encodings: {decode_err}", exc_info=True)
                return None

        return text.strip() if text else None # Return None if extraction yielded empty string

    except Exception as e:
        st.error(f"Error processing uploaded file {file_name}: {e}")
        logger.error(f"Error processing uploaded file {file_name}: {e}", exc_info=True)
        return None # Indicate failure

# --- Renamed and Updated create_documents for Tasks ---
def create_task_documents(data):
    """
    Creates LangChain Document objects from task data.

    Args:
        data (list): A list of task dictionaries.

    Returns:
        list: A list of LangChain Document objects.
    """
    documents = []
    logger.info(f"Creating documents for {len(data)} tasks.")
    for i, task in enumerate(data):
        # Ensure tags are handled correctly (assuming they are already strings from DB)
        # If tags are stored as comma-separated string in DB, use it directly.
        # If they are list, join them. Adjust based on actual DB format.
        tags_str = task.get('tags', '')
        if isinstance(tags_str, list): # Handle case where tags might be list
            tags_str = ', '.join(tags_str)

        # Add a type hint for better context during retrieval
        page_content = f"Type: Task\n"
        page_content += f"Title: {task.get('title', 'N/A')}\n"
        page_content += f"Description: {task.get('description', 'N/A')}\n"
        page_content += f"Tags: {tags_str}\n" # Use the processed string
        page_content += f"Timestamp: {task.get('timestamp', 'N/A')}\n\n"

        # Ensure metadata values are simple types (str, int, float, bool)
        # Task ID is crucial for potential future actions
        metadata = {
            "source_type": "task",
            "task_id": str(task.get('id', f'task_index_{i}')), # Use DB ID if available, ensure string
            "title": task.get('title', 'N/A'),
            "tags": tags_str, # Use the processed string
            "timestamp": task.get('timestamp', 'N/A')
        }
        # Filter out None values from metadata if necessary
        metadata = {k: v for k, v in metadata.items() if v is not None}

        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)
    logger.info(f"Created {len(documents)} task documents.")
    return documents

# --- Function for creating documents from uploaded Markdown files ---
def create_file_documents(uploaded_files):
    """Creates LangChain Document objects from uploaded Markdown files with chunking."""
    file_documents = []
    processed_files_info = [] # To return info to UI {name: ..., chunks: ...}

    # Filter for Markdown files only first
    md_files = [f for f in uploaded_files if f.name.lower().endswith(".md")]
    if not md_files:
        logger.info("No Markdown (.md) files found in uploaded list.")
        return [], [] # Return empty lists if no md files

    logger.info(f"Processing {len(md_files)} uploaded Markdown files.")

    # Configure the text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, # Experiment with size
        chunk_overlap=200,  # Overlap helps maintain context between chunks
        length_function=len,
        add_start_index=True, # Useful for referencing original position if needed
    )

    for uploaded_file in md_files:
        file_name = uploaded_file.name
        logger.info(f"Processing uploaded Markdown file: {file_name}")
        text = extract_text_from_md_file(uploaded_file) # Use the MD-specific extractor

        if text:
            # Split the extracted text into chunks
            chunks = text_splitter.split_text(text)
            num_chunks = len(chunks)
            logger.info(f"Splitting uploaded '{file_name}' into {num_chunks} chunks.")

            for i, chunk in enumerate(chunks):
                # Add type hint and source filename to content and metadata
                page_content = f"Type: File Content\nSource File: {file_name}\n\n{chunk}"
                metadata = {
                    "source_type": "file",
                    "filename": file_name,
                    "chunk_index": i,
                }
                metadata = {k: v for k, v in metadata.items() if v is not None}
                doc = Document(page_content=page_content, metadata=metadata)
                file_documents.append(doc)

            # Store info about the processed file (using name as key for simplicity)
            # Find existing entry or add new one
            file_info = next((item for item in processed_files_info if item["name"] == file_name), None)
            if file_info:
                file_info["chunks"] += num_chunks
            else:
                processed_files_info.append({"name": file_name, "chunks": num_chunks})

            logger.info(f"Successfully created {num_chunks} document chunks for uploaded {file_name}")
        else:
            logger.warning(f"No text extracted or processed for uploaded {file_name}, skipping.")

    logger.info(f"Created a total of {len(file_documents)} documents from {len(processed_files_info)} uploaded Markdown files.")
    return file_documents, processed_files_info

# --- NEW function for creating documents from the KB directory ---
def create_documents_from_kb(kb_dir_path: Path):
    """Scans a directory for .md files, reads them, and creates chunked Document objects."""
    kb_documents = []
    processed_kb_files_info = []

    if not kb_dir_path.is_dir():
        logger.warning(f"Knowledge base directory not found or is not a directory: {kb_dir_path}")
        # st.warning(f"Knowledge base directory '{kb_dir_path.name}' not found. No files loaded.") # Optional UI feedback
        return [], []

    logger.info(f"Scanning knowledge base directory: {kb_dir_path}")

    # Configure the text splitter (same as for uploads)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )

    md_files_found = list(kb_dir_path.rglob("*.md")) # Recursively find all .md files
    logger.info(f"Found {len(md_files_found)} Markdown files in {kb_dir_path}.")

    if not md_files_found:
        return [], []

    with st.spinner(f"Processing {len(md_files_found)} files from knowledge base..."):
        for file_path in md_files_found:
            file_name = file_path.name
            logger.info(f"Processing KB file: {file_path}")
            text = None
            try:
                # Try reading with UTF-8 first, then latin-1 as fallback
                try:
                    text = file_path.read_text(encoding="utf-8")
                    logger.info(f"Successfully read KB file '{file_name}' with UTF-8.")
                except UnicodeDecodeError:
                    logger.warning(f"UTF-8 decoding failed for KB file '{file_name}', trying latin-1.")
                    try:
                        text = file_path.read_text(encoding="latin-1")
                        logger.info(f"Successfully read KB file '{file_name}' with latin-1.")
                    except Exception as decode_err:
                        st.warning(f"Could not decode KB file '{file_name}' with UTF-8 or latin-1: {decode_err}. Skipping.")
                        logger.error(f"Decoding failed for KB file {file_name} with multiple encodings: {decode_err}", exc_info=True)
                        continue # Skip this file
                except Exception as read_err: # Catch other file reading errors
                     st.error(f"Error reading KB file {file_name}: {read_err}")
                     logger.error(f"Error reading KB file {file_name}: {read_err}", exc_info=True)
                     continue # Skip this file

                if text and text.strip():
                    text = text.strip()
                    chunks = text_splitter.split_text(text)
                    num_chunks = len(chunks)
                    logger.info(f"Splitting KB file '{file_name}' into {num_chunks} chunks.")

                    for i, chunk in enumerate(chunks):
                        page_content = f"Type: Knowledge Base File\nSource File: {file_name}\n\n{chunk}"
                        metadata = {
                            "source_type": "kb_file",
                            "filename": file_name,
                            "full_path": str(file_path), # Store full path for reference
                            "chunk_index": i,
                        }
                        metadata = {k: v for k, v in metadata.items() if v is not None}
                        doc = Document(page_content=page_content, metadata=metadata)
                        kb_documents.append(doc)

                    # Store info about the processed file
                    processed_kb_files_info.append({"name": file_name, "chunks": num_chunks})
                    logger.info(f"Successfully created {num_chunks} document chunks for KB file {file_name}")
                else:
                    logger.warning(f"No content extracted or empty content in KB file {file_name}, skipping.")

            except Exception as e:
                st.error(f"Unexpected error processing KB file {file_name}: {e}")
                logger.error(f"Unexpected error processing KB file {file_name}: {e}", exc_info=True)
                continue # Skip this file

    logger.info(f"Created a total of {len(kb_documents)} documents from {len(processed_kb_files_info)} KB files.")
    return kb_documents, processed_kb_files_info


# --- Modified initialize_rag_system ---
def initialize_rag_system(db, memory, uploaded_files=None): # Keep uploaded_files param for potential future use
    """
    Initializes the RAG system, combining task data and knowledge base file content.

    Args:
        db (TaskDatabase): Task database instance.
        memory (ConversationBufferMemory): Chat memory.
        uploaded_files (list, optional): List of Streamlit UploadedFile objects (currently unused in default flow).

    Returns:
        tuple: (chain, task_data, processed_files_info)
        Returns (None, [], []) if initialization fails critically.
        processed_files_info is a list of dicts: [{'name': str, 'chunks': int}] for KB files.
    """
    logger.info("Initializing RAG system...")
    # uploaded_files parameter is kept but might be None or empty from rag_ui.py calls
    # We prioritize loading from the KB directory.

    # --- API Key Check ---
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        st.warning("Google API key is missing. Please set the GOOGLE_API_KEY environment variable.")
        logger.warning("Google API key not found in environment variables.")
        return None, [], []
    try:
        genai.configure(api_key=api_key)
        logger.info("Google GenAI configured.")
    except Exception as e:
        st.error(f"Failed to configure Google GenAI: {e}")
        logger.error(f"Google GenAI configuration failed: {e}", exc_info=True)
        return None, [], []

    all_documents = []
    processed_files_info = [] # Will store info about processed KB files
    task_data = [] # Initialize task_data

    # 1. Load and process task data
    try:
        with st.spinner("Loading and processing task data..."):
            task_data = db.get_all_tasks()
            if task_data:
                task_documents = create_task_documents(task_data)
                all_documents.extend(task_documents)
                logger.info(f"Loaded {len(task_documents)} documents from tasks.")
            else:
                logger.warning("No task data found in the database.")
    except Exception as e:
        st.error(f"Failed to load or process task data: {e}")
        logger.error(f"Error loading/processing task data: {e}", exc_info=True)
        # Decide whether to proceed without tasks or fail
        # return None, [], [] # Option: Fail if tasks can't load

    # 2. Load and process files from the Knowledge Base directory
    try:
        logger.info(f"Attempting to load files from KB directory: {KB_DIRECTORY}")
        kb_documents, kb_processed_info = create_documents_from_kb(KB_DIRECTORY)
        if kb_documents:
            all_documents.extend(kb_documents)
            processed_files_info.extend(kb_processed_info) # Add KB file info
            logger.info(f"Added {len(kb_documents)} documents from {len(kb_processed_info)} KB files.")
        else:
            logger.info("No documents generated from the KB directory.")
            # Optionally inform user if KB dir was expected but empty/missing
            if KB_DIRECTORY.exists() and not any(KB_DIRECTORY.rglob("*.md")):
                 st.info(f"Knowledge base directory '{KB_DIRECTORY.name}' is empty or contains no Markdown files.")
            elif not KB_DIRECTORY.exists():
                 st.info(f"Knowledge base directory '{KB_DIRECTORY.name}' not found.")

    except Exception as e:
        st.error(f"Failed to process files from KB directory: {e}")
        logger.error(f"Error processing KB files: {e}", exc_info=True)
        # Decide whether to proceed without KB data or fail
        # return None, task_data, [] # Option: Fail if KB processing errors occur

    # --- Section for processing uploaded_files (Optional, if needed in future) ---
    # if uploaded_files:
    #     logger.info("Processing explicitly uploaded files (if any)...")
    #     try:
    #         # Filter only for .md files before showing spinner
    #         md_files_count = sum(1 for f in uploaded_files if f.name.lower().endswith(".md"))
    #         if md_files_count > 0:
    #             with st.spinner(f"Processing {md_files_count} uploaded Markdown file(s)..."):
    #                 # Pass the full list, the function will filter
    #                 uploaded_file_documents, uploaded_processed_info = create_file_documents(uploaded_files)
    #                 if uploaded_file_documents:
    #                     all_documents.extend(uploaded_file_documents)
    #                     processed_files_info.extend(uploaded_processed_info) # Combine info if needed
    #                     logger.info(f"Added {len(uploaded_file_documents)} documents from {len(uploaded_processed_info)} explicitly uploaded files.")
    #                 else:
    #                     logger.warning("No documents were generated from the explicitly uploaded files.")
    #         else:
    #             logger.info("No Markdown files provided in the explicit upload list.")
    #     except Exception as e:
    #         st.error(f"Failed to process explicitly uploaded files: {e}")
    #         logger.error(f"Error processing explicitly uploaded files: {e}", exc_info=True)
    #         # Decide if you want to proceed without file data or fail

    # 3. Check if we have any documents at all
    if not all_documents:
        st.warning("No documents found (neither tasks nor KB files). Assistant will have no knowledge base.")
        logger.warning("No documents available to build vector store. RAG system will be inactive.")
        return None, task_data, [] # Return empty list for processed_files_info

    # 4. Create embeddings and vector store
    vector_store = None
    try:
        with st.spinner(f"Creating embeddings and vector store from {len(all_documents)} documents... (can take a moment)"):
            logger.info(f"Creating vector store from {len(all_documents)} total documents.")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vector_store = FAISS.from_documents(all_documents, embeddings)
            logger.info("FAISS vector store created successfully.")
    except Exception as e:
        st.error(f"Failed to create vector store: {e}")
        logger.error(f"FAISS vector store creation failed: {e}", exc_info=True)
        return None, task_data, processed_files_info # Return data/info obtained so far

    # 5. Initialize LLM
    llm = None
    try:
        model_name = "gemini-1.5-flash"
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.3, convert_system_message_to_human=True)
        logger.info(f"Initialized LLM with model: {model_name}")
    except Exception as e:
        st.error(f"Failed to initialize the Language Model (Model: {model_name}): {e}")
        logger.error(f"LLM initialization failed: {e}", exc_info=True)
        return None, task_data, processed_files_info

    # 6. Create retrieval chain
    retrieval_chain = None
    try:
        retrieval_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vector_store.as_retriever(),
            memory=memory,
            verbose=True, # Keep verbose for debugging
        )
        logger.info("ConversationalRetrievalChain created successfully.")
        # Update success message to reflect KB loading
        kb_file_count = len(processed_files_info)
        task_count = len(task_data) if task_data else 0
        success_message = f"Assistant ready! Knowledge base includes {task_count} tasks"
        if kb_file_count > 0:
            success_message += f" and content from {kb_file_count} KB file(s)."
        else:
            success_message += "."
        st.success(success_message)

    except Exception as e:
        st.error(f"Failed to create retrieval chain: {e}")
        logger.error(f"ConversationalRetrievalChain creation failed: {e}", exc_info=True)
        return None, task_data, processed_files_info

    logger.info("RAG system initialization complete.")
    return retrieval_chain, task_data, processed_files_info

# ... rest of code remains same (if any)