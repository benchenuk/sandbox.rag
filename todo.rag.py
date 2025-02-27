import os
import logging
from datetime import datetime
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data with generic tasks
test_data = [
    {
        "title": "Research market trends",
        "description": "Research market trends for planning Project A. Needs to be done next Monday.",
        "tags": ["Project A", "planning", "research"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Create project plan",
        "description": "Develop a detailed project plan for Project A. Include timelines and milestones.",
        "tags": ["Project A", "planning", "development"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "UI development",
        "description": "Develop the frontend UI components for Project B. Focus on user experience.",
        "tags": ["Project B", "development", "frontend"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Read 'The Lean Startup'",
        "description": "Read 'The Lean Startup' by Eric Ries for personal development.",
        "tags": ["reading", "personal development"],
        "timestamp": datetime.now().isoformat()
    },
    # --- Project A (Focus on planning and initial setup) ---
    {
        "title": "Define Project A scope",
        "description": "Clearly define the scope and objectives of Project A.",
        "tags": ["Project A", "planning", "scope"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Identify key stakeholders",
        "description": "Identify all key stakeholders for Project A and their roles.",
        "tags": ["Project A", "planning", "stakeholders"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Set up project repository",
        "description": "Create and set up a Git repository for Project A.",
        "tags": ["Project A", "setup", "development"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Draft initial budget",
        "description": "Create a preliminary budget for Project A.",
        "tags": ["Project A", "budget", "planning"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Schedule kickoff meeting",
        "description": "Schedule the initial kickoff meeting for Project A.",
        "tags": ["Project A", "meetings", "planning"],
        "timestamp": datetime.now().isoformat()
    },
    # --- Project B (Focus on development and features) ---
    {
        "title": "Backend API design",
        "description": "Design the backend API endpoints for Project B.",
        "tags": ["Project B", "development", "backend"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Implement user authentication",
        "description": "Implement user authentication and authorization features for Project B.",
        "tags": ["Project B", "development", "security"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Database schema design",
        "description": "Design the database schema for Project B.",
        "tags": ["Project B", "development", "database"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Test UI components",
        "description": "Conduct thorough testing of all UI components for Project B.",
        "tags": ["Project B", "testing", "frontend"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Write API documentation",
        "description": "Create comprehensive documentation for the Project B API.",
        "tags": ["Project B", "documentation", "backend"],
        "timestamp": datetime.now().isoformat()
    },
    # --- Project C (New project, early stage) ---
    {
        "title": "Brainstorm Project C ideas",
        "description": "Brainstorm potential ideas and concepts for Project C.",
        "tags": ["Project C", "ideation", "planning"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Competitor analysis",
        "description": "Analyze the competitors in the market space for Project C.",
        "tags": ["Project C", "research", "planning"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Define MVP requirements",
        "description": "Define the minimum viable product (MVP) requirements for Project C.",
        "tags": ["Project C", "planning", "MVP"],
        "timestamp": datetime.now().isoformat()
    },
    # --- General Work Tasks ---
    {
        "title": "Review team progress",
        "description": "Review the progress of the team's tasks and address any roadblocks.",
        "tags": ["team", "management", "review"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Prepare weekly report",
        "description": "Prepare and submit the weekly progress report.",
        "tags": ["reporting", "management"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Attend team meeting",
        "description": "Attend the weekly team meeting to discuss progress and challenges.",
        "tags": ["team", "meetings", "communication"],
        "timestamp": datetime.now().isoformat()
    },
        {
        "title": "Schedule performance reviews",
        "description": "Plan and schedule the upcoming performance reviews for team members.",
        "tags": ["team", "management", "hr"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Onboard new team member",
        "description": "Guide and onboard the new team member to get them up to speed.",
        "tags": ["team", "management", "onboarding"],
        "timestamp": datetime.now().isoformat()
    },
    # --- Personal Tasks (Reading/Learning) ---
    {
        "title": "Read 'Deep Work'",
        "description": "Read 'Deep Work' by Cal Newport for improving focus and productivity.",
        "tags": ["reading", "personal development", "productivity"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Complete online course",
        "description": "Finish the online course on advanced Python techniques.",
        "tags": ["learning", "online course", "python"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Practice coding exercises",
        "description": "Practice coding exercises on LeetCode or similar platforms.",
        "tags": ["coding", "practice", "programming"],
        "timestamp": datetime.now().isoformat()
    },
    # --- Personal Tasks (Hobbies) ---
    {
        "title": "Plan weekend hike",
        "description": "Plan a hiking trip for the upcoming weekend.",
        "tags": ["hobbies", "hiking", "planning"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Practice guitar",
        "description": "Practice playing guitar for at least 30 minutes.",
        "tags": ["hobbies", "music", "guitar"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Start new book",
        "description": "Begin reading a new fiction novel for enjoyment.",
        "tags": ["hobbies", "reading", "fiction"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Organize workspace",
        "description": "Declutter and organize the workspace to improve efficiency.",
        "tags": ["personal", "organization"],
        "timestamp": datetime.now().isoformat()
    },
        {
        "title": "Meal prep for the week",
        "description": "Prepare meals for the upcoming week to save time.",
        "tags": ["personal", "health", "cooking"],
        "timestamp": datetime.now().isoformat()
    },
    {
        "title": "Update budget spreadsheet",
        "description": "Review and update the personal budget spreadsheet.",
        "tags": ["personal", "finance"],
        "timestamp": datetime.now().isoformat()
    },
]

def create_documents(data):
    documents = []
    for i, task in enumerate(data):
        text = f"Title: {task['title']}\n"
        text += f"Description: {task['description']}\n"
        text += f"Tags: {', '.join(task['tags'])}\n"
        text += f"Timestamp: {task['timestamp']}\n\n"

        from langchain.schema import Document
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
