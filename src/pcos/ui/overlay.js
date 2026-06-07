// ──────────────────────────────────────────────
// PCOS HUD – Application Logic
// ──────────────────────────────────────────────

// ── Bridge ──
let bridge = null;
let bridgeReady = false;

new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
    bridgeReady = true;

    // Chat response signal
    if (bridge.chat_response_received) {
        bridge.chat_response_received.connect(function (sessionId, jsonStr) {
            const data = JSON.parse(jsonStr);
            if (data.session_id) {
                localStorage.setItem('pcos_chat_session', data.session_id);
            }
            const typing = document.getElementById('typingIndicator');
            if (typing) typing.remove();
            waitingChat = false;
            addChatMsg('cms', data.response || data.error || 'No response');
        });
    }

    loadAllData();
    setInterval(loadAllData, 60000);
});

function callBridge(fn) {
    if (bridgeReady) fn();
}

// ── State ──
let captureMode = 'note';
let waitingChat = false;
let autoRefresh = true;
const STATES = ['deep_work', 'free', 'distracted', 'meeting', 'wind_down'];

// ── Helpers ──
function showToast(msg) {
    const t = document.getElementById('toast');
    t.querySelector('.toast-txt').textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

// ── Data loading ──
async function loadState() {
    callBridge(async () => {
        const d = JSON.parse(await bridge.get_state());
        const s = d.state || 'unknown';
        document.getElementById('stateLbl').textContent = s;
        document.getElementById('centerState').textContent = s.replace(/_/g, ' ');
        document.getElementById('contextStatePill').innerHTML =
            `<span class="sdot" style="width:4px;height:4px"></span> ${s}`;
        const chip = document.getElementById('stateChip');
        chip.style.background =
            s === 'deep_work' ? 'var(--teal-bg)' :
                s === 'distracted' ? 'var(--red-bg)' :
                    'var(--amber-bg)';
    });
}

async function loadNotes() {
    callBridge(async () => {
        const d = JSON.parse(await bridge.get_recent_notes(6));
        const notes = d.notes || [];
        const container = document.getElementById('recentNotesBody');
        container.innerHTML = notes.slice(0, 5).map(n =>
            `<div class="nr">
                <div class="nr-pip" style="background:var(--acc)"></div>
                <div class="nr-txt">${escapeHtml((n.content || '').substring(0, 80))}</div>
                <span class="nr-t">${n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</span>
            </div>`
        ).join('');
        document.getElementById('noteCount').textContent = notes.length;
    });
}

async function loadTasks() {
    callBridge(async () => {
        const d = JSON.parse(await bridge.get_tasks());
        const tasks = d.tasks || [];
        const container = document.getElementById('tasksBody');
        container.innerHTML = tasks.map(t => {
            const doneClass = t.completed ? ' done' : '';
            return `<div class="tr${doneClass}">
                <div class="chk${doneClass}" data-id="${t.id}" onclick="toggleTask(this)"></div>
                <div class="pdot"></div>
                <span class="tr-txt">${escapeHtml((t.content || '').substring(0, 60))}</span>
            </div>`;
        }).join('');
        const openCount = tasks.filter(t => !t.completed).length;
        document.getElementById('taskCount').textContent = openCount + ' open';
        document.getElementById('openTaskCt').textContent = openCount;
    });
}

async function loadDivergence() {
    callBridge(async () => {
        const d = JSON.parse(await bridge.get_divergence_queue());
        const items = d.items || [];
        const container = document.getElementById('divergenceBody');
        let pending = 0;
        container.innerHTML = items.map(i => {
            if (i.status === 'pending') pending++;
            let subHtml;
            if (i.status === 'pending') {
                subHtml = `<div class="dv-sub">
                    <button class="accept" onclick="event.stopPropagation();acceptDiv('${i.id}')">Accept</button>
                    <button class="dismiss" onclick="event.stopPropagation();dismissDiv('${i.id}')">Dismiss</button>
                    <button class="delete" onclick="event.stopPropagation();deleteDiv('${i.id}')">🗑</button>
                </div>`;
            } else {
                subHtml = `<div class="dv-sub">
                    <span>${i.status}</span>
                    <button class="delete" onclick="event.stopPropagation();deleteDiv('${i.id}')">🗑</button>
                </div>`;
            }
            return `<div class="dv" style="${i.status !== 'pending' ? 'opacity:0.5' : ''}">
                <div class="dv-dot" style="background:${i.status === 'pending' ? 'var(--acc2)' : 'var(--text3)'}"></div>
                <div class="dv-b">
                    <div class="dv-title">${escapeHtml(i.suggestion || '')}</div>
                    ${subHtml}
                </div>
            </div>`;
        }).join('');
        document.getElementById('divergenceNewBadge').textContent = pending + ' new';
    });
}

function loadAllData() {
    if (autoRefresh) {
        loadState();
        loadNotes();
        loadTasks();
        loadDivergence();
    }
}

// ── Task toggle ──
async function toggleTask(el) {
    if (el.classList.contains('done')) return;
    const id = el.getAttribute('data-id');
    const row = el.closest('.tr');
    el.classList.add('done');
    row.classList.add('done');
    row.style.opacity = '0.45';
    callBridge(async () => {
        const r = JSON.parse(await bridge.complete_task(id));
        if (r.status !== 'ok') {
            el.classList.remove('done');
            row.classList.remove('done');
            row.style.opacity = '1';
            showToast('Failed to complete task');
        }
    });
}

// ── Divergence actions ──
async function acceptDiv(id) {
    callBridge(async () => {
        await bridge.accept_divergence(id);
        loadDivergence();
    });
}

async function dismissDiv(id) {
    callBridge(async () => {
        await bridge.dismiss_divergence(id);
        loadDivergence();
    });
}

async function deleteDiv(id) {
    callBridge(async () => {
        if (typeof bridge.delete_divergence === 'function') {
            await bridge.delete_divergence(id);
        }
        const el = document.querySelector(`.dv button.delete[onclick*="${id}"]`);
        if (el) {
            const dv = el.closest('.dv');
            dv.style.transition = 'opacity .15s';
            dv.style.opacity = '0';
            setTimeout(() => dv.remove(), 200);
        }
        const pending = document.querySelectorAll('.dv .accept').length;
        document.getElementById('divergenceNewBadge').textContent = pending + ' new';
    });
}

// ── Radial State Menu ──
const stateChip = document.getElementById('stateChip');
const stateRadial = document.getElementById('stateRadial');

const STATE_OPTIONS = [
    { id: 'deep_work', label: 'Deep', color: 'var(--teal)' },
    { id: 'free', label: 'Free', color: 'var(--amber)' },
    { id: 'distracted', label: 'Dist', color: 'var(--red)' },
    { id: 'meeting', label: 'Meet', color: '#74b9ff' },   // blue fallback
    { id: 'wind_down', label: 'Wind', color: 'var(--text3)' }
];

// Build radial items
function buildRadialMenu() {
    stateRadial.innerHTML = '';
    STATE_OPTIONS.forEach((opt) => {
        const item = document.createElement('div');
        item.className = 'state-radial-item';
        item.innerHTML = `<span class="sdot" style="background:${opt.color};width:5px;height:5px;border-radius:50%;display:inline-block;margin-right:4px"></span>${opt.label}`;
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            selectState(opt.id);
            closeRadial();
        });
        stateRadial.appendChild(item);
    });
}

