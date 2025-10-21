from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
import httpx

load_dotenv()
app = Flask(__name__)
CORS(app, origins=['*'], supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "dataforge-support-secret-key")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY, http_client=httpx.Client(proxies=None, timeout=30))

# --- DB helpers ---

def get_db_connection():
    conn = sqlite3.connect('analytics.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        query TEXT,
        response TEXT,
        category TEXT,
        satisfaction INTEGER,
        is_fallback BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit(); conn.close()

init_db()

# --- Knowledge base loader with per-topic map ---

def load_knowledge_base():
    kb = {}
    kb_dir = "knowledge_base"
    os.makedirs(kb_dir, exist_ok=True)
    for name in os.listdir(kb_dir):
        if name.endswith(".md"):
            with open(os.path.join(kb_dir, name), "r", encoding="utf-8") as f:
                kb[name[:-3].lower()] = f.read()
    print(f"KB loaded topics: {', '.join(sorted(kb.keys()))}")
    return kb

KB = load_knowledge_base()

# Lightweight retrieval: pick top-N relevant md chunks by keyword overlap

def retrieve_context(query: str, top_n: int = 3) -> str:
    q = query.lower()
    scored = []
    for topic, content in KB.items():
        score = 0
        for token in q.split():
            if token and token in content.lower():
                score += 1
        if score:
            scored.append((score, topic, content))
    scored.sort(reverse=True)
    selected = scored[:top_n] if scored else [(0, t, c) for t, c in list(KB.items())[:top_n]]
    parts = [f"### {t}\n{c}" for _, t, c in selected]
    return "\n\n".join(parts)

# Category hint

def categorize(query: str) -> str:
    table = {
        "product":["what","overview","about","dataforge"],
        "pricing":["price","pricing","cost","plan","tier","trial"],
        "features":["feature","capabilities","integration","dashboard","model","ai","predictive"],
        "support":["support","contact","help","email"],
        "technical":["api","security","compliance","export","real-time","realtime"]
    }
    q=query.lower()
    for k,keys in table.items():
        if any(key in q for key in keys):
            return k
    return "other"

SYSTEM_PREFIX = (
    "You are DataForge AI's official support assistant. Answer ONLY using the provided context. "
    "If the answer is not in context, say you don't know and suggest contacting support."
)

# --- LLM call grounded with retrieved context ---

def answer(query: str, history: list):
    context = retrieve_context(query, top_n=3)
    messages = [
        {"role":"system","content": f"{SYSTEM_PREFIX}\n\nContext:\n{context}"},
        {"role":"user","content": f"Category: {categorize(query)}"},
    ]
    # include only last 4 turns to reduce repetition
    for m in (history or [])[-4:]:
        messages.append({"role":"user" if m.get('type')=='user' else 'assistant', "content": m.get('content','')})
    messages.append({"role":"user","content": query})

    try:
        resp = client.chat.completions.create(
            model="deepseek/deepseek-v3-base:free",
            messages=messages,
            max_tokens=500,
            temperature=0.15,
            frequency_penalty=0.3,
        )
        return resp.choices[0].message.content, False
    except Exception as e:
        print("LLM error:", e)
        # conservative fallback different per category
        cat = categorize(query)
        if cat=="pricing":
            return "Pricing details vary by plan. Please see pricing-plans in the docs or contact sales.", True
        if cat=="features":
            return "Key features include data integration, preparation, model builder, dashboards, and predictive analytics.", True
        if cat=="technical":
            return "Technical docs cover APIs, security, exports, and compliance.", True
        if cat=="support":
            return "Reach support via the contact-support page or email.", True
        return "Please clarify your question or check the documentation sections.", True

# --- API routes (unchanged contract) ---

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    query = (data.get('message') or '').strip()
    session_id = data.get('session_id', request.remote_addr)
    if 'conversation' not in session:
        session['conversation'] = []
    if query:
        session['conversation'].append({"type":"user","content":query})
        if len(session['conversation'])>10:
            session['conversation'] = session['conversation'][-10:]
    response, is_fallback = answer(query, session['conversation'])
    session['conversation'].append({"type":"assistant","content":response})

    conn = get_db_connection(); c = conn.cursor()
    c.execute("INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?,?,?,?,?)",
              (session_id, query, response, categorize(query), is_fallback))
    chat_id = c.lastrowid; conn.commit(); conn.close()
    return jsonify({'response': response, 'chat_id': chat_id})

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.json or {}
    chat_id = data.get('chat_id'); rating = data.get('rating')
    if not chat_id or rating not in [0,1]:
        return jsonify({'error':'Invalid parameters'}), 400
    conn=get_db_connection(); c=conn.cursor(); c.execute("UPDATE chat_analytics SET satisfaction=? WHERE id=?", (rating, chat_id)); conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/analytics', methods=['GET'])
def analytics():
    conn=get_db_connection(); c=conn.cursor()
    c.execute("SELECT category, COUNT(*) as count FROM chat_analytics GROUP BY category"); categories=[dict(r) for r in c.fetchall()]
    c.execute("SELECT COUNT(*) as total, SUM(is_fallback) as fallbacks FROM chat_analytics"); row=dict(c.fetchone()); fallback_rate=(row['fallbacks'] or 0)/(row['total'] or 1)*100
    c.execute("SELECT AVG(satisfaction) as avg_satisfaction FROM chat_analytics WHERE satisfaction IS NOT NULL"); sat=dict(c.fetchone()); conn.close()
    return jsonify({'categories':categories,'fallback_rate':fallback_rate,'satisfaction':sat['avg_satisfaction']})

@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error':'Session ID is required'}), 400
    conn=get_db_connection(); c=conn.cursor()
    c.execute("""
      SELECT id, query, response, category, is_fallback, satisfaction, datetime(timestamp,'localtime') as formatted_time
      FROM chat_analytics WHERE session_id=? ORDER BY timestamp DESC
    """, (session_id,))
    rows=[dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'session_id':session_id,'history':rows})

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
