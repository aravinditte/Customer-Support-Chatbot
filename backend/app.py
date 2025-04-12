from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import json
import datetime
import sqlite3
import markdown
from openai import OpenAI
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "vahan-support-secret-key")

# Clear any proxy environment variables that might be causing issues
proxy_env_vars = [
    'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
    'NO_PROXY', 'no_proxy'
]
for var in proxy_env_vars:
    if var in os.environ:
        del os.environ[var]

# Initialize OpenRouter client with OpenAI SDK
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

# Initialize client with custom HTTP client to avoid proxy issues
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    http_client=httpx.Client(proxies=None)  # Explicitly disable proxies
)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('analytics.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        query TEXT,
        response TEXT,
        category TEXT,
        satisfaction INTEGER,
        is_fallback BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Load knowledge base
def load_knowledge_base():
    knowledge_base = {}
    knowledge_base_dir = "knowledge_base"
    
    if not os.path.exists(knowledge_base_dir):
        os.makedirs(knowledge_base_dir)
        # Create a default knowledge file if none exists
        if len(os.listdir(knowledge_base_dir)) == 0:
            with open(os.path.join(knowledge_base_dir, "product-overview.md"), "w") as f:
                f.write("""# Vahan Overview

Vahan is an AI-enabled livelihood platform founded in 2016 and headquartered in Bangalore, Karnataka. The company harnesses state-of-the-art AI-driven chatbot technology to empower businesses to expand their blue-collar workforce through streamlined recruitment, payroll, and staffing processes.

## Core Capabilities

- **AI-Powered Recruitment**: Automate high-volume hiring of blue and grey collar workers
- **Nationwide Reach**: Source candidates from across India, from the northern hills to the southern shores
- **Payroll Management**: Comprehensive workforce staffing and payroll administration
- **Single Platform Solution**: Manage recruitment, payroll, and staffing from one streamlined interface
- **Strategic Partnerships**: Collaboration with Airtel for extensive hiring campaigns reaching 30 crore people

Vahan specializes in facilitating blue-collar worker recruitment for leading companies in India's gig economy, including Zomato, Swiggy, Flipkart, Uber, Shadowfax, Rapido, Zepto, Dunzo, and Delhivery.""")
    
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(knowledge_base_dir, filename)
            with open(file_path, 'r') as file:
                content = file.read()
                knowledge_base[filename[:-3]] = content
    
    print(f"Loaded {len(knowledge_base)} knowledge base files: {', '.join(knowledge_base.keys())}")
    return knowledge_base

knowledge_base = load_knowledge_base()

# Convert knowledge base to context for LLM
def create_knowledge_context():
    context = "You are an AI assistant for Vahan, an AI-enabled recruitment and staffing platform for blue-collar workers in India.\n\n"
    for topic, content in knowledge_base.items():
        context += f"# {topic}\n{content}\n\n"
    return context

# Function to categorize query
def categorize_query(query):
    categories = {
        "company": ["what is", "vahan", "overview", "about", "founded", "headquarters"],
        "recruitment": ["recruitment", "hiring", "candidates", "workers", "jobs", "positions"],
        "staffing": ["staffing", "payroll", "management", "workforce"],
        "technology": ["ai", "technology", "chatbot", "platform", "automation"],
        "programs": ["mitra", "program", "leader", "app"],
        "partnerships": ["partners", "companies", "zomato", "swiggy", "flipkart", "uber"]
    }
    
    query_lower = query.lower()
    for category, keywords in categories.items():
        if any(keyword in query_lower for keyword in keywords):
            return category
    
    return "other"

# Track analytics
def track_analytics(session_id, query, response, category, is_fallback):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?, ?, ?, ?, ?)",
        (session_id, query, response, category, is_fallback)
    )
    conn.commit()
    conn.close()

# Update satisfaction rating
def update_satisfaction(chat_id, rating):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE chat_analytics SET satisfaction = ? WHERE id = ?",
        (rating, chat_id)
    )
    conn.commit()
    conn.close()

