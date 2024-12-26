import os
import uuid
from datetime import datetime
# import openai
from huggingface_hub import InferenceClient

#openai.api_key = os.getenv("OPENAI_API_KEY")

class Todo:
    def __init__(self, task, completed=False, created_at = None, completed_at=None, id = None):
      self.id = id if id else str(uuid.uuid4())
      self.task = task
      self.completed = completed
      self.created_at = created_at if created_at else datetime.now()
      self.completed_at = completed_at

    def __str__(self):
        completed_symbol = "[x]" if self.completed else "[ ]"
        created_date = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        completed_date = self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else "Not Completed"
        return f"{completed_symbol} - {self.task} (ID: {self.id}, Created: {created_date}, Completed: {completed_date})"

class TodoApp:
    def __init__(self):
        self.todos = []

    def add_todo(self, task):
        todo = Todo(task)
        self.todos.append(todo)
        return todo.id

    def list_todos(self):
        if not self.todos:
            print("No todos yet!")
            return
        for todo in self.todos:
            print(todo)

    def mark_complete(self, todo_id):
        for todo in self.todos:
            if todo.id == todo_id:
                todo.completed = True
                todo.completed_at = datetime.now()
                return True
        return False

    def delete_todo(self, todo_id):
         for idx,todo in enumerate(self.todos):
            if todo.id == todo_id:
                del self.todos[idx]
                return True
         return False

    def find_todo(self, todo_id):
         for todo in self.todos:
            if todo.id == todo_id:
                return todo
         return None
    
    # def suggest_todos(self, keywords, todos):
    #     # Create prompt by including the existing todos in the prompt
    #     todos_string = "\n".join([f"- {todo.task}" for todo in todos]) if todos else "None"
    #     prompt = f"Suggest 1 todo task related to these keywords: {', '.join(keywords)}. Considering these existing todos:\n{todos_string}\n Be concise."

    #     response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=[{"role": "user", "content": prompt}],
    #     max_tokens=100
    #     )
        
    #     suggestions = response.choices[0].message.content.strip().split("\n")
    #     return [suggestion.strip() for suggestion in suggestions if suggestion]


    
    def suggest_todos(self, keywords, todos):
        # Initialize the client with your API token
        client = InferenceClient(token="API_KEY")

        # Create context by including the existing todos
        todos_string = "\n".join([f"- {todo.task}" for todo in todos]) if todos else "None"
        
        # Create a more structured prompt that enforces using only existing tasks
        prompt = f"""Given the following list of existing tasks:
    {todos_string}

    And these keywords: {', '.join(keywords)}

    Please suggest tasks from the EXISTING list above that best matches these keywords.
    If no existing task matches the keywords, respond with 'No matching tasks found.'

    Your response should only contain the exact text of an existing task or 'No matching tasks found.'"""

        # Generate text using the model
        response = client.text_generation(
            prompt,
            model="mistralai/Mistral-7B-Instruct-v0.1",
            max_new_tokens=100,
            temperature=0.3,  # Lower temperature for more focused responses
            return_full_text=False
        )

        # Process the response and verify it matches an existing task
        suggestion = response.strip()
        
        # Verify the suggestion is actually from the existing tasks
        for todo in todos:
            if suggestion.lower().replace('-', '').strip() == todo.task.lower().strip():
                return [todo.task]
        
        return ["No matching tasks found."]


def main():
    app = TodoApp()
    while True:
        print("\nTodo App Menu:")
        print("1. Add Todo")
        print("2. List Todos")
        print("3. Mark Complete")
        print("4. Delete Todo")
        print("5. Get Suggestions")
        print("6. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            task = input("Enter the task: ")
            todo_id = app.add_todo(task)
            print(f"Added todo with ID {todo_id}")
        elif choice == "2":
            app.list_todos()
        elif choice == "3":
            todo_id = input("Enter the ID of the todo to mark complete: ")
            if app.mark_complete(todo_id):
                print("Todo marked as complete!")
            else:
                print("Todo not found")
        elif choice == "4":
            todo_id = input("Enter the ID of the todo to delete: ")
            if app.delete_todo(todo_id):
                print("Todo deleted!")
            else:
                print("Todo not found")
        elif choice == "5":
            keywords = input("Enter keywords for suggestions (comma-separated): ").split(",")
            suggestions = app.suggest_todos(keywords, app.todos) # pass app.todos
            print("Suggested todos:")
            for idx, suggestion in enumerate(suggestions):
                print(f"{idx+1}. {suggestion}")
        elif choice == "6":
            print("Exiting...")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
