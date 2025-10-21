// SPA frontend wired to backend without backend changes
let sessionId = localStorage.getItem('chatSessionId') || `session_${Math.random().toString(36).slice(2)}`;
localStorage.setItem('chatSessionId', sessionId);

// View map (filled after DOM ready)
const VIEWS = {};
let viewTitle, menuItems, suggestionsEl, chatMessagesEl, messageInputEl;

function api(path, options={}){
  const base = (window && window.API_BASE_URL) ? window.API_BASE_URL : '';
  return fetch(`${base}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
}

function renderSuggestions(){
  if (!suggestionsEl) return;
  const defaultQs = [
    'What is DataForge AI?',
    'What features does DataForge AI offer?',
    'How much does DataForge AI cost?',
    'How do I get started with DataForge AI?'
  ];
  suggestionsEl.innerHTML='';
  defaultQs.forEach(q=>{ const b=document.createElement('button'); b.textContent=q; b.onclick=()=>ask(q); suggestionsEl.appendChild(b); });
}

function switchView(name){
  if (!VIEWS[name]) return;
  Object.values(VIEWS).forEach(v => v && v.classList.add('hidden'));
  VIEWS[name].classList.remove('hidden');
  if (viewTitle) viewTitle.textContent = name[0].toUpperCase()+name.slice(1);
  if (name==='history') loadHistory();
  if (name==='analytics') loadAnalytics();
}

function addMessage(role, text, chatId=null){
  if (!chatMessagesEl) return;
  const row=document.createElement('div'); row.className=`message ${role}`;
  const bubble=document.createElement('div'); bubble.className='bubble'; bubble.textContent=text; row.appendChild(bubble);
  if(role==='assistant' && chatId){
    const fb=document.createElement('div'); fb.className='feedback';
    const up=document.createElement('button'); up.textContent='👍'; up.onclick=()=>feedback(chatId,1);
    const dn=document.createElement('button'); dn.textContent='👎'; dn.onclick=()=>feedback(chatId,0);
    fb.append(up,dn); bubble.appendChild(fb);
  }
  chatMessagesEl.appendChild(row); chatMessagesEl.scrollTop=chatMessagesEl.scrollHeight;
}

function typing(show){
  if (!chatMessagesEl) return;
  let el=document.getElementById('typing');
  if(show){ if(!el){ el=document.createElement('div'); el.id='typing'; el.className='message assistant'; el.innerHTML='<div class="bubble">Typing…</div>'; chatMessagesEl.appendChild(el);} }
  else if(el){ el.remove(); }
  chatMessagesEl.scrollTop=chatMessagesEl.scrollHeight;
}

async function send(){
  if (!messageInputEl) return;
  const text=messageInputEl.value.trim(); if(!text) return;
  addMessage('user', text); messageInputEl.value=''; typing(true);
  try{
    const res=await api('/api/chat',{method:'POST',body:JSON.stringify({message:text, session_id:sessionId})});
    if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json(); typing(false); addMessage('assistant', data.response, data.chat_id);
  }catch(e){ typing(false); addMessage('assistant','Sorry, there was an error. Please try again.'); }
}

async function feedback(chatId, rating){
  try{ await api('/api/feedback',{method:'POST',body:JSON.stringify({chat_id:chatId,rating})}); } catch(e){ /* no-op */ }
}

function ask(q){ if (!messageInputEl) return; messageInputEl.value=q; send(); }

async function loadHistory(){
  const list=document.getElementById('historyList'); if (!list) return; list.textContent='Loading…';
  try{
    const res=await api(`/api/chat-history?session_id=${encodeURIComponent(sessionId)}`,{method:'GET'});
    if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json();
    if(!data.history?.length){ list.textContent='No history yet.'; return; }
    list.innerHTML='';
    data.history.forEach(row=>{ const div=document.createElement('div'); div.className='row';
      const left=document.createElement('div'); left.textContent=row.query;
      const right=document.createElement('div'); right.style.opacity='.7'; right.textContent=row.formatted_time;
      div.append(left,right); list.appendChild(div); });
  }catch(e){ list.textContent='Failed to load history.'; }
}

async function loadAnalytics(){
  try{
    const res=await api('/api/analytics',{method:'GET'}); if(!res.ok) throw new Error('HTTP '+res.status);
    const data=await res.json();
    const cat=document.getElementById('categories'); if (cat){ cat.innerHTML=''; (data.categories||[]).forEach(c=>{ const b=document.createElement('span'); b.className='badge'; b.textContent=`${c.category}: ${c.count}`; cat.appendChild(b); }); }
    const fr=document.getElementById('fallbackRate'); if(fr) fr.textContent = `${(data.fallback_rate||0).toFixed(1)}%`;
    const as=document.getElementById('avgSatisfaction'); if(as){ const s=data.satisfaction; as.textContent = s? Number(s).toFixed(2): '—'; }
  }catch(e){ const ids=['categories','fallbackRate','avgSatisfaction']; ids.forEach(id=>{ const el=document.getElementById(id); if(el) el.textContent='—'; }); }
}

// DOM Ready wiring
document.addEventListener('DOMContentLoaded', () => {
  // Cache elements
  viewTitle = document.getElementById('viewTitle');
  menuItems = document.querySelectorAll('.menu-item');
  suggestionsEl = document.getElementById('suggestions');
  chatMessagesEl = document.getElementById('chatMessages');
  messageInputEl = document.getElementById('messageInput');

  VIEWS.chat = document.getElementById('chatView');
  VIEWS.history = document.getElementById('historyView');
  VIEWS.analytics = document.getElementById('analyticsView');

  // Menu wiring
  if (menuItems && menuItems.length){
    menuItems.forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
  }

  // Composer wiring
  const sendBtn=document.getElementById('sendBtn'); if (sendBtn) sendBtn.addEventListener('click', send);
  if (messageInputEl){
    messageInputEl.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }});
    messageInputEl.focus();
  }

  // Topbar & actions
  const newChatBtn=document.getElementById('newChatBtn'); if (newChatBtn) newChatBtn.addEventListener('click', ()=>{ if(chatMessagesEl) chatMessagesEl.innerHTML=''; });
  const refreshBtn=document.getElementById('refreshBtn'); if (refreshBtn) refreshBtn.addEventListener('click', ()=>{ if(VIEWS.analytics && !VIEWS.analytics.classList.contains('hidden')) loadAnalytics(); else if(VIEWS.history && !VIEWS.history.classList.contains('hidden')) loadHistory(); });

  // Suggestions and default view
  renderSuggestions();
  switchView('chat');
});
