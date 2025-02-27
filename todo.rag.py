import os
import logging
from datetime import datetime
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data Loading from external file ---
import json

def load_test_data(filepath="todo.rag.test_data.json"):
    """Loads test data from a JSON file."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        # Validate data structure if needed
        return data
    except FileNotFoundError:
        logger.error(f"Test data file not found: {filepath}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {filepath}")
        return []
    except Exception as e:
        logger.error(f"An error occured: {e}")
        return []

def create_documents(data):
    documents = []
    for i, task in enumerate(data):
        text = f"Title: {task['title']}\n"
        text += f"Description: {task['description']}\n"
        text += f"Tags: {', '.join(task['tags'])}\n"
        text += f"Timestamp: {task['timestamp']}\n\n"

        doc = Document(page_content=text, metadata=task)
        documents.append(doc)

        logger.info(f"Created document {i+1}: {task['title']}")

    return documents

def main():
    # Set up the API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        api_key = input("Please enter your Google API key: ")
        os.environ["GOOGLE_API_KEY"] = api_key

    genai.configure(api_key=api_key)

    logger.info("Initializing the Task Recommendation System")

    # Load test data
    test_data = load_test_data()

    if not test_data:
        logger.error("No test data loaded. Exiting.")
        return

    # Create documents from test data
    documents = create_documents(test_data)

    # Create embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Create vector store
    logger.info("Creating vector store...")
    vector_store = FAISS.from_documents(documents, embeddings)

    # Initialize LLM
    logger.info("Initializing Gemini model...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)

    # Create memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    # Create retrieval chain
    logger.info("Creating retrieval chain...")
    retrieval_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(),
        memory=memory,
        verbose=True
    )

    # Simple terminal interface
    logger.info("System ready for queries!")
    print("\nTask Recommendation System")
    print("==========================")
    print("You can ask questions about your tasks, such as:")
    print("- What tasks are related to Project A?")
    print("- What should I work on next?")
    print("- Do I have any reading tasks?")

    while True:
        user_input = input("\nEnter your query (or 'quit' to exit): ")
        if user_input.lower() == "quit":
            break

        logger.info(f"User query: {user_input}")

        try:
            response = retrieval_chain.invoke({"question": user_input})
            print("\nResponse:")
            print(response["answer"])
            logger.info("Response generated successfully")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            print(f"Error: {str(e)}")

    logger.info("System shutting down")

if __name__ == "__main__":
    main()