# Function to get response using OpenAI client for OpenRouter
def get_ai_response(query, conversation_history):
    try:
        knowledge_context = create_knowledge_context()
        
        # Format messages for the API
        messages = [
            {"role": "system", "content": knowledge_context}
        ]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]})
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        print(f"Sending request to OpenRouter API - Query: '{query}'")
        
        # Make request using OpenAI client
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://vahan.co",
                "X-Title": "Vahan Support"
            },
            model="deepseek/deepseek-v3-base:free",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        response_text = completion.choices[0].message.content
        print(f"Response received: {response_text[:100]}...")
        return response_text, False
            
    except Exception as e:
        print(f"Error getting AI response: {e}")
        
        # Fallback to hardcoded responses if API fails
        fallback_responses = {
            "company": "Vahan is an AI-enabled recruitment and staffing platform founded in 2016 and headquartered in Bangalore. It specializes in blue-collar workforce recruitment for companies like Zomato, Swiggy, and Flipkart.",
            "recruitment": "Vahan offers AI-powered recruitment for blue-collar workers, processing over 20,000 placements per month with an average fulfillment time of just 2-3 days.",
            "staffing": "Vahan's workforce staffing solution includes end-to-end management, payroll administration, compliance management, and workforce analytics.",
            "technology": "Vahan uses advanced AI chatbots and machine learning algorithms to automate the recruitment process, with mobile-first design optimized for blue-collar job seekers.",
            "programs": "Vahan offers the Mitra program, an all-in-one delivery job search app, and the Mitra Leader program for creating leaders in recruitment.",
            "partnerships": "Vahan partners with major companies in India's gig economy, including Zomato, Swiggy, Flipkart, Uber, Shadowfax, Rapido, Zepto, Dunzo, and Delhivery."
        }
        
        query_lower = query.lower()
        for category, keywords in {
            "company": ["vahan", "company", "about", "founded"],
            "recruitment": ["recruitment", "hiring", "candidates"],
            "staffing": ["staffing", "payroll", "management"],
            "technology": ["ai", "technology", "chatbot"],
            "programs": ["mitra", "program", "app"],
            "partnerships": ["partners", "companies", "zomato"]
        }.items():
            if any(keyword in query_lower for keyword in keywords):
                return fallback_responses[category], True
        
        return "I'm sorry, I'm having trouble processing your request. Please try again or contact our support team.", True

# Routes
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('message', '')
    session_id = data.get('session_id', request.remote_addr)
    
    # Initialize session if it doesn't exist
    if 'conversation' not in session:
        session['conversation'] = []
    
    # Add query to conversation history
    session['conversation'].append({"type": "user", "content": query})
    
    # Limit conversation history to last 10 messages
    if len(session['conversation']) > 10:
        session['conversation'] = session['conversation'][-10:]
    
    # Categorize query
    category = categorize_query(query)
    
    # Get response from AI
    response, is_fallback = get_ai_response(query, session['conversation'])
    
    # Add response to conversation history
    session['conversation'].append({"type": "assistant", "content": response})
    
    # Track analytics
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?, ?, ?, ?, ?)",
        (session_id, query, response, category, is_fallback)
    )
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'response': response,
        'chat_id': chat_id
    })

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.json
    chat_id = data.get('chat_id')
    rating = data.get('rating')
    
    if not chat_id or rating not in [0, 1]:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    update_satisfaction(chat_id, rating)
    
    return jsonify({'success': True})

@app.route('/api/analytics', methods=['GET'])
def analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get category distribution
    cursor.execute("SELECT category, COUNT(*) as count FROM chat_analytics GROUP BY category")
    categories = [dict(row) for row in cursor.fetchall()]
    
    # Get fallback rate
    cursor.execute("SELECT COUNT(*) as total, SUM(is_fallback) as fallbacks FROM chat_analytics")
    fallback_stats = dict(cursor.fetchone())
    fallback_rate = (fallback_stats['fallbacks'] / fallback_stats['total']) * 100 if fallback_stats['total'] > 0 else 0
    
    # Get satisfaction rate
    cursor.execute("SELECT AVG(satisfaction) as avg_satisfaction FROM chat_analytics WHERE satisfaction IS NOT NULL")
    satisfaction = dict(cursor.fetchone())
    
    conn.close()
    
    return jsonify({
        'categories': categories,
        'fallback_rate': fallback_rate,
        'satisfaction': satisfaction['avg_satisfaction']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