function positionRadialItems() {
    const items = stateRadial.querySelectorAll('.state-radial-item');
    const count = items.length;
    if (count === 0) return;

    const radius = 70;
    // Only fan out downwards – south hemisphere
    const startAngle = 45;   // bottom‑right
    const endAngle = 135;    // bottom‑left

    items.forEach((item, i) => {
        let angle;
        if (count === 1) {
            angle = 90;
        } else {
            angle = startAngle + (i / (count - 1)) * (endAngle - startAngle);
        }
        const rad = angle * Math.PI / 180;
        const x = Math.cos(rad) * radius;
        const y = Math.sin(rad) * radius;
        item.style.transform = `translate(${x}px, ${y}px)`;
    });
}

function positionRadialContainer() {
    // Position the radial container at the chip's center
    const chipRect = stateChip.getBoundingClientRect();
    const overlayRect = document.querySelector('.overlay').getBoundingClientRect();
    const centerX = chipRect.left + chipRect.width / 2 - overlayRect.left;
    const centerY = chipRect.top + chipRect.height / 2 - overlayRect.top;
    stateRadial.style.left = centerX + 'px';
    stateRadial.style.top = centerY + 'px';
}

function openRadial() {
    positionRadialContainer();
    positionRadialItems();
    stateRadial.classList.add('open');
}

function closeRadial() {
    stateRadial.classList.remove('open');
}

// Toggle on chip click
stateChip.addEventListener('click', (e) => {
    e.stopPropagation();
    if (stateRadial.classList.contains('open')) {
        closeRadial();
    } else {
        openRadial();
    }
});

