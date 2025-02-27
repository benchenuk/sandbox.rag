# -*- coding: utf-8 -*-
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
import asyncio

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
        self.db_path = db_path
        self.conn = None
        self.create_tables()

    def _get_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def _close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        with self._get_connection():
            self._get_connection().execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP
                )
            """)

    def add_task(self, task: Task) -> int:
        with self._get_connection():
            cursor = self._get_connection().execute(
                "INSERT INTO tasks (title, description, created_at) VALUES (?, ?, ?)",
                (task.title, task.description, task.created_at)
            )
            return cursor.lastrowid

    def get_all_tasks(self) -> List[Task]:
        cursor = self._get_connection().execute("SELECT * FROM tasks")
        return [Task(id=row[0], title=row[1], description=row[2], 
                    created_at=datetime.fromisoformat(row[3])) 
                for row in cursor.fetchall()]

    def get_tasks_by_ids(self, ids: List[int]) -> List[Task]:
        placeholder = ','.join('?' * len(ids))
        cursor = self._get_connection().execute(
            f"SELECT * FROM tasks WHERE id IN ({placeholder})", ids
        )
        return [Task(id=row[0], title=row[1], description=row[2], 
                    created_at=datetime.fromisoformat(row[3])) 
                for row in cursor.fetchall()]

    def delete_all_tasks(self):
        with self._get_connection():
            self._get_connection().execute("DELETE FROM tasks")
            try:
                self._get_connection().execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
            except sqlite3.OperationalError:
                pass

    def __del__(self):
        self._close_connection()

class EnhancedVectorIndex:
    def __init__(self, embedding_dim: int = 768, use_llm: bool = True):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.use_llm = use_llm
        self.task_ids = []
        self.lock = Lock()
        self.enhanced_embeddings: Dict[int, np.ndarray] = {}

        if use_llm:
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def enhance_task_descriptions(self, tasks: List[Tuple[int, str]]) -> Dict[int, str]:
        enhanced_texts = {}
        if not self.use_llm:
            return {task_id: text for task_id, text in tasks}

        try:
            batch_prompt = """You are analyzing tasks to enhance descriptions..."""
            for i, (_, text) in enumerate(tasks, 1):
                batch_prompt += f"\n{i}. {text}"
            batch_prompt += "\n\nProvide enhanced versions:"

            response = await self.model.generate_content_async(batch_prompt)
            enhanced_batch = response.text.split('TASK:')[1:]
            logging.info("Enhanced task descriptions generated successfully: %s", enhanced_batch)

            for i, (task_id, original_text) in enumerate(tasks):
                if i < len(enhanced_batch):
                    enhanced_part = enhanced_batch[i].strip()
                    tags_start = enhanced_part.rfind('TAGS:')
                    if tags_start != -1:
                        enhanced_text = enhanced_part[:tags_start].strip()
                        tags = enhanced_part[tags_start:].strip()
                    else:
                        enhanced_text = enhanced_part
                        tags = ""
                    enhanced_texts[task_id] = f"{original_text} {enhanced_text} {tags}"
                else:
                    enhanced_texts[task_id] = original_text
            return enhanced_texts
        except Exception as e:
            logging.warning(f"Batch enhancement failed: {e}")
            return {task_id: text for task_id, text in tasks}

    async def build_index_for_tasks(self, tasks: List[Task]):
        with self.lock:
            self.index = faiss.IndexFlatL2(self.embedding_model.get_sentence_embedding_dimension())
            self.task_ids = []
            task_texts = [(task.id, f"{task.title} {task.description}".strip()) 
                        for task in tasks]
            enhanced_texts = await self.enhance_task_descriptions(task_texts)
            all_texts = [enhanced_texts[task_id] for task_id, _ in task_texts]
            all_embeddings = self.embedding_model.encode(all_texts, normalize_embeddings=True)
            self.task_ids = [task_id for task_id, _ in task_texts]
            self.index.add(np.array(all_embeddings, dtype=np.float32))
            for idx, (task_id, _) in enumerate(task_texts):
                self.enhanced_embeddings[task_id] = all_embeddings[idx]

    async def search(self, query: str, k: int = 5) -> List[int]:
        query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)[0]
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
        return [self.task_ids[idx] for idx in indices[0] if idx != -1]

class TaskRecommender:
    def __init__(self, use_llm: bool = True):
        self.task_store = TaskStore()
        self.vector_index = EnhancedVectorIndex(use_llm=use_llm)

    async def add_task(self, title: str, description: str = "") -> None:
        task = Task(id=0, title=title, description=description, created_at=datetime.now())
        self.task_store.add_task(task)

    async def find_relevant_tasks(self, query: str, limit: int = 5) -> List[Task]:
        all_tasks = self.task_store.get_all_tasks()
        await self.vector_index.build_index_for_tasks(all_tasks)
        relevant_ids = await self.vector_index.search(query, k=limit)
        return self.task_store.get_tasks_by_ids(relevant_ids)

async def main():
    recommender = TaskRecommender(use_llm=True)
    recommender.task_store.delete_all_tasks()

    tasks_list = [
        ("Grocery shopping", "Buy vegetables and essentials"),
        ("Morning workout", "30-minute cardio session"),
        ("Plan vacation", "Research summer destinations"),
        ("Family dinner", "Prepare weekend meal"),
        ("Bake a cake", "Chocolate cake recipe")
    ]

    for title, description in tasks_list:
        await recommender.add_task(title, description)

    queries = [
        "Prepare family dinner",
        # "Vacation ideas",
        # "Baking plans"
    ]

    print("\nTask Recommendations:")
    for query in queries:
        print(f"\nQuery: {query}")
        relevant_tasks = await recommender.find_relevant_tasks(query, limit=2)
        for task in relevant_tasks:
            print(f"- {task.title}: {task.description}")

    recommender.task_store.delete_all_tasks()

if __name__ == "__main__":
    asyncio.run(main())