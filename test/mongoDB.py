from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["data"]
collection = db["mcq_questions"]

# AI Questions
ai_questions = [
    {
        "question": "What does AI stand for?",
        "options": ["Artificial Intelligence", "Automatic Interface", "Advanced Internet", "Autonomous Interaction"],
        "answer": "Artificial Intelligence",
        "category": "ai"
    },
    {
        "question": "Which of the following is an application of AI?",
        "options": ["Speech Recognition", "Cable TV", "Hard Disk", "Mechanical Mouse"],
        "answer": "Speech Recognition",
        "category": "ai"
    },
    {
        "question": "Which type of AI can perform tasks without human input?",
        "options": ["Strong AI", "Weak AI", "Narrow AI", "Soft AI"],
        "answer": "Strong AI",
        "category": "ai"
    },
    {
        "question": "What is the full form of NLP?",
        "options": ["Natural Language Processing", "Neural Learning Program", "Network Level Protocol", "Natural Learning Project"],
        "answer": "Natural Language Processing",
        "category": "ai"
    },
    {
        "question": "Which of the following is an AI assistant?",
        "options": ["Siri", "Microsoft Word", "Google Docs", "Notepad"],
        "answer": "Siri",
        "category": "ai"
    }
]

# ML Questions
ml_questions = [
    {
        "question": "What is Machine Learning?",
        "options": ["Learning from data", "Learning how to code", "Learning about machines", "Learning by heart"],
        "answer": "Learning from data",
        "category": "ml"
    },
    {
        "question": "Which language is widely used in ML?",
        "options": ["Python", "HTML", "CSS", "PHP"],
        "answer": "Python",
        "category": "ml"
    },
    {
        "question": "What type of ML involves labeled data?",
        "options": ["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Deep Learning"],
        "answer": "Supervised Learning",
        "category": "ml"
    },
    {
        "question": "Which of the following is an ML algorithm?",
        "options": ["Linear Regression", "Bootstrap", "Flask", "React"],
        "answer": "Linear Regression",
        "category": "ml"
    },
    {
        "question": "What is overfitting in ML?",
        "options": ["Model fits training data too well", "Model fits test data poorly", "Model fits randomly", "Model doesn't train"],
        "answer": "Model fits training data too well",
        "category": "ml"
    }
]

# Insert both sets into MongoDB
collection.insert_many(ai_questions + ml_questions)

print("✅ AI and ML questions inserted successfully.")