// Close when clicking outside
document.addEventListener('click', (e) => {
    if (stateRadial.classList.contains('open') &&
        !stateChip.contains(e.target) &&
        !stateRadial.contains(e.target)) {
        closeRadial();
    }
});

async function selectState(stateId) {
    callBridge(async () => {
        await bridge.override_state(stateId, 30);
        loadState();
    });
}

// Build on load
buildRadialMenu();

// ── Chat ──
function openChat() {
    document.getElementById('chatOverlay').classList.add('open');
    setTimeout(() => document.getElementById('chatIn').focus(), 80);
}

function closeChat() {
    document.getElementById('chatOverlay').classList.remove('open');
}

function chatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 56) + 'px';
}

function addChatMsg(cls, txt) {
    const msgs = document.getElementById('chatMsgs');
    const d = document.createElement('div');
    d.className = 'cmsg ' + cls;
    d.innerHTML = `<div class="cmsg-av">${cls === 'cmu' ? 'Y' : 'P'}</div>
                   <div><div class="cmsg-b">${txt}</div></div>`;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
}

function sendChat() {
    if (waitingChat) return;
    const inp = document.getElementById('chatIn');
    const msg = inp.value.trim();
    if (!msg) return;
    addChatMsg('cmu', escapeHtml(msg));
    inp.value = '';
    inp.style.height = 'auto';
    const typing = document.createElement('div');
    typing.className = 'cmsg cms';
    typing.id = 'typingIndicator';
    typing.innerHTML = '<div class="cmsg-av">P</div><div><div class="cmsg-b"><div class="tping"><span></span><span></span><span></span></div></div></div>';
    document.getElementById('chatMsgs').appendChild(typing);
    waitingChat = true;
    callBridge(() => {
        const sid = localStorage.getItem('pcos_chat_session') || '';
        bridge.send_chat(msg, sid);
    });
}

// ── Command bar ──
const csIn = document.getElementById('csIn');
const results = document.getElementById('cmdResults');
const modeBadge = document.getElementById('modeBadge');
const cmdHint = document.getElementById('cmdHint');
let searchDeb = null;

function clearSearch() {
    results.classList.remove('show');
    autoRefresh = true;
}

csIn.addEventListener('input', () => {
    const v = csIn.value;
    if (v.startsWith('?')) {
        modeBadge.className = 'cmd-mode-badge cmb-chat';
        modeBadge.textContent = 'chat';
        cmdHint.textContent = '⏎ to open';
        clearSearch();
    } else if (v.startsWith('/note ')) {
        modeBadge.className = 'cmd-mode-badge cmb-note';
        modeBadge.textContent = 'note';
        cmdHint.textContent = '⏎ to save';
        clearSearch();
    } else if (v.startsWith('/task ')) {
        modeBadge.className = 'cmd-mode-badge cmb-task';
        modeBadge.textContent = 'task';
        cmdHint.textContent = '⏎ to save';
        clearSearch();
    } else if (v.startsWith('/idea ')) {
        modeBadge.className = 'cmd-mode-badge cmb-task';
        modeBadge.textContent = 'idea';
        cmdHint.textContent = '⏎ to save';
        clearSearch();
    } else if (v.length > 1 && !v.startsWith('/')) {
        modeBadge.className = 'cmd-mode-badge cmb-search';
        modeBadge.textContent = 'search';
        cmdHint.textContent = 'searching…';
        if (searchDeb) clearTimeout(searchDeb);
        searchDeb = setTimeout(() => {
            callBridge(async () => {
                const r = JSON.parse(await bridge.search_notes(v));
                if (r.results && r.results.length) {
                    results.innerHTML = r.results.map(n =>
                        `<div class="cr-item" data-query="${escapeHtml(n.content || '')}">
                            <div class="cr-pip" style="background:var(--acc)"></div>
                            <div class="cr-text">${escapeHtml((n.content || '').substring(0, 80))}</div>
                        </div>`
                    ).join('');
                    results.classList.add('show');
                    autoRefresh = false;
                } else {
                    clearSearch();
                }
            });
        }, 300);
    } else {
        modeBadge.className = 'cmd-mode-badge cmb-default';
        modeBadge.textContent = 'PCOS';
        cmdHint.textContent = '⌘K';
        clearSearch();
    }
});

