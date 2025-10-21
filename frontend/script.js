// Enhanced single-page interactions for chat, history and analytics
let sessionId = localStorage.getItem('chatSessionId') || `session_${Math.random().toString(36).slice(2)}`;
localStorage.setItem('chatSessionId', sessionId);

const VIEWS = {
  chat: document.getElementById('chatView'),
  history: document.getElementById('historyView'),
  analytics: document.getElementById('analyticsView')
};

const viewTitle = document.getElementById('viewTitle');
const menuItems = document.querySelectorAll('.menu-item');
const suggestions = document.getElementById('suggestions');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');

function api(path, options={}){
  const base = (window && window.API_BASE_URL) ? window.API_BASE_URL : '';
  return fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
}

// Navigation
menuItems.forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
function switchView(name){
  Object.values(VIEWS).forEach(v => v.classList.add('hidden'));
  VIEWS[name].classList.remove('hidden');
  menuItems.forEach(m => m.classList.toggle('active', m.dataset.view===name));
  viewTitle.textContent = name[0].toUpperCase()+name.slice(1);
  if(name==='history') loadHistory();
  if(name==='analytics') loadAnalytics();
}

// Suggestions
const defaultQs = [
  'What is DataForge AI?',
  'What features does DataForge AI offer?',
  'How much does DataForge AI cost?',
  'How do I get started with DataForge AI?'
];
function renderSuggestions(){
  suggestions.innerHTML = '';
  defaultQs.forEach(q=>{
    const b=document.createElement('button'); b.textContent=q; b.onclick=()=>ask(q); suggestions.appendChild(b);
  })
}

// Chat
function addMessage(role, text, chatId=null){
  const row=document.createElement('div'); row.className=`message ${role}`;
  const bubble=document.createElement('div'); bubble.className='bubble'; bubble.textContent=text; row.appendChild(bubble);
  if(role==='assistant' && chatId){
    const fb=document.createElement('div'); fb.className='feedback';
    const up=document.createElement('button'); up.textContent='👍'; up.onclick=()=>feedback(chatId,1);
    const dn=document.createElement('button'); dn.textContent='👎'; dn.onclick=()=>feedback(chatId,0);
    fb.append(up,dn); bubble.appendChild(fb);
  }
  chatMessages.appendChild(row); chatMessages.scrollTop=chatMessages.scrollHeight;
}

function typing(show){
  let el=document.getElementById('typing');
  if(show){
    if(!el){ el=document.createElement('div'); el.id='typing'; el.className='message assistant'; el.innerHTML='<div class="bubble">Typing…</div>'; chatMessages.appendChild(el);} 
  } else if(el){ el.remove(); }
  chatMessages.scrollTop=chatMessages.scrollHeight;
}

async function send(){
  const text=messageInput.value.trim(); if(!text) return;
  addMessage('user', text); messageInput.value=''; typing(true);
  try{
    const res=await api('/api/chat',{method:'POST',body:JSON.stringify({message:text, session_id:sessionId})});
    if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json(); typing(false); addMessage('assistant', data.response, data.chat_id);
  }catch(e){ typing(false); addMessage('assistant','Sorry, there was an error. Please try again.'); }
}

async function feedback(chatId, rating){
  try{ await api('/api/feedback',{method:'POST',body:JSON.stringify({chat_id:chatId,rating})}); }
  catch(e){ /* no-op */ }
}

function ask(q){ messageInput.value=q; send(); }

// History
async function loadHistory(){
  const list=document.getElementById('historyList'); list.innerHTML='Loading…';
  try{
    const url=`/api/chat-history?session_id=${encodeURIComponent(sessionId)}`;
    const res=await api(url,{method:'GET'}); if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json();
    if(!data.history?.length){ list.textContent='No history yet.'; return; }
    list.innerHTML='';
    data.history.forEach(row=>{
      const div=document.createElement('div'); div.className='row';
      const left=document.createElement('div'); left.textContent=row.query;
      const right=document.createElement('div'); right.style.opacity='.7'; right.textContent=row.formatted_time;
      div.append(left,right); list.appendChild(div);
    });
  }catch(e){ list.textContent='Failed to load history.'; }
}

// Analytics
async function loadAnalytics(){
  try{
    const res=await api('/api/analytics',{method:'GET'}); if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json();
    const cat=document.getElementById('categories'); cat.innerHTML='';
    (data.categories||[]).forEach(c=>{ const b=document.createElement('span'); b.className='badge'; b.textContent=`${c.category}: ${c.count}`; cat.appendChild(b); });
    document.getElementById('fallbackRate').textContent = `${(data.fallback_rate||0).toFixed(1)}%`;
    const s = data.satisfaction; document.getElementById('avgSatisfaction').textContent = s? Number(s).toFixed(2): '—';
  }catch(e){
    document.getElementById('categories').textContent='—';
    document.getElementById('fallbackRate').textContent='—';
    document.getElementById('avgSatisfaction').textContent='—';
  }
}

// Wire up
document.getElementById('sendBtn').addEventListener('click', send);
messageInput.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }});
document.getElementById('newChatBtn').addEventListener('click', ()=>{ chatMessages.innerHTML=''; });
document.getElementById('refreshBtn').addEventListener('click', ()=>{ if(!VIEWS.analytics.classList.contains('hidden')) loadAnalytics(); else if(!VIEWS.history.classList.contains('hidden')) loadHistory(); });
renderSuggestions();
switchView('chat');
