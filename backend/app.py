from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import json
import datetime
import sqlite3
import markdown
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "cloudflow-analytics-secret-key")

# Initialize OpenRouter API key for DeepSeek
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set. Please set it in your .env file.")

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
                f.write("""# CloudFlow Analytics Overview

CloudFlow Analytics is a comprehensive data analytics platform designed to help businesses of all sizes transform their raw data into actionable insights. Our cloud-based solution combines powerful data processing capabilities with intuitive visualization tools and AI-powered analytics.

## Core Capabilities

- **Connect** to over 50 data sources with our pre-built connectors
- **Process** data through our no-code transformation pipeline
- **Visualize** insights with our interactive dashboard builder
- **Discover** hidden patterns with our AI Insights Engine
- **Collaborate** with team members through sharing and commenting features
- **Secure** your data with enterprise-grade security measures

CloudFlow Analytics empowers your team to make data-driven decisions without requiring advanced technical skills.""")
    
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
    context = "You are an AI assistant for CloudFlow Analytics, a SaaS platform for data analytics.\n\n"
    for topic, content in knowledge_base.items():
        context += f"# {topic}\n{content}\n\n"
    return context

# Function to categorize query
def categorize_query(query):
    categories = {
        "product": ["what is", "product", "cloudflow", "overview", "features"],
        "pricing": ["price", "cost", "subscription", "plan", "tier", "billing"],
        "technical": ["api", "integration", "connect", "data source", "dashboard"],
        "account": ["login", "account", "password", "sign up", "registration"],
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

# Function to get response from DeepSeek via OpenRouter
def get_ai_response(query, conversation_history):
    try:
        knowledge_context = create_knowledge_context()
        
        # Prepare messages including system context and conversation history
        messages = [
            {"role": "system", "content": knowledge_context}
        ]
        
        # Add conversation history (limited to last few exchanges)
        for msg in conversation_history:
            messages.append({"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]})
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Make request to OpenRouter API with DeepSeek model
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://cloudflow-analytics.com",  # Replace with your actual domain
            "X-Title": "CloudFlow Analytics Support"  # Your app name
        }
        
        data = {
            "model": "deepseek/deepseek-chat-v3-0324:free",  # Free version of DeepSeek V3
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7,
        }
        
        print(f"Sending request to OpenRouter API - Query: '{query}'")
        print(f"Messages context length: {len(str(messages))} characters")
        
        response = requests.post(url, headers=headers, json=data)
        
        print(f"OpenRouter API Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"OpenRouter API Response (first 100 chars): {str(result)[:100]}...")
            return result["choices"][0]["message"]["content"], False
        else:
            print(f"Error from OpenRouter API: {response.text}")
            
            # Try with a simpler request as fallback
            if len(messages) > 2:
                print("Retrying with simplified context...")
                simplified_messages = [
                    {"role": "system", "content": "You are an AI assistant for CloudFlow Analytics, a SaaS platform for data analytics."},
                    {"role": "user", "content": query}
                ]
                
                data["messages"] = simplified_messages
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Simplified Response (first 100 chars): {str(result)[:100]}...")
                    return result["choices"][0]["message"]["content"], False
            
            # If still failing, return error message
            return "I'm sorry, I'm having trouble processing your request. Please try again later.", True
            
    except Exception as e:
        print(f"Error getting AI response: {e}")
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