csIn.addEventListener('keydown', (e) => {
    const v = csIn.value.trim();
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (v.startsWith('?')) {
            openChat();
            const q = v.slice(1).trim();
            if (q) {
                setTimeout(() => {
                    document.getElementById('chatIn').value = q;
                    sendChat();
                }, 120);
            }
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        } else if (v.startsWith('/note ')) {
            openCapture('note', v.slice(6).trim());
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        } else if (v.startsWith('/task ')) {
            openCapture('task', v.slice(6).trim());
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        } else if (v.startsWith('/idea ')) {
            openCapture('idea', v.slice(6).trim());
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        } else if (v.length > 0) {
            openChat();
            setTimeout(() => {
                document.getElementById('chatIn').value = v;
                sendChat();
            }, 120);
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        }
    }
    if (e.key === 'Escape') {
        if (v.length > 0) {
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
        } else if (bridgeReady) {
            bridge.close_overlay();
        }
    }
});

results.addEventListener('click', (e) => {
    const item = e.target.closest('.cr-item');
    if (item) {
        const q = item.getAttribute('data-query');
        openChat();
        setTimeout(() => {
            document.getElementById('chatIn').value = q;
            sendChat();
        }, 120);
        csIn.value = '';
        clearSearch();
    }
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('.cmd-strip')) clearSearch();
});

// ── Capture modal ──
function openCapture(mode, prefill) {
    setCapMode(mode || 'note');
    document.getElementById('capModal').classList.add('open');
    const inp = document.getElementById('capIn');
    if (prefill) inp.value = prefill;
    setTimeout(() => inp.focus(), 80);
}

function closeCapture() {
    document.getElementById('capModal').classList.remove('open');
    document.getElementById('capIn').value = '';
}

function capKey(e) {
    if (e.key === 'Escape') {
        closeCapture();
        e.preventDefault();
    }
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const v = document.getElementById('capIn').value.trim();
        if (v) {
            callBridge(async () => {
                const r = JSON.parse(await bridge.capture(v, captureMode));
                showToast(r.status === 'ok' ? captureMode + ' captured' : 'Error');
                loadAllData();
            });
            closeCapture();
        }
    }
}

function setCapMode(m) {
    captureMode = m;
    document.querySelectorAll('.cap-modes .cpm').forEach(b => {
        b.classList.toggle('act', b.getAttribute('data-mode') === m);
    });
}

// ── Expand panel ──
function expandPanel(type) {
    const overlay = document.getElementById('expandedOverlay');
    const title = document.getElementById('expandedTitle');
    const body = document.getElementById('expandedBody');
    let content = '';

    switch (type) {
        case 'notes':
            title.textContent = 'Recent Notes';
            content = document.getElementById('recentNotesBody').innerHTML;
            break;
        case 'tasks':
            title.textContent = 'Tasks';
            content = document.getElementById('tasksBody').innerHTML;
            break;
        case 'diverge':
            title.textContent = 'Divergence';
            content = document.getElementById('divergenceBody').innerHTML;
            break;
        case 'context':
            title.textContent = 'Context';
            const ctxItems = document.querySelectorAll('.xrow');
            content = Array.from(ctxItems).map(r => r.outerHTML).join('');
            break;
        default:
            return;
    }
    body.innerHTML = content;
    overlay.classList.add('open');
}

function closeExpanded() {
    document.getElementById('expandedOverlay').classList.remove('open');
}

// ── Close overlay ──
function closeOverlay() {
    callBridge(() => { bridge.close_overlay(); });
}

// ── Keyboard shortcuts ──
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (document.getElementById('capModal').classList.contains('open')) {
            closeCapture();
            return;
        }
        if (document.getElementById('chatOverlay').classList.contains('open')) {
            closeChat();
            return;
        }
        if (csIn.value) {
            csIn.value = '';
            csIn.dispatchEvent(new Event('input'));
            return;
        }
        if (bridgeReady) bridge.close_overlay();
        return;
    }
    if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        openCapture();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        csIn.focus();
        csIn.select();
    }
});

// ── Attach listeners once the DOM is interactive ──
document.addEventListener('DOMContentLoaded', function () {
    // Chat toggle
    const chatToggle = document.getElementById('chatToggleCard');
    if (chatToggle) {
        chatToggle.addEventListener('click', openChat);
    }

    // Expand buttons (select all elements with data-expand attribute)
    document.querySelectorAll('[data-expand]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation(); // prevent card click if needed
            const panelType = this.getAttribute('data-expand');
            expandPanel(panelType);
        });
    });
});

// ── Clock ──
function tick() {
    const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    document.getElementById('osClock').textContent = t;
    document.getElementById('centerClock').textContent = t;
}
tick();
setInterval(tick, 10000);

// ── Initial load fallback ──
setTimeout(loadAllData, 200);