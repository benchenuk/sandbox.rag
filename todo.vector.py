from typing import List, Dict
from datetime import datetime
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import sqlite3
from dataclasses import dataclass
from threading import Lock
import logging
import time
import google.generativeai as genai
from typing import Optional
import os

# Add at the beginning of the file, after imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class Task:
    id: int
    title: str
    description: str
    created_at: datetime

class TaskStore:
    def __init__(self, db_path: str = "tasks.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP
                )
            """)

    def add_task(self, task: Task) -> int:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO tasks (title, description, created_at) VALUES (?, ?, ?)",
                (task.title, task.description, task.created_at)
            )
            return cursor.lastrowid

    def get_all_tasks(self) -> List[Task]:
        cursor = self.conn.execute("SELECT * FROM tasks")
        return [Task(id=row[0], title=row[1], description=row[2], 
                    created_at=datetime.fromisoformat(row[3])) 
                for row in cursor.fetchall()]

    def get_tasks_by_ids(self, ids: List[int]) -> List[Task]:
        placeholder = ','.join('?' * len(ids))
        cursor = self.conn.execute(
            f"SELECT * FROM tasks WHERE id IN ({placeholder})", ids
        )
        return [Task(id=row[0], title=row[1], description=row[2], 
                    created_at=datetime.fromisoformat(row[3])) 
                for row in cursor.fetchall()]

    def delete_all_tasks(self):
        """Delete all tasks from the database."""
        with self.conn:
            self.conn.execute("DELETE FROM tasks")
            try:
                self.conn.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")  # Reset auto-increment
            except sqlite3.OperationalError:
                pass    # sqlite_sequence table doesn't exist, which is fine

class VectorIndex:
    def __init__(self, embedding_dim: int = 384):  # SentenceTransformer default dim
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.task_ids = []
        self.lock = Lock()

    def add_embedding(self, task_id: int, text: str):
        embedding = self.embedding_model.encode([text])[0]
        with self.lock:
            self.index.add(np.array([embedding], dtype=np.float32))
            self.task_ids.append(task_id)

    def search(self, query: str, k: int = 5) -> List[int]:
        query_embedding = self.embedding_model.encode([query])[0]
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), k
        )
        return [self.task_ids[idx] for idx in indices[0] if idx != -1]

class EnhancedVectorIndex:
    def __init__(self, embedding_dim: int = 768, use_llm: bool = True):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.use_llm = use_llm
        self.task_ids = []
        self.lock = Lock()

        # Initialize Gemini
        if use_llm:
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            # Using the most capable model
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def get_llm_enhanced_text(self, text: str) -> str:
        """Enhance text using Gemini for better semantic understanding"""
        try:
            prompt = f"""
            Enhance this task description while preserving its core meaning.
            Keep the enhancement concise and focused on the task context.
            Find high level tags that best abstraacts and categorises the task by context. 

            Task: {text}
            """

            response = await self.model.generate_content_async(prompt)
            enhanced_text = response.text

            # Combine original and enhanced text
            logging.debug(f"{text} - {enhanced_text}")
            return f"{text} {enhanced_text}"
        except Exception as e:
            logging.warning(f"Gemini enhancement failed: {e}")
            return text

    async def add_embedding(self, task_id: int, text: str):
        if self.use_llm:
            enhanced_text = await self.get_llm_enhanced_text(text)
        else:
            enhanced_text = text

        embedding = self.embedding_model.encode([enhanced_text], 
                                              normalize_embeddings=True,
                                              show_progress_bar=False)[0]

        with self.lock:
            self.index.add(np.array([embedding], dtype=np.float32))
            self.task_ids.append(task_id)

    async def search(self, query: str, k: int = 5) -> List[int]:
        if self.use_llm:
            enhanced_query = await self.get_llm_enhanced_text(query)
        else:
            enhanced_query = query

        query_embedding = self.embedding_model.encode([enhanced_query], 
                                                    normalize_embeddings=True)[0]
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), k
        )
        return [self.task_ids[idx] for idx in indices[0] if idx != -1]

class TaskRecommender:
    def __init__(self, use_llm: bool = True):
        self.task_store = TaskStore()
        self.vector_index = EnhancedVectorIndex(use_llm=use_llm)
        self._initialize_vector_index()

    def _initialize_vector_index(self):
        """Initialize vector index with existing tasks"""
        tasks = self.task_store.get_all_tasks()
        for task in tasks:
            self._add_to_vector_index(task)

    def _add_to_vector_index(self, task: Task):
        """Add a task to the vector index"""
        text = f"{task.title} {task.description}".strip()
        self.vector_index.add_embedding(task.id, text)

    async def add_task(self, title: str, description: str = "") -> None:
        task = Task(
            id=0,
            title=title,
            description=description,
            created_at=datetime.now()
        )
        task_id = self.task_store.add_task(task)
        task.id = task_id
        text = f"{task.title} {task.description}".strip()
        await self.vector_index.add_embedding(task_id, text)

    async def find_relevant_tasks(self, query: str, limit: int = 5) -> List[Task]:
        relevant_ids = await self.vector_index.search(query, k=limit)
        return self.task_store.get_tasks_by_ids(relevant_ids)

async def main():
    # Initialize recommender
    recommender = TaskRecommender(use_llm=True)
    recommender.task_store.delete_all_tasks()

    # Define sample tasks (using a smaller subset for demonstration)
    tasks_list = [
        ("Complete project presentation", "Prepare slides for quarterly review"),
        ("Schedule dentist appointment", "Annual checkup and cleaning"),
        ("Update resume", "Add recent projects and skills"),
        ("Plan team building event", "Organize virtual team activity"),
        ("Review code pull requests", "Check team's pending PRs"),
        ("Buy groceries", "Get ingredients for weekly meal prep"),
        ("Write blog post", "Create technical article about vector databases"),
        ("Fix website bug", "Debug the user authentication issue"),
        ("Call insurance company", "Discuss policy renewal and coverage options"),
        ("Clean home office", "Organize desk and file paperwork")
    ]

    # Add tasks to the recommender
    for title, description in tasks_list:
        await recommender.add_task(title, description)

    # Print all tasks
    all_tasks = recommender.task_store.get_all_tasks()
    logging.info(f"Total number of tasks: {len(all_tasks)}")
    # loggin.info("All Tasks:")
    # for task in all_tasks :
    #     loggin.info(f"- {task.title}")

    # Test queries
    queries = [
        "project related tasks", 
        "personal tasks"
        # "technical planning",
        # "development tasks",
        # "meetings and coordination",
        # "documentation work"
    ]

    # Search and display results
    print("\nTesting task recommendations:")
    print("-" * 50)

    for query in queries:
        print(f"\nQuery: {query}")
        relevant_tasks = await recommender.find_relevant_tasks(query, limit=3)
        for task in relevant_tasks:
            print(f"- {task.title}: {task.description}")

    # Clean up database
    recommender.task_store.delete_all_tasks()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# Created/Modified files during execution:
# - tasks.db (SQLite database file)