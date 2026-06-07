import re
import os

source_path = r"e:\project\pcos_hud_v5.html"
target_path = r"e:\project\src\pcos\ui\overlay_hud.html"

with open(source_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Remove desktop div cleanly
desktop_html = """<!-- DESKTOP -->
<div class="desktop">
  <div class="desk-code">
    <div class="code-sidebar">
      <div class="cs-item act"><svg viewBox="0 0 12 12"><rect x="2" y="1" width="8" height="10" rx="1"/></svg>auth.py</div>
      <div class="cs-item"><svg viewBox="0 0 12 12"><rect x="2" y="1" width="8" height="10" rx="1"/></svg>middleware.py</div>
      <div class="cs-item"><svg viewBox="0 0 12 12"><rect x="2" y="1" width="8" height="10" rx="1"/></svg>models.py</div>
      <div class="cs-item"><svg viewBox="0 0 12 12"><rect x="2" y="1" width="8" height="10" rx="1"/></svg>routes.py</div>
      <div class="cs-item"><svg viewBox="0 0 12 12"><rect x="2" y="1" width="8" height="10" rx="1"/></svg>config.py</div>
    </div>
    <div class="code-main">
      <div class="code-tabs"><div class="ctab act">auth.py</div><div class="ctab">middleware.py</div><div class="ctab">models.py</div></div>
<pre><span class="ky">import</span> jwt, redis
<span class="ky">from</span> datetime <span class="ky">import</span> datetime, timedelta

<span class="cm"># TODO: review refresh token rotation edge case</span>
<span class="ky">class</span> <span class="fn">AuthManager</span>:
    <span class="ky">def</span> <span class="fn">__init__</span>(self, redis_client):
        self.redis = redis_client
        self.secret = config.<span class="fn">get</span>(<span class="st">'JWT_SECRET'</span>)

    <span class="ky">def</span> <span class="fn">create_token</span>(self, user_id: str) -> str:
        payload = {
            <span class="st">'sub'</span>: user_id,
            <span class="st">'iat'</span>: datetime.<span class="fn">utcnow</span>(),
            <span class="st">'exp'</span>: datetime.<span class="fn">utcnow</span>() + timedelta(hours=<span class="st">1</span>)
        }
        <span class="ky">return</span> jwt.<span class="fn">encode</span>(payload, self.secret)

    <span class="ky">def</span> <span class="fn">validate_token</span>(self, token: str) -> dict:
        <span class="cm"># cache-first — fix applied Oct 12</span>
        cached = self.redis.<span class="fn">get</span>(<span class="st">f'token:{token}'</span>)
        <span class="ky">if</span> cached:
            <span class="ky">return</span> json.<span class="fn">loads</span>(cached)
        <span class="ky">return</span> jwt.<span class="fn">decode</span>(token, self.secret)</pre>
    </div>
  </div>
  <div class="desk-bar"><div class="dbar-clk" id="dbarClk">12:00</div></div>
</div>

<!-- OVERLAY -->"""

html = html.replace(desktop_html, "<!-- OVERLAY -->")

# 2. Make body background transparent
html = html.replace('background:#000;', 'background: transparent;')

# 3. Increase glass opacity so modals and panels are legible over bright desktops
html = html.replace('--glass:rgba(7,7,18,0.58);', '--glass:rgba(10,10,18,0.96);')

# 4. Clear recent notes mock block
recent_mock = """        <div class="gc-body">
          <div class="nr"><div class="nr-pip" style="background:var(--acc)"></div><div class="nr-txt">Semantic search debounce — 300ms to cut API hammering on rapid keystrokes</div><span class="nr-t">2m</span></div>
          <div class="nr"><div class="nr-pip" style="background:var(--teal)"></div><div class="nr-txt">Qdrant wins filtered search latency, Chroma simpler to self-host</div><span class="nr-t">41m</span></div>
          <div class="nr"><div class="nr-pip" style="background:var(--amber)"></div><div class="nr-txt">TODO: JWT refresh token edge case — 5-min window too narrow?</div><span class="nr-t">1h</span></div>
          <div class="nr"><div class="nr-pip" style="background:var(--text3)"></div><div class="nr-txt">Rohit: HDBSCAN for node clustering in graph phase 2</div><span class="nr-t">3h</span></div>
        </div>"""
html = html.replace(recent_mock, '<div class="gc-body" id="recentNotesBody"></div>')

# 4. Clear tasks mock block
tasks_mock = """        <div class="gc-body">
          <div class="tr"><div class="chk" onclick="toggleChk(this)"></div><div class="pdot ph"></div><span class="tr-txt">Review JWT middleware edge case</span></div>
          <div class="tr"><div class="chk" onclick="toggleChk(this)"></div><div class="pdot pm"></div><span class="tr-txt">Write Chroma benchmark notes</span></div>
          <div class="tr"><div class="chk done" onclick="toggleChk(this)"></div><div class="pdot pl"></div><span class="tr-txt done">Set up PyQt6 tray icon</span></div>
          <div class="tr"><div class="chk" onclick="toggleChk(this)"></div><div class="pdot pl"></div><span class="tr-txt">Draft PCOS architecture post</span></div>
        </div>"""
html = html.replace(tasks_mock, '<div class="gc-body" id="tasksBody"></div>')

# 5. Clear divergence mock block
divergence_mock = """        <div class="gc-body">
          <div class="dv">
            <div class="dv-dot"></div>
            <div class="dv-b">
              <div class="dv-title">LLM agents + tool calling patterns</div>
              <div class="dv-sub">AI/ML match · free at 3pm · 25 min</div>
            </div>
            <div class="dv-arr">↗</div>
          </div>
          <div class="dv">
            <div class="dv-dot"></div>
            <div class="dv-b">
              <div class="dv-title">Async Python: trio vs asyncio</div>
              <div class="dv-sub">Python match · 15 min read</div>
            </div>
            <div class="dv-arr">↗</div>
          </div>
          <div class="dv" style="opacity:.38">
            <div class="dv-dot" style="background:var(--text3)"></div>
            <div class="dv-b">
              <div class="dv-title">ChromaDB vs Qdrant benchmark</div>
              <div class="dv-sub">Dismissed · 2 days ago</div>
            </div>
          </div>
        </div>"""
html = html.replace(divergence_mock, '<div class="gc-body" id="divergenceBody"></div>')

# Insert the Javascript logic
new_script = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
// Bridge setup
let bridge = null;
let currentSessionId = localStorage.getItem('pcos_chat_session') || null;

new QWebChannel(qt.webChannelTransport, function(channel) {
    bridge = channel.objects.bridge;
    window.bridge = bridge;
    
    // Connect chat response signal
    bridge.chat_response_received.connect(function(sessionId, respJson) {
        let data = JSON.parse(respJson);
        const msgs = document.getElementById('chatMsgs');
        
        // Remove typing indicator if exists
        const typing = document.getElementById('typingIndicator');
        if(typing) typing.remove();
        
        if (data.error) {
            addMsg('cms', 'Error: ' + data.error);
        } else {
            if (data.session_id) {
                currentSessionId = data.session_id;
                localStorage.setItem('pcos_chat_session', currentSessionId);
            }
            addMsg('cms', data.response);
        }
    });

    loadInitialData();
});

function loadInitialData() {
    if(!bridge) return;
    bridge.get_state(function(res) {
        let data = JSON.parse(res);
        document.getElementById('stateLbl').textContent = data.state;
        document.getElementById('centerState').textContent = data.state.replace('_', ' ');
    });
    
    bridge.get_recent_notes(5, function(res) {
        let data = JSON.parse(res);
        renderNotes(data.notes);
    });
    
    bridge.get_tasks(function(res) {
        let data = JSON.parse(res);
        renderTasks(data.tasks);
    });
    
    bridge.get_divergence_queue(function(res) {
        let data = JSON.parse(res);
        renderDivergence(data.items);
    });
}

function renderNotes(notes) {
    const container = document.getElementById('recentNotesBody');
    if(!container) return;
    container.innerHTML = '';
    notes.forEach(n => {
        const div = document.createElement('div');
        div.className = 'nr';
        div.innerHTML = `<div class="nr-pip" style="background:var(--acc)"></div><div class="nr-txt">${n.content}</div><span class="nr-t"></span>`;
        container.appendChild(div);
    });
}

function renderTasks(tasks) {
    const container = document.getElementById('tasksBody');
    if(!container) return;
    container.innerHTML = '';
    document.getElementById('openTaskCt').textContent = tasks.length;
    tasks.forEach(t => {
        const div = document.createElement('div');
        div.className = 'tr';
        div.innerHTML = `<div class="chk" onclick="toggleTask('${t.id}', this)"></div><div class="pdot pl"></div><span class="tr-txt">${t.content}</span>`;
        container.appendChild(div);
    });
}

function toggleTask(id, el) {
    if(el.classList.contains('done')) return;
    el.classList.add('done');
    el.closest('.tr').querySelector('.tr-txt').classList.add('done');
    el.closest('.tr').style.opacity = '0.38';
    
    if(bridge) {
        bridge.complete_task(id, function(res) {
            let data = JSON.parse(res);
            if(data.status !== 'ok') {
                showToast("Failed to complete task");
                el.classList.remove('done');
                el.closest('.tr').querySelector('.tr-txt').classList.remove('done');
                el.closest('.tr').style.opacity = '1';
            } else {
                loadInitialData(); // refresh counts
            }
        });
    }
}

function renderDivergence(items) {
    const container = document.getElementById('divergenceBody');
    if(!container) return;
    container.innerHTML = '';
    items.forEach(i => {
        const div = document.createElement('div');
        div.className = 'dv';
        if (i.status === 'pending') {
            div.innerHTML = `
                <div class="dv-dot"></div>
                <div class="dv-b">
                  <div class="dv-title">${i.suggestion}</div>
                  <div class="dv-sub" style="margin-top: 4px;">
                    <button onclick="acceptDiv('${i.id}', this)" style="background:var(--acc);color:#fff;border:none;border-radius:3px;padding:2px 6px;font-size:9px;cursor:pointer;margin-right:4px;">Accept</button>
                    <button onclick="dismissDiv('${i.id}', this)" style="background:rgba(255,255,255,0.1);color:var(--text3);border:none;border-radius:3px;padding:2px 6px;font-size:9px;cursor:pointer;">Dismiss</button>
                  </div>
                </div>
            `;
        } else {
            div.style.opacity = '0.38';
            div.innerHTML = `
                <div class="dv-dot" style="background:var(--text3)"></div>
                <div class="dv-b">
                  <div class="dv-title">${i.suggestion}</div>
                  <div class="dv-sub">${i.status}</div>
                </div>
            `;
        }
        container.appendChild(div);
    });
}

function acceptDiv(id, el) {
    if(bridge) bridge.accept_divergence(id, function(){ loadInitialData(); });
}
function dismissDiv(id, el) {
    if(bridge) bridge.dismiss_divergence(id, function(){ loadInitialData(); });
}

// chat functions
function openChat(){document.getElementById('chatOverlay').classList.add('open');setTimeout(()=>document.getElementById('chatIn').focus(),80);}
function closeChat(){document.getElementById('chatOverlay').classList.remove('open');}
function sendChat(){
  const inp=document.getElementById('chatIn'),v=inp.value.trim();if(!v)return;
  addMsg('cmu',v);inp.value='';inp.style.height='auto';
  
  const msgs=document.getElementById('chatMsgs');
  const t=document.createElement('div');t.className='cmsg cms'; t.id = 'typingIndicator';
  t.innerHTML='<div class="cmsg-av">P</div><div><div class="cmsg-b"><div class="tping"><span></span><span></span><span></span></div></div></div>';
  msgs.appendChild(t);msgs.scrollTop=msgs.scrollHeight;
  
  if(bridge) bridge.send_chat(v, currentSessionId);
}
function addMsg(cls,txt){
  const msgs=document.getElementById('chatMsgs');
  const d=document.createElement('div');d.className='cmsg '+cls;
  d.innerHTML=`<div class="cmsg-av">${cls==='cmu'?'Y':'P'}</div><div><div class="cmsg-b">${txt}</div></div>`;
  msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}

// capture
let capMode='note';
function openCapModal(mode,prefill){
  setMode(mode||'note');
  document.getElementById('capModal').classList.add('open');
  const i=document.getElementById('capIn');
  if(prefill)i.value=prefill;
  setTimeout(()=>i.focus(),80);
}
function capBg(e){if(e.target===document.getElementById('capModal'))closeCapture();}
function closeCapture(){document.getElementById('capModal').classList.remove('open');document.getElementById('capIn').value='';}
function capKey(e){
  if(e.key==='Escape'){e.preventDefault();closeCapture();}
  if(e.key==='Enter'&&!e.shiftKey){
      e.preventDefault();
      const v=document.getElementById('capIn').value.trim();
      if(v && bridge){
          bridge.capture(v, capMode, function(res) {
              let data = JSON.parse(res);
              if(data.status === 'ok') {
                  showToast("Captured successfully");
                  loadInitialData();
              } else {
                  showToast("Error capturing");
              }
          });
          closeCapture();
      }
  }
}
function setMode(m){
  capMode=m;
  ['note','task','idea'].forEach(k=>document.getElementById('cpm-'+k).classList.toggle('act',k===m));
  document.getElementById('capModal').querySelector('.cap-ic').style.background=
    m==='task'?'var(--amber-bg)':m==='idea'?'var(--green-bg)':'var(--acc-bg)';
}

// command bar
const csIn=document.getElementById('csIn');
const results=document.getElementById('cmdResults');
const modeBadge=document.getElementById('modeBadge');
const cmdHint=document.getElementById('cmdHint');

let searchTimer = null;
csIn.addEventListener('input',()=>{
  const v=csIn.value;
  if(v.startsWith('?')){
    modeBadge.className='cmd-mode-badge cmb-chat';modeBadge.textContent='chat';
    cmdHint.textContent='⏎ to open';
    results.classList.remove('show');
  } else if(v.startsWith('/note ')||v==='/note'){
    modeBadge.className='cmd-mode-badge cmb-note';modeBadge.textContent='note';
    cmdHint.textContent='⏎ to save';
    results.classList.remove('show');
  } else if(v.startsWith('/task ')||v==='/task'){
    modeBadge.className='cmd-mode-badge cmb-task';modeBadge.textContent='task';
    cmdHint.textContent='⏎ to save';
    results.classList.remove('show');
  } else if(v.startsWith('/idea ')||v==='/idea'){
    modeBadge.className='cmd-mode-badge cmb-idea';modeBadge.textContent='idea';
    cmdHint.textContent='⏎ to save';
    results.classList.remove('show');
  } else if(v.length>1){
    modeBadge.className='cmd-mode-badge cmb-search';modeBadge.textContent='search';
    cmdHint.textContent='⏎ to search';
    results.classList.remove('show');
  } else {
    modeBadge.className='cmd-mode-badge cmb-default';modeBadge.textContent='PCOS';
    cmdHint.textContent='⌘K';
    results.classList.remove('show');
  }
});

function renderSearchResults(items) {
    results.innerHTML = '';
    if(items && items.length > 0) {
        const sec = document.createElement('div'); sec.className = 'cr-section';
        const lbl = document.createElement('div'); lbl.className = 'cr-label'; lbl.textContent = 'results';
        sec.appendChild(lbl);
        items.forEach(i => {
            const div = document.createElement('div'); div.className = 'cr-item';
            // Determine type correctly if available, fallback to note
            const typ = i.type || 'note';
            const color = typ === 'task' ? 'var(--amber)' : (typ === 'idea' ? 'var(--green)' : 'var(--acc)');
            div.innerHTML = `<div class="cr-pip" style="background:${color}"></div><div class="cr-text">${i.content.substring(0, 80)}</div><span class="cr-type crt-${typ}">${typ}</span>`;
            sec.appendChild(div);
        });
        results.appendChild(sec);
        results.classList.add('show');
    } else {
        results.classList.remove('show');
    }
}

csIn.addEventListener('keydown',e=>{
  const v=csIn.value.trim();
  if(e.key==='Enter'&&!e.shiftKey){
    e.preventDefault();
    if(v.startsWith('?')){
      const q=v.slice(1).trim();
      openChat();
      if(q){setTimeout(()=>{document.getElementById('chatIn').value=q;sendChat();},120);}
      csIn.value='';csIn.dispatchEvent(new Event('input'));
    } else if(v.startsWith('/note ')){
      openCapModal('note',v.slice(6).trim());csIn.value='';csIn.dispatchEvent(new Event('input'));
    } else if(v.startsWith('/task ')){
      openCapModal('task',v.slice(6).trim());csIn.value='';csIn.dispatchEvent(new Event('input'));
    } else if(v.startsWith('/idea ')){
      openCapModal('idea',v.slice(6).trim());csIn.value='';csIn.dispatchEvent(new Event('input'));
    } else if(v.length>0){
      if(bridge){
          bridge.search_notes(v, function(res) {
              let data = JSON.parse(res);
              renderSearchResults(data.results);
          });
      }
    }
  }
  if(e.key==='Escape'){
    if(v.length>0){csIn.value='';csIn.dispatchEvent(new Event('input'));}
    else { if(bridge) bridge.close_overlay(); }
  }
});

document.addEventListener('click',e=>{
  if(!document.getElementById('cmdStrip').contains(e.target))results.classList.remove('show');
});

// toast
function showToast(msg, submsg="") {
    const toast = document.getElementById('toast');
    toast.querySelector('.toast-txt').textContent = msg;
    toast.querySelector('.toast-sub').textContent = submsg;
    toast.classList.remove('gone');
    setTimeout(() => toast.classList.add('gone'), 4000);
}

// clock
function tick(){
  const n=new Date(),t=n.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
  ['osClock','centerClock','dbarClk'].forEach(id=>{const el=document.getElementById(id);if(el)el.textContent=t;});
}
tick();setInterval(tick,10000);

// State Override
const STATES=[
  {lbl:'deep_work',cls:'sc-deep'},
  {lbl:'free',cls:'sc-free'},
  {lbl:'distracted',cls:'sc-dist'},
  {lbl:'meeting',cls:'sc-meet'}
];
let si=0;
function cycleState(){
  si=(si+1)%STATES.length;
  const s=STATES[si];
  const chip=document.getElementById('stateChip');
  chip.className='state-chip '+s.cls;
  document.getElementById('stateLbl').textContent=s.lbl;
  document.getElementById('centerState').textContent=s.lbl.replace('_',' ');
  if(bridge) bridge.override_state(s.lbl, 30, function(){});
}

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    if(document.getElementById('capModal').classList.contains('open')){closeCapture();return;}
    if(document.getElementById('chatOverlay').classList.contains('open')){closeChat();return;}
    if(bridge) { bridge.close_overlay(); return; }
  }
  if((e.ctrlKey||e.metaKey)&&e.altKey&&e.key.toLowerCase()==='p'){e.preventDefault();openCapModal();}
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();csIn.focus();csIn.select();}
});
</script>
"""

html = re.sub(r'<script>.*?</script>', new_script, html, flags=re.DOTALL)

with open(target_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Wrote {target_path}")
