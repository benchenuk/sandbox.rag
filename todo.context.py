# Add these imports if not already present
from typing import List, Dict, Tuple
import pickle
import hashlib
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
                pass    # sqlite_sequence table doesn't exist, which is fines

class EnhancedVectorIndex:
    def __init__(self, embedding_dim: int = 768, use_llm: bool = True):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.use_llm = use_llm
        self.task_ids = []
        self.lock = Lock()
        # Cache for enhanced embeddings
        self.enhanced_embeddings: Dict[int, np.ndarray] = {}

        if use_llm:
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def enhance_task_descriptions(self, tasks: List[Tuple[int, str]]) -> Dict[int, str]:
        """Enhance multiple task descriptions in a single batch with full context awareness"""
        enhanced_texts = {}

        if not self.use_llm:
            return {task_id: text for task_id, text in tasks}

        try:
            # Prepare batch prompt with clear instructions and context
            batch_prompt = """
            You are analyzing a set of tasks to enhance their descriptions with contextual information and categorization, 
            so they become more searchable and meaningful.

            First, read through ALL tasks to understand the overall context and relationships between tasks.
            Then, for EACH task:
            1. Identify the primary category
            2. Add relevant contextual keywords and related concepts
            3. Include any cross-task dependencies or relationships
            4. Add high-level tags in [brackets] at the end

            Format each enhanced task as:
            TASK: <original task>
            ENHANCED: <enhanced description>
            TAGS: [tag1] [tag2] [tag3]

            Here are all the tasks to analyze:
            """

            # Add all tasks for context
            for i, (_, text) in enumerate(tasks, 1):
                batch_prompt += f"\n{i}. {text}"

            batch_prompt += "\n\nNow, provide the enhanced version of each task while maintaining their relationships and overall context:"

            response = await self.model.generate_content_async(batch_prompt)
            enhanced_batch = response.text.split('TASK:')[1:]  # Split by TASK: and remove empty first element

            # Process enhanced descriptions
            for i, (task_id, original_text) in enumerate(tasks):
                if i < len(enhanced_batch):
                    # Extract enhanced text and tags
                    enhanced_part = enhanced_batch[i].strip()
                    try:
                        # Extract tags if present
                        tags_start = enhanced_part.rfind('TAGS:')
                        if tags_start != -1:
                            enhanced_text = enhanced_part[:tags_start].strip()
                            tags = enhanced_part[tags_start:].strip()
                        else:
                            enhanced_text = enhanced_part
                            tags = ""

                        # Combine original text with enhancement and tags
                        enhanced_texts[task_id] = f"{original_text} {enhanced_text} {tags}"
                        logging.debug(f"Enhanced task {task_id} : {enhanced_texts[task_id]}")
                    except Exception as e:
                        logging.warning(f"Error processing enhancement for task {task_id}: {e}")
                        enhanced_texts[task_id] = original_text
                else:
                    enhanced_texts[task_id] = original_text

            return enhanced_texts
        except Exception as e:
            logging.warning(f"Batch enhancement failed: {e}")
            return {task_id: text for task_id, text in tasks}

    async def build_index_for_tasks(self, tasks: List[Task]):
        """Build or update index with enhanced task descriptions in a single batch"""
        with self.lock:
            # Reset index
            self.index = faiss.IndexFlatL2(self.embedding_model.get_sentence_embedding_dimension())
            self.task_ids = []

            # Prepare all tasks for batch processing
            task_texts = [(task.id, f"{task.title} {task.description}".strip()) 
                         for task in tasks]

            # Enhance all tasks in a single batch
            enhanced_texts = await self.enhance_task_descriptions(task_texts)

            # Convert all enhanced texts to embeddings in a single batch
            all_texts = [enhanced_texts[task_id] for task_id, _ in task_texts]
            all_embeddings = self.embedding_model.encode(all_texts, 
                                                       normalize_embeddings=True,
                                                       show_progress_bar=False)

            # Store embeddings and task IDs
            self.task_ids = [task_id for task_id, _ in task_texts]
            self.index.add(np.array(all_embeddings, dtype=np.float32))

            # Cache the embeddings
            for idx, (task_id, _) in enumerate(task_texts):
                self.enhanced_embeddings[task_id] = all_embeddings[idx]

    async def search(self, query: str, k: int = 5) -> List[int]:
        """Search for relevant tasks using enhanced query"""
        # enhanced_query = await self.enhance_search_query(query)
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

    async def add_task(self, title: str, description: str = "") -> None:
        """Add task to database without LLM enhancement"""
        task = Task(
            id=0,
            title=title,
            description=description,
            created_at=datetime.now()
        )
        task_id = self.task_store.add_task(task)

    async def find_relevant_tasks(self, query: str, limit: int = 5) -> List[Task]:
        """Find relevant tasks using enhanced search"""
        # Get all tasks and build index if needed
        all_tasks = self.task_store.get_all_tasks()

        # Build/update index with all tasks in a single batch
        await self.vector_index.build_index_for_tasks(all_tasks)

        # Search using enhanced query
        relevant_ids = await self.vector_index.search(query, k=limit)
        return self.task_store.get_tasks_by_ids(relevant_ids)

