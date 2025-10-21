from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os, re, sqlite3
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# ------------------ Config ------------------
load_dotenv()
app = Flask(__name__)
CORS(app, origins=['*'], supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY', 'dataforge-support-secret-key')

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise RuntimeError('OPENROUTER_API_KEY is not set')

client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=OPENROUTER_API_KEY,
    http_client=httpx.Client(proxies=None, timeout=60),
)

# ------------------ DB ------------------

def get_db():
    conn = sqlite3.connect('analytics.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_analytics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT,
      query TEXT,
      response TEXT,
      category TEXT,
      satisfaction INTEGER,
      is_fallback INTEGER DEFAULT 0,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit(); conn.close()

init_db()

# ------------------ KB ------------------

def load_kb():
    kb_dir = 'knowledge_base'
    os.makedirs(kb_dir, exist_ok=True)
    kb = {}
    for name in os.listdir(kb_dir):
        if name.endswith('.md'):
            path = os.path.join(kb_dir, name)
            with open(path, 'r', encoding='utf-8') as f:
                kb[name[:-3]] = f.read()
    return kb

KB = load_kb()
KB_KEYS = list(KB.keys())

# Normalize and tokenize query/content for better overlap
_WORD_RE = re.compile(r"[a-z0-9]+")
STOP = set(['the','a','an','is','are','and','or','to','of','for','with','on','in','how','what','does','do','i','you','we'])

def tokenize(text: str):
    return [w for w in _WORD_RE.findall(text.lower()) if w not in STOP]

# Improved retrieval: Jaccard similarity with title boost

def retrieve(query: str, top_n: int = 3) -> str:
    q_tokens = set(tokenize(query))
    scored = []
    for key, content in KB.items():
        c_tokens = set(tokenize(content))
        inter = len(q_tokens & c_tokens)
        union = len(q_tokens | c_tokens) or 1
        jacc = inter / union
        # Title boost if any query word appears in the topic key
        title_boost = 0.1 if any(t in key.lower() for t in q_tokens) else 0.0
        score = jacc + title_boost
        scored.append((score, key, content))
    scored.sort(reverse=True)
    top = [item for item in scored if item[0] > 0][:top_n]
    if not top:
        # if no overlap at all, still give the first N topics to avoid empty context
        sel = KB_KEYS[:top_n]
        return '\n\n'.join(f"### {k}\n{KB[k]}" for k in sel)
    return '\n\n'.join(f"### {k}\n{content}" for _, k, content in top)

# Category hint

def categorize(q: str) -> str:
    table = {
        'product': ['overview','about','platform','dataforge'],
        'features': ['feature','capabilities','integration','dashboard','model','models','ai','predictive','realtime','real','time','export'],
        'pricing': ['pricing','price','cost','plan','tier','trial','billing'],
        'getting_started': ['getting','started','setup','onboarding','connect','create','first'],
        'api': ['api','endpoint','rest','webhook','docs','documentation'],
        'security': ['security','compliance','soc','gdpr','encryption'],
        'support': ['support','contact','email','help']
    }
    l = tokenize(q)
    for cat, keys in table.items():
        if any(k in l for k in keys):
            return cat
    return 'other'

SYSTEM_PREFIX = (
  "You are the official customer support assistant for DataForge AI. "
  "Use ONLY the provided Context to answer. If the answer isn’t in Context, reply: "
  "'I don’t have that in my documentation. Please contact support.'"
)

# ------------------ LLM ------------------

def llm_answer(query: str, history: list):
    context = retrieve(query, top_n=3)
    messages = [
        { 'role': 'system', 'content': f"{SYSTEM_PREFIX}\n\nContext:\n{context}" },
        { 'role': 'user', 'content': f"Category: {categorize(query)}" },
    ]
    for m in (history or [])[-4:]:
        messages.append({ 'role': 'user' if m.get('type')=='user' else 'assistant', 'content': m.get('content','') })
    messages.append({ 'role': 'user', 'content': query })

    try:
        res = client.chat.completions.create(
            model='deepseek/deepseek-v3:free',
            messages=messages,
            max_tokens=600,
            temperature=0.2,
            frequency_penalty=0.2,
            presence_penalty=0,
            extra_headers={ 'HTTP-Referer': 'https://dataforge.ai', 'X-Title': 'DataForge AI Support' }
        )
        txt = res.choices[0].message.content
        return txt, 0
    except Exception as e:
        print('OpenRouter error:', e)
        # fallback varies per category to avoid identical replies
        cat = categorize(query)
        fb = {
          'getting_started': "I don’t have setup details in my documentation. Please contact support.",
          'pricing': "Pricing details aren’t in my documentation. Please contact sales or support.",
          'features': "Feature specifics aren’t listed in my documentation. Please contact support.",
          'api': "API details aren’t available in my documentation. Please contact support.",
          'security': "Security/compliance details aren’t available in my documentation. Please contact support.",
          'product': "I don’t have a product overview in my documentation. Please contact support.",
          'other': "I don’t have that in my documentation. Please contact support."
        }
        return fb.get(cat, fb['other']), 1

# ------------------ API ------------------

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    query = (data.get('message') or '').strip()
    session_id = data.get('session_id', request.remote_addr)

    if 'conversation' not in session:
        session['conversation'] = []
    if query:
        session['conversation'].append({ 'type': 'user', 'content': query })
        if len(session['conversation']) > 10:
            session['conversation'] = session['conversation'][-10:]

    response, is_fallback = llm_answer(query, session['conversation'])
    session['conversation'].append({ 'type': 'assistant', 'content': response })

    conn = get_db(); c = conn.cursor()
    c.execute(
      "INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?,?,?,?,?)",
      (session_id, query, response, categorize(query), is_fallback)
    )
    chat_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({ 'response': response, 'chat_id': chat_id })

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.json or {}
    chat_id = data.get('chat_id'); rating = data.get('rating')
    if not chat_id or rating not in [0,1]:
        return jsonify({ 'error': 'Invalid parameters' }), 400
    conn = get_db(); c = conn.cursor()
    c.execute('UPDATE chat_analytics SET satisfaction=? WHERE id=?', (rating, chat_id))
    conn.commit(); conn.close()
    return jsonify({ 'success': True })

@app.route('/api/analytics', methods=['GET'])
def analytics():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT category, COUNT(*) as count FROM chat_analytics GROUP BY category')
    categories = [dict(r) for r in c.fetchall()]
    c.execute('SELECT COUNT(*) as total, SUM(is_fallback) as fallbacks FROM chat_analytics')
    row = dict(c.fetchone()); fallback_rate = (row['fallbacks'] or 0)/(row['total'] or 1)*100
    c.execute('SELECT AVG(satisfaction) as avg_satisfaction FROM chat_analytics WHERE satisfaction IS NOT NULL')
    sat = dict(c.fetchone()); conn.close()
    return jsonify({ 'categories': categories, 'fallback_rate': fallback_rate, 'satisfaction': sat['avg_satisfaction'] })

@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({ 'error': 'Session ID is required' }), 400
    conn = get_db(); c = conn.cursor()
    c.execute('''
      SELECT id, query, response, category, is_fallback, satisfaction,
             datetime(timestamp, 'localtime') as formatted_time
      FROM chat_analytics WHERE session_id = ? ORDER BY timestamp DESC
    ''', (session_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({ 'session_id': session_id, 'history': rows })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
