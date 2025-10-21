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
# Enable CORS for all routes (lock down origins in production)
CORS(app, origins=['*'], supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "dataforge-support-secret-key")

# Clear any proxy environment variables that might be causing issues
for var in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','NO_PROXY','no_proxy']:
    os.environ.pop(var, None)

# Initialize OpenRouter client with OpenAI SDK
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    http_client=httpx.Client(proxies=None, timeout=30)  # Explicitly disable proxies and set timeout
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
    os.makedirs(knowledge_base_dir, exist_ok=True)

    # If empty, seed with a minimal file (only once)
    if len([f for f in os.listdir(knowledge_base_dir) if f.endswith('.md')]) == 0:
        with open(os.path.join(knowledge_base_dir, "product-overview.md"), "w") as f:
            f.write("""# DataForge AI Overview\n\nProvide a concise overview here.""")

    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith(".md"):
            path = os.path.join(knowledge_base_dir, filename)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                knowledge_base[filename[:-3]] = content

    print(f"Loaded {len(knowledge_base)} knowledge base files: {', '.join(sorted(knowledge_base.keys()))}")
    return knowledge_base

knowledge_base = load_knowledge_base()

# Build system prompt from knowledge base with clear instructions

def create_knowledge_context():
    parts = [
        "You are the official customer support assistant for DataForge AI.",
        "Answer strictly using the knowledge base below. If the answer is not present, say you don't know and suggest contacting support.",
        "Format with short paragraphs and bullet points when helpful.",
        "Knowledge Base:"
    ]
    for topic, content in knowledge_base.items():
        parts.append(f"\n### {topic}\n{content}\n")
    return "\n".join(parts)

# Simple keyword-based router (optional hinting for the model)

def categorize_query(query: str) -> str:
    categories = {
        "product": ["what is","dataforge","overview","about","platform"],
        "features": ["features","capabilities","integration","dashboard","analytics","ai","models"],
        "pricing": ["pricing","cost","subscription","plan","tier","free","trial","price"],
        "use_cases": ["use case","example","industry","business","scenario","how to use"],
        "technical": ["technical","api","integration","security","data","model","algorithm","compliance"],
        "support": ["help","support","contact","assistance","troubleshoot","email"]
    }
    q = query.lower()
    for cat, keys in categories.items():
        if any(k in q for k in keys):
            return cat
    return "other"

# Fallback answers (only used if API fails)
FALLBACKS = {
    "product": "DataForge AI is a data analytics and ML platform for turning data into insights.",
    "features": "Key features: data integration, data prep, AI model builder, dashboards, predictive analytics, collaboration.",
    "pricing": "Plans include Starter, Professional, and Enterprise. Contact sales for exact pricing.",
    "use_cases": "Common use cases: sales forecasting, segmentation, inventory optimization, predictive maintenance, campaign analysis.",
    "technical": "Provides REST APIs, webhooks, SSO, and enterprise-grade security.",
    "support": "24/7 support for paid plans; knowledge base and community are available to all users.",
    "other": "Please clarify your question or contact support if you need specific details."
}

# Call OpenRouter (DeepSeek) with explicit grounding and temperature control

def get_ai_response(query, conversation_history):
    kb_context = create_knowledge_context()

    # Construct messages: keep conversation short and relevant
    messages = [
        {"role": "system", "content": kb_context},
        {"role": "user", "content": f"Question category hint: {categorize_query(query)}"}
    ]

    # Include only the last 6 turns (to avoid repetition bias)
    history_tail = conversation_history[-6:] if conversation_history else []
    for msg in history_tail:
        role = "user" if msg.get("type") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": query})

    try:
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://dataforge.ai", "X-Title": "DataForge AI Support"},
            model="deepseek/deepseek-v3-base:free",
            messages=messages,
            max_tokens=500,
            temperature=0.2,          # lower temp to reduce generic answers
            presence_penalty=0,       # avoid random topic shifts
            frequency_penalty=0.2     # reduce repetition
        )
        text = completion.choices[0].message.content
        return text, False
    except Exception as e:
        print(f"LLM error: {e}")
        # fallback path
        cat = categorize_query(query)
        return FALLBACKS.get(cat, FALLBACKS['other']), True

# Routes remain the same

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    query = data.get('message', '').strip()
    session_id = data.get('session_id', request.remote_addr)

    if 'conversation' not in session:
        session['conversation'] = []

    if query:
        session['conversation'].append({"type": "user", "content": query})
        if len(session['conversation']) > 10:
            session['conversation'] = session['conversation'][-10:]

    category = categorize_query(query)
    response, is_fallback = get_ai_response(query, session['conversation'])

    session['conversation'].append({"type": "assistant", "content": response})

    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?, ?, ?, ?, ?)",
        (session_id, query, response, category, is_fallback)
    )
    chat_id = cursor.lastrowid
    conn.commit(); conn.close()

    return jsonify({ 'response': response, 'chat_id': chat_id })

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.json or {}
    chat_id = data.get('chat_id'); rating = data.get('rating')
    if not chat_id or rating not in [0,1]:
        return jsonify({'error':'Invalid parameters'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE chat_analytics SET satisfaction = ? WHERE id = ?", (rating, chat_id))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/analytics', methods=['GET'])
def analytics():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) as count FROM chat_analytics GROUP BY category")
    categories = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) as total, SUM(is_fallback) as fallbacks FROM chat_analytics")
    row = dict(cursor.fetchone()); fallback_rate = (row['fallbacks'] or 0) / (row['total'] or 1) * 100
    cursor.execute("SELECT AVG(satisfaction) as avg_satisfaction FROM chat_analytics WHERE satisfaction IS NOT NULL")
    sat = dict(cursor.fetchone())
    conn.close()
    return jsonify({ 'categories': categories, 'fallback_rate': fallback_rate, 'satisfaction': sat['avg_satisfaction'] })

@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error':'Session ID is required'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT id, query, response, category, is_fallback, satisfaction,
               datetime(timestamp, 'localtime') as formatted_time
        FROM chat_analytics WHERE session_id = ? ORDER BY timestamp DESC
    """, (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({ 'session_id': session_id, 'history': rows })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