async def main():
    # Initialize recommender
    recommender = TaskRecommender(use_llm=True)
    recommender.task_store.delete_all_tasks()

    # Define sample tasks grouped by semantic context
    tasks_list = [
        # Development Tasks
        # ("Debug authentication service", "Fix OAuth token refresh mechanism in login flow"),
        # ("Optimize database queries", "Improve performance of slow-running SQL queries in user service"),
        # ("Implement API endpoints", "Create new REST endpoints for customer dashboard"),
        # ("Code review backlog", "Review pending pull requests for frontend features"),
        # ("Update dependencies", "Upgrade npm packages and fix security vulnerabilities"),

        # Documentation & Communication Tasks
        # ("Write API documentation", "Create Swagger docs for new payment API endpoints"),
        # ("Draft release notes", "Prepare changelog for version 2.0 release"),
        # ("Technical blog post", "Write article about our microservices architecture"),
        # ("Update user guide", "Revise installation and setup documentation"),
        # ("Team newsletter", "Compile monthly technical achievements and updates"),

        # Planning & Management Tasks
        # ("Sprint planning meeting", "Organize next sprint's goals and task allocation"),
        # ("Architecture review", "Evaluate proposed system design changes"),
        # ("Resource allocation", "Plan team capacity for Q3 projects"),
        # ("Stakeholder presentation", "Prepare slides for quarterly technical review"),
        # ("Team performance review", "Complete developer evaluations for Q2"),

        # Infrastructure & Operations Tasks
        # ("Server maintenance", "Apply security patches to production servers"),
        # ("Monitoring setup", "Configure Grafana dashboards for new services"),
        # ("Backup verification", "Test database backup and recovery procedures"),
        # ("CI/CD pipeline update", "Optimize build times in Jenkins pipeline"),
        # ("Cloud cost optimization", "Review and optimize AWS resource usage"),

        # Personal Tasks
        ("Grocery shopping", "Buy vegetables, fruits, and other essentials for the week"),
        ("Morning workout", "Complete a 30-minute cardio and strength training session"),
        ("Read a book", "Finish reading the last two chapters of the novel"),
        ("Plan vacation", "Research destinations and book flights for the summer trip"),
        ("Family dinner", "Prepare a special meal for the family gathering this weekend"),
        ("Gardening", "Plant new flowers and trim the hedges in the backyard"),
        ("Organize closet", "Sort clothes and donate items no longer needed"),
        ("Pay bills", "Settle electricity, water, and internet bills for the month"),
        ("Call parents", "Catch up with mom and dad over a phone call"),
        ("Bake a cake", "Try a new recipe for a chocolate cake for the weekend"),
    ]

    # Add tasks (now without LLM enhancement)
    for title, description in tasks_list:
        await recommender.add_task(title, description)

    # Test queries
    queries = [
        # Short queries
        # "debugging service",
        # "database optimization",
        # "API documentation",
        # "team meeting",
        # "server maintenance",
        # "grocery shopping",
        # "morning workout",
        # "vacation planning",
        # "family dinner",
        # "baking",

        # Long queries
        # "How to fix issues with OAuth token refresh in the login flow?",
        # "What are the best practices for optimizing SQL queries in a user service?",
        # "Can you recommend tasks related to writing technical documentation?",
        # "I need to organize a sprint planning meeting for the next sprint's goals.",
        # "What tasks involve applying security patches to production servers?",
        # "What are some personal tasks related to gardening and organizing?",
        # "I want to plan a vacation and book flights for the summer trip.",
        # "What are some tasks related to catching up with family or parents?",

        # Manual test
        "Prepare family dinner"
    ]

    # Search and display results
    print("\nTesting task recommendations:")
    print("-" * 50)

    for query in queries:
        print(f"\nQuery: {query}")
        relevant_tasks = await recommender.find_relevant_tasks(query, limit=3)
        for task in relevant_tasks:
            print(f"- {task.title}: {task.description}")

    # Clean up
    recommender.task_store.delete_all_tasks()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())