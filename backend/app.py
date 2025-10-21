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
# Enable CORS for all routes
CORS(app, origins=['*'], supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "dataforge-support-secret-key")

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
                f.write("""# DataForge AI Overview

DataForge AI is a comprehensive data analytics and machine learning platform that empowers businesses to transform raw data into actionable insights without requiring deep technical expertise. Our cloud-based solution combines powerful data processing capabilities with intuitive visualization tools and automated AI model development.

## Core Capabilities

- **Data Integration**: Connect to 100+ data sources with our pre-built connectors
- **Automated Data Preparation**: Clean, transform, and enrich your data without coding
- **AI Model Builder**: Create and deploy machine learning models with a no-code interface
- **Interactive Dashboards**: Build stunning visualizations with our drag-and-drop designer
- **Predictive Analytics**: Forecast trends and detect anomalies automatically
- **Collaboration Tools**: Share insights and models across your organization

DataForge AI is designed for business analysts, data scientists, and decision-makers who need to leverage the power of AI without the complexity of traditional data science workflows.""")
    
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
    context = "You are an AI assistant for DataForge AI, a SaaS platform for data analytics and machine learning.\n\n"
    for topic, content in knowledge_base.items():
        context += f"# {topic}\n{content}\n\n"
    return context

# Function to categorize query
def categorize_query(query):
    categories = {
        "product": ["what is", "dataforge", "overview", "about", "platform"],
        "features": ["features", "capabilities", "integration", "dashboard", "analytics", "ai", "models"],
        "pricing": ["pricing", "cost", "subscription", "plan", "tier", "free", "trial"],
        "use_cases": ["use case", "example", "industry", "business", "company", "scenario"],
        "technical": ["technical", "api", "integration", "security", "data", "model", "algorithm"],
        "support": ["help", "support", "contact", "assistance", "troubleshoot"]
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
                "HTTP-Referer": "https://dataforge.ai",
                "X-Title": "DataForge AI Support"
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
            "product": "DataForge AI is a comprehensive data analytics and machine learning platform that empowers businesses to transform raw data into actionable insights without requiring deep technical expertise.",
            "features": "DataForge AI offers data integration with 100+ sources, automated data preparation, AI model building, interactive dashboards, predictive analytics, and collaboration tools.",
            "pricing": "DataForge AI offers three pricing tiers: Starter ($49/month), Professional ($149/month), and Enterprise (custom pricing). All plans include a 14-day free trial.",
            "use_cases": "DataForge AI is used for sales forecasting, customer segmentation, inventory optimization, predictive maintenance, and marketing campaign analysis across various industries.",
            "technical": "DataForge AI provides REST APIs, webhooks, SSO integration, and enterprise-grade security with SOC 2 Type II compliance.",
            "support": "DataForge AI offers 24/7 support via chat, email, and phone for all paid plans. Our knowledge base and community forum are available to all users."
        }
        
        query_lower = query.lower()
        for category, keywords in {
            "product": ["dataforge", "what is", "about", "overview"],
            "features": ["features", "capabilities", "integration", "dashboard"],
            "pricing": ["pricing", "cost", "subscription", "plan", "tier"],
            "use_cases": ["use case", "example", "industry", "business"],
            "technical": ["technical", "api", "integration", "security"],
            "support": ["help", "support", "contact", "assistance"]
        }.items():
            if any(keyword in query_lower for keyword in keywords):
                return fallback_responses[category], True
        
        return "I'm sorry, I'm having trouble processing your request. Please try again or contact our support team at support@dataforge.ai.", True

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

@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get chat history for the session
    cursor.execute("""
        SELECT id, query, response, category, is_fallback, satisfaction, 
               datetime(timestamp, 'localtime') as formatted_time
        FROM chat_analytics 
        WHERE session_id = ? 
        ORDER BY timestamp DESC
    """, (session_id,))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'session_id': session_id,
        'history': history
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
