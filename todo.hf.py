from typing import List, Dict
from datetime import datetime
from huggingface_hub import InferenceClient

class TaskRecommender:
    def __init__(self, hf_token: str):
        self.client = InferenceClient(
            model="mistralai/Mistral-7B-Instruct-v0.1",
            token=hf_token
        )
        self.tasks = []

    def add_task(self, title: str, description: str = "") -> None:
        """Add a new task to the system"""
        task = {
            "id": len(self.tasks) + 1,
            "title": title,
            "description": description,
            "created_at": datetime.now()
        }
        self.tasks.append(task)

    def find_relevant_tasks(self, query: str, limit: int = 3) -> List[Dict]:
        """Find most relevant tasks based on the query using Mistral"""
        if not self.tasks:
            return []

        # Prepare context for LLM
        tasks_context = "\n".join([
            f"Task {t['id']}: {t['title']}" + 
            (f" - {t['description']}" if t['description'] else "")
            for t in self.tasks
        ])

        prompt = f"""<s>[INST] Given these tasks:
{tasks_context}

Find the most relevant tasks for the query: "{query}"
Return only the task IDs in order of relevance, separated by commas.
Consider semantic meaning, not just keyword matching.
Only return tasks that are truly relevant to the query.

Response format: task_id1,task_id2 [/INST]"""

        # Get response from Mistral
        response = self.client.text_generation(
            prompt,
            max_new_tokens=50,
            temperature=0.3,
            top_p=0.95,
            repetition_penalty=1.1
        )

        # Parse response to get relevant task IDs
        try:
            # Clean up response and extract numbers
            response_text = response.strip()
            relevant_ids = [
                int(id.strip()) 
                for id in response_text.split(',')
                if id.strip().isdigit()
            ]

            # Return relevant tasks with full information
            relevant_tasks = [
                task for task in self.tasks 
                if task['id'] in relevant_ids
            ]

            return relevant_tasks[:limit]
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []

    def get_task_by_id(self, task_id: int) -> Dict:
        """Retrieve a task by its ID"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None

# Usage example
def main():
    # Initialize with Hugging Face token
    recommender = TaskRecommender(hf_token="API_KEY")

    # Add sample tasks
    recommender.add_task(
        "Watch an Avenger movie",
        "Need to relax and enjoy the latest Marvel movie"
    )
    recommender.add_task(
        "Try out Google AI Studio",
        "Experiment with Google's new AI development platform"
    )
    recommender.add_task(
        "Buy groceries",
        "Get milk, eggs, and bread"
    )

    # Find relevant tasks
    queries = ["movie", "relax", "AI", "shopping"]

    for query in queries:
        print(f"\nQuery: {query}")
        relevant_tasks = recommender.find_relevant_tasks(query)
        for task in relevant_tasks:
            print(f"- {task['title']}")

if __name__ == "__main__":
    main()