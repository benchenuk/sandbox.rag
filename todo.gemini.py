from typing import List, Dict
from datetime import datetime
import google.generativeai as genai

class TaskRecommender:
    def __init__(self, google_api_key: str):
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
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
        """Find most relevant tasks based on the query using Gemini"""
        if not self.tasks:
            return []

        # Prepare context for LLM
        tasks_context = "\n".join([
            f"Task {t['id']}: {t['title']}" + 
            (f" - {t['description']}" if t['description'] else "")
            for t in self.tasks
        ])

        prompt = f"""Given these tasks:
{tasks_context}

Find the most relevant tasks for the query: "{query}"
Return only the task IDs in order of relevance, separated by commas.
Consider semantic meaning, not just keyword matching.
Only return tasks that are truly relevant to the query.

Response format: task_id1,task_id2"""

        try:
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            
            # Clean up response and extract numbers
            response_text = response.text.strip()
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
            print(f"Error generating response: {e}")
            return []

    def get_task_by_id(self, task_id: int) -> Dict:
        """Retrieve a task by its ID"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None

# Usage example
def main():
    # Initialize with Google API key
    recommender = TaskRecommender(google_api_key="API_KEY")

     # Define a list of tasks with titles and descriptions
    tasks_list = [
        ("Complete project presentation", "Prepare slides for quarterly review"),
        ("Schedule dentist appointment", "Annual checkup and cleaning"),
        ("Update resume", "Add recent projects and skills"),
        ("Plan team building event", "Organize virtual team activity"),
        ("Review code pull requests", "Check team's pending PRs"),
        ("Write technical documentation", "Document new API endpoints"),
        ("Backup computer files", "Monthly backup to external drive"),
        ("Learn Python decorators", "Study advanced Python concepts"),
        ("Exercise routine", "30 minutes cardio and strength training"),
        ("Read tech article", "Stay updated with industry trends"),
        ("Fix website bug", "Address reported login issues"),
        ("Attend AI workshop", "Virtual workshop on machine learning"),
        ("Update software licenses", "Renew expired subscriptions"),
        ("Clean email inbox", "Archive old emails and organize folders"),
        ("Write blog post", "Share insights about recent project"),
        ("Network maintenance", "Check router and wifi settings"),
        ("Study cloud computing", "AWS certification preparation"),
        ("Organize digital files", "Clean up desktop and downloads"),
        ("Update password manager", "Review and update secure passwords"),
        ("Learn Docker basics", "Container fundamentals study"),
        ("Practice meditation", "15 minutes mindfulness session"),
        ("Review budget spreadsheet", "Update monthly expenses"),
        ("Call family", "Weekly catch-up call"),
        ("Garden maintenance", "Water plants and remove weeds"),
        ("Car service appointment", "Regular maintenance check"),
        ("Cook healthy meal", "Prepare balanced dinner"),
        ("Practice guitar", "Learn new song"),
        ("Home office setup", "Organize workspace"),
        ("Plan vacation", "Research destinations and costs"),
        ("Update LinkedIn profile", "Add recent achievements"),
        ("Learn JavaScript", "Study async/await concepts"),
        ("Fix kitchen sink", "Address leaking faucet"),
        ("Organize bookshelf", "Sort books by category"),
        ("Update antivirus", "Run system security check"),
        ("Write thank you notes", "Send appreciation messages"),
        ("Study design patterns", "Read about software architecture"),
        ("Plan birthday party", "Organize celebration details"),
        ("Create workout playlist", "Update exercise music"),
        ("Research new phone", "Compare latest models"),
        ("Update emergency contacts", "Review and update list"),
        ("Learn photography", "Practice composition techniques"),
        ("Fix bicycle", "Check brakes and tires"),
        ("Organize recipes", "Digitize favorite recipes"),
        ("Study Spanish", "Practice basic conversations"),
        ("Update smart home", "Configure new devices"),
        ("Write journal entry", "Daily reflection"),
        ("Plan garden layout", "Design spring planting"),
        ("Research investments", "Review portfolio options"),
        ("Clean garage", "Organize tools and storage"),
        ("Update insurance", "Review coverage details"),
        ("Learn React hooks", "Study useEffect and useState"),
        ("Fix printer", "Troubleshoot connection issues"),
        ("Create budget", "Plan monthly expenses"),
        ("Update emergency kit", "Check supplies and expiration"),
        ("Study algorithms", "Practice coding challenges"),
        ("Paint living room", "Choose colors and supplies"),
        ("Learn Git advanced", "Study branching strategies"),
        ("Fix door handle", "Replace broken hardware"),
        ("Organize photos", "Sort digital albums"),
        ("Update healthcare", "Review annual benefits"),
        ("Learn TypeScript", "Study type systems"),
        ("Fix window seal", "Address draft issues"),
        ("Create backup plan", "Document recovery procedures"),
        ("Study SQL", "Practice complex queries"),
        ("Plan meal prep", "Weekly meal planning"),
        ("Update resume website", "Add portfolio projects"),
        ("Learn Vue.js", "Study component system"),
        ("Fix bathroom tile", "Repair grout"),
        ("Organize garage", "Sort tools and equipment"),
        ("Update will", "Review legal documents"),
        ("Learn React Native", "Mobile app development"),
        ("Fix deck boards", "Replace worn planks"),
        ("Create cleaning schedule", "Weekly task planning"),
        ("Study cybersecurity", "Learn about threats"),
        ("Plan home renovation", "Budget and timeline"),
        ("Update social media", "Review privacy settings"),
        ("Learn MongoDB", "Study NoSQL databases"),
        ("Fix garden fence", "Repair damaged sections"),
        ("Organize basement", "Sort storage items"),
        ("Update medical records", "Compile health history"),
        ("Learn AWS Lambda", "Serverless computing"),
        ("Fix squeaky floor", "Address noisy boards"),
        ("Create emergency plan", "Family safety procedures"),
        ("Study machine learning", "Basic algorithms"),
        ("Plan retirement", "Review savings strategy"),
        ("Update phone apps", "Remove unused software"),
        ("Learn Docker Compose", "Container orchestration"),
        ("Fix ceiling fan", "Balance blades"),
        ("Organize attic", "Sort seasonal items"),
        ("Update car insurance", "Compare rates"),
        ("Learn Kubernetes", "Container management"),
        ("Fix screen door", "Replace mesh"),
        ("Create file backup", "Important document copies"),
        ("Study data structures", "Advanced concepts"),
        ("Plan home office", "Design workspace layout"),
        ("Update contact list", "Review phone numbers"),
        ("Learn GraphQL", "API query language"),
        ("Fix kitchen cabinet", "Adjust hinges"),
        ("Organize closet", "Sort clothing items"),
        ("Update virus protection", "Security software"),
        ("Learn Flutter", "Cross-platform development"),
        ("Fix bathroom sink", "Clear drain"),
        ("Create shopping list", "Weekly groceries"),
        ("Study system design", "Architecture patterns"),
        ("Plan fitness goals", "Set monthly targets")
    ]

    # Add all tasks to the recommender
    for title, description in tasks_list:
        recommender.add_task(title, description)

    # Test with various queries
    queries = [
        "technology", 
        # "home maintenance", 
        # "fitness", 
        # "learning",
        # "organization",
        # "programming",
        # "cleaning",
        "planning"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        relevant_tasks = recommender.find_relevant_tasks(query, limit=5)  # Increased limit to 5
        for task in relevant_tasks:
            print(f"- {task['title']}")


if __name__ == "__main__":
    main()
