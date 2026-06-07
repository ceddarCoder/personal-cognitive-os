// ==================== API Helpers ====================
const API_BASE = 'http://localhost:8765';

async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
}

function showToast(title, subtitle, type = 'acc') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const colors = {
        green: ['var(--green-bg)', 'var(--green)'],
        acc: ['var(--acc-bg)', 'var(--acc2)'],
        teal: ['var(--teal-bg)', 'var(--teal)'],
        amber: ['var(--amber-bg)', 'var(--amber)'],
        red: ['var(--red-bg)', 'var(--red)']
    };
    const [bg, clr] = colors[type] || colors.acc;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon" style="background:${bg};color:${clr}"><svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M2 5.5l2 2 4-4"/></svg></div>
        <div><div class="toast-text">${escapeHtml(title)}</div><div class="toast-sub">${escapeHtml(subtitle)}</div></div>
        <button class="toast-x" onclick="this.closest('.toast').remove()">✕</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

function timeAgo(date) {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
}

// ==================== Global State ====================
let currentNoteId = null;
let chatSessionId = localStorage.getItem('pcos_chat_session') || null;
let currentWeekOffset = 0;
let currentTaskFilter = 'all';
let currentGraphNodes = [];
let currentGraphEdges = [];

// ==================== Notes ====================
async function loadNotes() {
    const data = await apiCall('/notes?limit=50');
    const notesList = document.getElementById('notesList');
    if (!notesList) return;
    notesList.innerHTML = '';
    let lastGroup = '';
    data.notes.forEach(note => {
        const date = new Date(note.created_at);
        const today = new Date();
        const isToday = date.toDateString() === today.toDateString();
        const group = isToday ? 'today' : 'yesterday';
        if (group !== lastGroup) {
            lastGroup = group;
            const groupDiv = document.createElement('div');
            groupDiv.className = 'nl-group-label';
            groupDiv.textContent = group;
            notesList.appendChild(groupDiv);
        }
        const nli = document.createElement('div');
        nli.className = 'nli';
        nli.dataset.id = note.id;
        nli.onclick = () => openNote(note.id);
        nli.innerHTML = `
            <div class="nli-pip" style="background:var(--acc)"></div>
            <div class="nli-title">${escapeHtml(note.title || note.content.substring(0, 50))}</div>
            <div class="nli-preview">${escapeHtml(note.content.substring(0, 100))}</div>
            <div class="nli-meta">
                ${note.tags ? JSON.parse(note.tags).map(t => `<span class="ntag nt-acc">${escapeHtml(t)}</span>`).join('') : ''}
                <span class="nli-time">${timeAgo(date)}</span>
            </div>
        `;
        notesList.appendChild(nli);
    });
    document.getElementById('notesCount').innerText = data.notes.length;
    return data.notes;
}

async function openNote(id) {
    currentNoteId = id;
    const note = await apiCall(`/notes/${id}`);
    document.getElementById('noteTitleIn').value = note.title || '';
    document.getElementById('noteEditor').value = note.content;
    // Update tags
    const tagsContainer = document.getElementById('noteTags');
    if (tagsContainer) {
        if (note.tags) {
            const tags = JSON.parse(note.tags);
            tagsContainer.innerHTML = tags.map(t => `<span class="ntag nt-acc" onclick="this.remove()">${escapeHtml(t)} ✕</span>`).join('');
            tagsContainer.innerHTML += '<span class="ne-tag-add" id="addTagBtn">+ tag</span>';
        } else {
            tagsContainer.innerHTML = '<span class="ne-tag-add" id="addTagBtn">+ tag</span>';
        }
    }
    // Update backlinks
    const backlinksDiv = document.getElementById('backlinksList');
    if (backlinksDiv) {
        if (note.backlinks && note.backlinks.length) {
            backlinksDiv.innerHTML = note.backlinks.map(link => `<div class="backlink" onclick="openNoteByTitle('${link}')">${escapeHtml(link)}</div>`).join('');
        } else {
            backlinksDiv.innerHTML = '<div class="backlink">—</div>';
        }
    }
    // Update timestamp
    const timestampEl = document.getElementById('noteTimestamp');
    if (timestampEl) timestampEl.innerHTML = `<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="3.5"/><path d="M5 3v2.5L6.5 7"/></svg> ${timeAgo(new Date(note.created_at))}`;
    // Word count
    const words = note.content.trim().split(/\s+/).length;
    const wordCountEl = document.getElementById('wordCount');
    if (wordCountEl) wordCountEl.innerText = words;
    // Highlight in list
    document.querySelectorAll('.nli').forEach(el => el.classList.remove('act'));
    const active = document.querySelector(`.nli[data-id="${id}"]`);
    if (active) active.classList.add('act');
}

async function saveNote() {
    const title = document.getElementById('noteTitleIn').value;
    const content = document.getElementById('noteEditor').value;
    if (!content.trim() && !title.trim()) return;

    if (!currentNoteId) {
        const data = await apiCall('/notes', {
            method: 'POST',
            body: JSON.stringify({ title, content, type: 'note', source: 'webapp' })
        });
        currentNoteId = data.id;
        showToast('Note created', 'Saved successfully', 'green');
        loadNotes();
        return;
    }

    await apiCall(`/notes/${currentNoteId}`, {
        method: 'PUT',
        body: JSON.stringify({ title, content })
    });
    showToast('Note saved', 'Changes saved', 'green');
    loadNotes(); // refresh list
}

function startNewNote() {
    currentNoteId = null;
    document.getElementById('noteTitleIn').value = '';
    document.getElementById('noteEditor').value = '';
    
    const tagsContainer = document.getElementById('noteTags');
    if (tagsContainer) {
        tagsContainer.innerHTML = '<span class="ne-tag-add" id="addTagBtn">+ tag</span>';
    }
    
    const backlinksDiv = document.getElementById('backlinksList');
    if (backlinksDiv) {
        backlinksDiv.innerHTML = '<div class="backlink">—</div>';
    }
    
    const timestampEl = document.getElementById('noteTimestamp');
    if (timestampEl) timestampEl.innerHTML = `<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="3.5"/><path d="M5 3v2.5L6.5 7"/></svg> Just now`;
    
    const wordCountEl = document.getElementById('wordCount');
    if (wordCountEl) wordCountEl.innerText = '0';
    
    document.querySelectorAll('.nli').forEach(el => el.classList.remove('act'));
    document.getElementById('noteEditor').focus();
}

async function deleteNote() {
    if (!currentNoteId) return;
    if (!confirm('Delete this note permanently?')) return;
    await apiCall(`/notes/${currentNoteId}?hard=true`, { method: 'DELETE' });
    showToast('Note deleted', 'Permanently removed', 'red');
    startNewNote();
    loadNotes();
}

document.getElementById('deleteNoteBtn')?.addEventListener('click', deleteNote);

// Auto‑save on input
let saveTimeout;
function scheduleSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveNote, 1500);
}
document.getElementById('noteTitleIn')?.addEventListener('input', scheduleSave);
document.getElementById('noteEditor')?.addEventListener('input', scheduleSave);
document.getElementById('saveNoteBtn')?.addEventListener('click', saveNote);

// Add tag
document.getElementById('noteTags')?.addEventListener('click', (e) => {
    if (e.target.id === 'addTagBtn') {
        const tag = prompt('Enter new tag:');
        if (tag && tag.trim()) {
            const tagsContainer = document.getElementById('noteTags');
            const newTag = document.createElement('span');
            newTag.className = 'ntag nt-acc';
            newTag.innerHTML = `${escapeHtml(tag.trim())} ✕`;
            newTag.onclick = () => newTag.remove();
            tagsContainer.insertBefore(newTag, tagsContainer.lastElementChild);
            // Save tags to backend
            const allTags = Array.from(tagsContainer.querySelectorAll('.ntag:not(#addTagBtn)')).map(t => t.innerText.replace('✕', '').trim());
            if (currentNoteId) {
                apiCall(`/notes/${currentNoteId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ tags: allTags })
                }).catch(() => { });
            }
        }
    }
});

// ==================== Tasks ====================
async function loadTasks() {
    const data = await apiCall('/tasks');
    // Ensure kanban columns exist
    const tasksBody = document.getElementById('kanbanColumns');
    if (tasksBody && tasksBody.children.length === 0) {
        tasksBody.innerHTML = `
            <div class="task-col"><div class="task-col-head"><div class="tch-dot" style="background:var(--text3)"></div><span class="tch-label">backlog</span><span class="tch-count"></span></div><div class="task-col-body"></div></div>
            <div class="task-col"><div class="task-col-head"><div class="tch-dot" style="background:var(--amber)"></div><span class="tch-label">in progress</span><span class="tch-count"></span></div><div class="task-col-body"></div></div>
            <div class="task-col"><div class="task-col-head"><div class="tch-dot" style="background:var(--blue)"></div><span class="tch-label">review</span><span class="tch-count"></span></div><div class="task-col-body"></div></div>
            <div class="task-col"><div class="task-col-head"><div class="tch-dot" style="background:var(--green)"></div><span class="tch-label">done</span><span class="tch-count"></span></div><div class="task-col-body"></div></div>
        `;
    }
    const columns = {
        backlog: document.querySelector('.task-col:first-child .task-col-body'),
        in_progress: document.querySelector('.task-col:nth-child(2) .task-col-body'),
        review: document.querySelector('.task-col:nth-child(3) .task-col-body'),
        done: document.querySelector('.task-col:nth-child(4) .task-col-body'),
    };
    for (let col in columns) if (columns[col]) columns[col].innerHTML = '';
    let counts = { backlog: 0, in_progress: 0, review: 0, done: 0 };
    data.tasks.forEach(task => {
        let col = 'backlog';
        if (task.status === 'in_progress') col = 'in_progress';
        else if (task.status === 'review') col = 'review';
        else if (task.status === 'done') col = 'done';
        counts[col]++;
        const container = columns[col];
        if (!container) return;
        const card = document.createElement('div');
        card.className = `task-card ${task.priority || 'med'}`;
        const taskTitle = task.title || task.content?.substring(0, 50) || 'Untitled';
        card.innerHTML = `
            <div class="tc-header">
                <div class="tc-title">${escapeHtml(taskTitle)}</div>
                <button class="tc-delete" data-id="${task.id}" title="Delete task">✕</button>
            </div>
            <div class="tc-meta">
                ${task.tags ? JSON.parse(task.tags).map(t => `<span class="tc-tag nt-acc">${escapeHtml(t)}</span>`).join('') : ''}
                ${task.due_date ? `<span class="tc-due"><svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="3.5"/><path d="M5 3v2.5"/></svg> ${task.due_date}</span>` : ''}
                <span class="tc-pri ${task.priority}">${task.priority}</span>
            </div>
        `;
        card.querySelector('.tc-title').onclick = () => openNote(task.id);
        container.appendChild(card);
    });
    // Update column counts
    const countSpans = document.querySelectorAll('.task-col-head .tch-count');
    if (countSpans.length) {
        countSpans[0].innerText = counts.backlog;
        countSpans[1].innerText = counts.in_progress;
        countSpans[2].innerText = counts.review;
        countSpans[3].innerText = counts.done;
    }
    document.getElementById('tasksCount').innerText = counts.backlog + counts.in_progress + counts.review;
    // Attach delete listeners to task cards
    document.querySelectorAll('.tc-delete').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (!confirm('Delete this task?')) return;
            await apiCall(`/tasks/${id}`, { method: 'DELETE' });
            showToast('Task deleted', 'Removed', 'red');
            loadTasks();
        };
    });
}

async function createTask(title, priority, dueDate, tags, description) {
    await apiCall('/tasks', {
        method: 'POST',
        body: JSON.stringify({ title, priority, due_date: dueDate, tags, description })
    });
    showToast('Task created', `"${title}" added`, 'green');
    loadTasks();
}

// New task modal
document.getElementById('newTaskBtn')?.addEventListener('click', () => document.getElementById('taskModalBackdrop').classList.add('open'));
document.getElementById('createTaskBtn')?.addEventListener('click', async () => {
    const title = document.getElementById('newTaskTitle').value;
    if (!title) return;
    const priority = document.getElementById('newTaskPriority').value;
    const dueDate = document.getElementById('newTaskDue').value;
    const tags = [];
    document.querySelectorAll('#taskTagsWrap .tag-chip').forEach(t => tags.push(t.innerText.replace('✕', '').trim()));
    const notes = document.getElementById('newTaskNotes').value;
    await createTask(title, priority, dueDate, tags, notes);
    document.getElementById('taskModalBackdrop').classList.remove('open');
    document.getElementById('newTaskTitle').value = '';
    document.getElementById('newTaskNotes').value = '';
    document.getElementById('newTaskDue').value = '';
    document.getElementById('taskTagsWrap').innerHTML = '<input class="tag-inp" id="newTaskTagInput" placeholder="add tag…">';
});
document.getElementById('cancelTaskBtn')?.addEventListener('click', () => document.getElementById('taskModalBackdrop').classList.remove('open'));

// Add tag in task modal
document.getElementById('taskTagsWrap')?.addEventListener('keydown', (e) => {
    if (e.target.id === 'newTaskTagInput' && e.key === 'Enter') {
        e.preventDefault();
        const tag = e.target.value.trim();
        if (tag) {
            const chip = document.createElement('span');
            chip.className = 'tag-chip nt-acc';
            chip.innerHTML = `${escapeHtml(tag)} <span class="tag-chip-x" onclick="this.parentElement.remove()">✕</span>`;
            e.target.parentElement.insertBefore(chip, e.target);
            e.target.value = '';
        }
    }
});

// ==================== Schedule ====================
async function loadScheduleWeek() {
    const data = await apiCall('/schedule/week');
    const tasksData = await apiCall('/tasks'); // Fetch tasks for calendar
    const daysContainer = document.getElementById('schedDays');
    if (!daysContainer) return;
    daysContainer.innerHTML = '';
    const weekStart = new Date(data.week_start);
    for (let i = 0; i < 7; i++) {
        const day = new Date(weekStart);
        day.setDate(weekStart.getDate() + i);
        const year = day.getFullYear();
        const month = String(day.getMonth() + 1).padStart(2, '0');
        const d = String(day.getDate()).padStart(2, '0');
        const dateStr = `${year}-${month}-${d}`;
        const blocks = data.days[dateStr] || [];
        const dayTasks = tasksData.tasks.filter(t => t.due_date && t.due_date.startsWith(dateStr));
        const col = document.createElement('div');
        col.className = 'sched-col';
        col.innerHTML = `
            <div class="sched-col-head">
                <div class="sch-day">${day.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()}</div>
                <div class="sch-date">${day.getDate()}</div>
            </div>
            <div class="sched-col-body"></div>
        `;
        const body = col.querySelector('.sched-col-body');
        blocks.forEach(block => {
            const start = new Date(block.start_time);
            const end = new Date(block.end_time);
            const timeStr = `${start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} – ${end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            const blockDiv = document.createElement('div');
            blockDiv.className = `sched-block sb-${block.block_type}`;
            blockDiv.innerHTML = `<div class="sb-time">${timeStr}</div><div class="sb-title">${escapeHtml(block.title || block.block_type)}</div>`;
            body.appendChild(blockDiv);
        });
        // Overlay tasks
        dayTasks.forEach(task => {
            const taskDiv = document.createElement('div');
            taskDiv.className = 'sched-block sb-task';
            taskDiv.style.borderLeftColor = 'var(--acc)';
            taskDiv.style.background = 'var(--acc-bg)';
            taskDiv.innerHTML = `<div class="sb-title" style="color:var(--text);font-size:12px;">❏ ${escapeHtml(task.title || task.content?.substring(0,20) || 'Task')}</div>`;
            taskDiv.onclick = () => openNote(task.id);
            body.appendChild(taskDiv);
        });
        daysContainer.appendChild(col);
    }
    const titleDate = new Date(weekStart);
    const endDate = new Date(weekStart);
    endDate.setDate(weekStart.getDate() + 6);
    document.getElementById('schedTitle').innerHTML = `Week of ${titleDate.toLocaleDateString()} – ${endDate.toLocaleDateString()}`;
}

document.getElementById('prevWeekBtn')?.addEventListener('click', async () => {
    currentWeekOffset--;
    const data = await apiCall(`/schedule/week?offset=${currentWeekOffset}`);
    // Re-fetch with offset; we need to support offset in backend or just reload with a different base date.
    // Simpler: change base date in frontend.
    const newBase = new Date();
    newBase.setDate(newBase.getDate() + currentWeekOffset * 7);
    const year = newBase.getFullYear();
    const month = String(newBase.getMonth() + 1).padStart(2, '0');
    const day = String(newBase.getDate()).padStart(2, '0');
    const res = await apiCall(`/schedule/week?date=${year}-${month}-${day}`);
    // Re-render with res
});
// For brevity, we'll implement the backend offset later; for now just reload without offset.

// New schedule block modal
document.getElementById('newScheduleBlockBtn')?.addEventListener('click', () => document.getElementById('schedModalBackdrop').classList.add('open'));
document.getElementById('addSchedBlockBtn')?.addEventListener('click', async () => {
    const title = document.getElementById('newBlockTitle').value;
    const blockType = document.getElementById('newBlockType').value.toLowerCase().replace(' ', '_');
    const date = document.getElementById('newBlockDate').value;
    const startTime = document.getElementById('newBlockStart').value;
    const endTime = document.getElementById('newBlockEnd').value;
    if (!date || !startTime || !endTime) return;
    await apiCall('/schedule', {
        method: 'POST',
        body: JSON.stringify({
            start_time: `${date}T${startTime}:00`,
            end_time: `${date}T${endTime}:00`,
            block_type: blockType,
            title: title || undefined
        })
    });
    showToast('Block added', 'Schedule updated', 'green');
    document.getElementById('schedModalBackdrop').classList.remove('open');
    loadScheduleWeek();
});
document.getElementById('cancelSchedBtn')?.addEventListener('click', () => document.getElementById('schedModalBackdrop').classList.remove('open'));

// ==================== Graph ====================
async function loadGraph() {
    const [nodes, edges] = await Promise.all([
        apiCall('/graph/nodes'),
        apiCall('/graph/edges')
    ]);
    currentGraphNodes = nodes.nodes;
    currentGraphEdges = edges.edges;
    initGraphCanvas();
}

function initGraphCanvas() {
    const canvas = document.getElementById('graphCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const resize = () => {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        drawGraph();
    };
    window.addEventListener('resize', resize);
    resize();
    function drawGraph() {
        if (!ctx) return;
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        if (!currentGraphNodes.length) return;
        // Simple force layout or just position nodes randomly – for demo, position in a circle
        const centerX = w / 2, centerY = h / 2;
        const radius = Math.min(w, h) * 0.35;
        currentGraphNodes.forEach((node, i) => {
            const angle = (i / currentGraphNodes.length) * Math.PI * 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            node.x = x;
            node.y = y;
        });
        // Draw edges
        currentGraphEdges.forEach(edge => {
            const source = currentGraphNodes.find(n => n.id === edge.source_id);
            const target = currentGraphNodes.find(n => n.id === edge.target_id);
            if (source && target) {
                ctx.beginPath();
                ctx.moveTo(source.x, source.y);
                ctx.lineTo(target.x, target.y);
                ctx.strokeStyle = 'rgba(255,255,255,0.1)';
                ctx.stroke();
            }
        });
        // Draw nodes
        currentGraphNodes.forEach(node => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, 8, 0, Math.PI * 2);
            ctx.fillStyle = node.color || '#6C5CE7';
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = '10px monospace';
            ctx.fillText(node.name, node.x - 12, node.y - 10);
        });
    }
    drawGraph();
}

// ==================== Divergence ====================
async function loadDivergence() {
    const data = await apiCall('/diverge/queue');
    const container = document.getElementById('divergeList');
    if (!container) return;
    container.innerHTML = '';

    // --- Dashboard widget (max 4 items + view all link) ---
    const hudDiv = document.getElementById('hudDiverge');
    if (hudDiv) {
        hudDiv.innerHTML = '';
        let pendingCount = 0;
        data.items.forEach(item => { if (item.status === 'pending') pendingCount++; });
        const previewItems = data.items.slice(0, 4);
        previewItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'hdv';
            div.onclick = () => showPage('diverge');
            div.innerHTML = `
                <div class="hdv-dot"></div>
                <div class="hdv-b">
                    <div class="hdv-title">${escapeHtml(item.suggestion.substring(0, 60))}</div>
                    <div class="hdv-sub">${item.status}</div>
                </div>
                <div class="hdv-arr">↗</div>
            `;
            hudDiv.appendChild(div);
        });
        if (data.items.length > 4) {
            const link = document.createElement('div');
            link.className = 'hdv-viewall';
            link.innerHTML = `<span onclick="showPage('diverge')">view all ${data.items.length} items →</span>`;
            hudDiv.appendChild(link);
        }
        const countEl = document.getElementById('divergeCount');
        if (countEl) countEl.innerText = pendingCount;
        const badgeEl = document.getElementById('divergeHudBadge');
        if (badgeEl) badgeEl.innerText = pendingCount + ' new';
    }

    // --- Full divergence pane ---
    if (data.items.length === 0) {
        container.innerHTML = '<div class="empty-state" style="text-align:center;padding:40px;opacity:0.5">No divergence prompts yet.</div>';
        return;
    }
    data.items.forEach(item => {
        const card = document.createElement('div');
        card.className = `dv-card ${item.status === 'pending' ? 'new' : ''}`;
        card.innerHTML = `
            <div class="dvc-head">
                <div class="dvc-icon" style="background:var(--acc-bg);color:var(--acc2)">📘</div>
                <div class="dvc-title">
                    <div class="dvc-name">${escapeHtml(item.suggestion)}</div>
                    <div class="dvc-sub">${item.status}</div>
                </div>
                ${item.status === 'pending' ? '<span class="dvc-badge">new</span>' : ''}
            </div>
            <div class="dvc-footer">
                <span class="dvc-time">${timeAgo(new Date(item.created_at))}</span>
                <div class="dvc-act">
                    <button class="dvca dvca-dismiss" data-id="${item.id}">dismiss</button>
                    <button class="dvca dvca-go" data-id="${item.id}">accept ✓</button>
                    <button class="dvca dvca-del" data-id="${item.id}">delete</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
    // Attach event listeners after rendering
    document.querySelectorAll('.dvca-dismiss').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            await apiCall(`/diverge/queue/${id}/dismiss`, { method: 'PUT' });
            showToast('Divergence dismissed', 'Removed', 'amber');
            loadDivergence();
        };
    });
    document.querySelectorAll('.dvca-go').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            await apiCall(`/diverge/queue/${id}/accept`, { method: 'PUT' });
            showToast('Divergence accepted', 'Marked accepted', 'green');
            loadDivergence();
        };
    });
    document.querySelectorAll('.dvca-del').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (!confirm('Permanently delete this divergence prompt?')) return;
            await apiCall(`/diverge/queue/${id}`, { method: 'DELETE' });
            showToast('Deleted', 'Prompt removed permanently', 'red');
            loadDivergence();
        };
    });
}

// ==================== Files ====================
async function loadFiles() {
    const data = await apiCall('/files');
    const grid = document.getElementById('filesGrid');
    if (!grid) return;
    grid.innerHTML = '';
    data.files.forEach(file => {
        const card = document.createElement('div');
        card.className = 'file-card';
        card.onclick = () => openNote(file.id);
        const icon = file.file_path?.endsWith('.pdf') ? '📄' : '📝';
        card.innerHTML = `
            <div class="fc-icon">${icon}</div>
            <div class="fc-name">${escapeHtml(file.title)}</div>
            <div class="fc-meta">${timeAgo(new Date(file.updated_at))}</div>
        `;
        grid.appendChild(card);
    });
    document.getElementById('filesCount').innerText = data.files.length;
}

document.getElementById('indexFolderBtn')?.addEventListener('click', async () => {
    await apiCall('/files/reindex', { method: 'POST' });
    showToast('Indexing started', 'Files will be indexed shortly', 'teal');
    setTimeout(loadFiles, 2000);
});

// ==================== Search ====================
async function performSearch(query) {
    if (!query) return;
    const data = await apiCall(`/notes/search?q=${encodeURIComponent(query)}&limit=20`);
    const resultsDiv = document.getElementById('searchResults');
    if (!resultsDiv) return;
    resultsDiv.innerHTML = `
        <div class="sr-section-lbl">semantic matches</div>
        ${data.results.map(r => `
            <div class="sr-item" onclick="openNote('${r.id}')">
                <div class="sr-icon" style="background:var(--acc-bg);color:var(--acc2)">📄</div>
                <div class="sr-body">
                    <div class="sr-title">${escapeHtml(r.title || r.content.substring(0, 50))}</div>
                    <div class="sr-excerpt">${escapeHtml(r.content.substring(0, 150))}…</div>
                </div>
                <div class="sr-meta">${timeAgo(new Date(r.created_at))}</div>
            </div>
        `).join('')}
    `;
}

document.getElementById('globalSearch')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        showPage('search');
        const val = e.target.value;
        document.getElementById('globalSearchPage').value = val;
        performSearch(val);
        e.target.value = '';
    }
});
document.getElementById('globalSearchPage')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') performSearch(e.target.value);
});

// ==================== Chat ====================
async function sendChatMessage(message) {
    const data = await apiCall('/chat', {
        method: 'POST',
        body: JSON.stringify({ message, session_id: chatSessionId })
    });
    if (data.session_id) {
        chatSessionId = data.session_id;
        localStorage.setItem('pcos_chat_session', chatSessionId);
    }
    return data.response;
}

function addChatMessage(role, name, text) {
    const container = document.getElementById('chatMsgs');
    const div = document.createElement('div');
    div.className = `cmsg ${role === 'user' ? 'cmu' : 'cms'}`;
    div.innerHTML = `
        <div class="cmsg-av">${role === 'user' ? 'Y' : 'P'}</div>
        <div class="cmsg-content">
            <div class="cmsg-name">${escapeHtml(name)}</div>
            <div class="cmsg-bub">${escapeHtml(text)}</div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

document.getElementById('sendChatBtn')?.addEventListener('click', async () => {
    const input = document.getElementById('chatIn');
    const msg = input.value.trim();
    if (!msg) return;
    addChatMessage('user', 'You', msg);
    input.value = '';
    const typing = document.createElement('div');
    typing.className = 'cmsg cms';
    typing.innerHTML = '<div class="cmsg-av">P</div><div class="cmsg-content"><div class="cmsg-bub"><div class="tping"><span></span><span></span><span></span></div></div></div>';
    document.getElementById('chatMsgs').appendChild(typing);
    const response = await sendChatMessage(msg);
    typing.remove();
    addChatMessage('assistant', 'pcos', response);
});
document.getElementById('chatIn')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('sendChatBtn').click();
    }
});

// ==================== Quick Capture ====================
let currentCaptureMode = 'note';
document.querySelectorAll('[data-cap-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-cap-mode]').forEach(b => b.classList.remove('act'));
        btn.classList.add('act');
        currentCaptureMode = btn.dataset.capMode;
        const ic = document.getElementById('capIc');
        if (currentCaptureMode === 'task') ic.style.background = 'var(--amber-bg)';
        else if (currentCaptureMode === 'idea') ic.style.background = 'var(--green-bg)';
        else ic.style.background = 'var(--acc-bg)';
    });
});

async function saveQuickCapture(content) {
    let type = 'note';
    if (currentCaptureMode === 'task') type = 'task';
    if (currentCaptureMode === 'idea') type = 'idea';
    await apiCall('/capture', {
        method: 'POST',
        body: JSON.stringify({ content, source: 'webapp', type, is_task: type === 'task' })
    });
    showToast('Captured', `Saved as ${currentCaptureMode}`, 'green');
    loadNotes();
    loadTasks();
}

document.getElementById('capIn')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const val = document.getElementById('capIn').value.trim();
        if (val) {
            saveQuickCapture(val);
            document.getElementById('captureBackdrop').classList.remove('open');
            document.getElementById('capIn').value = '';
        }
    }
});

// ==================== Navigation / Page Switching ====================
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${pageId}`).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('act'));
    const navItem = document.getElementById(`ni-${pageId}`);
    if (navItem) navItem.classList.add('act');
    if (pageId === 'hud') loadDashboard();
    if (pageId === 'notes') loadNotes();
    if (pageId === 'tasks') loadTasks();
    if (pageId === 'schedule') loadScheduleWeek();
    if (pageId === 'graph') loadGraph();
    if (pageId === 'diverge') loadDivergence();
    if (pageId === 'files') loadFiles();
    if (pageId === 'search') document.getElementById('globalSearchPage')?.focus();
    const topbarCTA = document.getElementById('topbarCTA');
    if (pageId === 'notes') topbarCTA.innerHTML = '<svg viewBox="0 0 12 12"><path d="M6 2v8M2 6h8"/></svg>New Note';
    else if (pageId === 'tasks') topbarCTA.innerHTML = '<svg viewBox="0 0 12 12"><path d="M6 2v8M2 6h8"/></svg>New Task';
    else topbarCTA.style.display = 'none';
}

// Attach navigation listeners
document.getElementById('ni-hud')?.addEventListener('click', () => showPage('hud'));
document.getElementById('ni-notes')?.addEventListener('click', () => showPage('notes'));
document.getElementById('ni-tasks')?.addEventListener('click', () => showPage('tasks'));
document.getElementById('ni-schedule')?.addEventListener('click', () => showPage('schedule'));
document.getElementById('ni-chat')?.addEventListener('click', () => showPage('chat'));
document.getElementById('ni-graph')?.addEventListener('click', () => showPage('graph'));
document.getElementById('ni-diverge')?.addEventListener('click', () => showPage('diverge'));
document.getElementById('ni-search')?.addEventListener('click', () => showPage('search'));
document.getElementById('ni-files')?.addEventListener('click', () => showPage('files'));
document.getElementById('quickCaptureBtn')?.addEventListener('click', () => document.getElementById('captureBackdrop').classList.add('open'));
document.getElementById('cmdPalBtn')?.addEventListener('click', () => document.getElementById('cmdPalBackdrop').classList.add('open'));
document.getElementById('hudViewAllNotes')?.addEventListener('click', () => showPage('notes'));
document.getElementById('hudViewAllTasks')?.addEventListener('click', () => showPage('tasks'));
document.getElementById('hudViewSchedule')?.addEventListener('click', () => showPage('schedule'));
document.getElementById('topbarCTA')?.addEventListener('click', () => {
    const activePage = document.querySelector('.page.active').id;
    if (activePage === 'page-notes') {
        startNewNote();
    } else if (activePage === 'page-tasks') {
        document.getElementById('newTaskBtn').click();
    }
});

// Command palette
const cpIn = document.getElementById('cpIn');
cpIn?.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        const val = cpIn.value.trim();
        if (val.startsWith('?')) {
            showPage('chat');
            document.getElementById('chatIn').value = val.slice(1);
            document.getElementById('sendChatBtn').click();
        } else {
            showPage('search');
            document.getElementById('globalSearchPage').value = val;
            await performSearch(val);
        }
        document.getElementById('cmdPalBackdrop').classList.remove('open');
        cpIn.value = '';
    }
});

// Close modals
document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('open');
    });
    backdrop.querySelector('.modal-close')?.addEventListener('click', () => backdrop.classList.remove('open'));
});

// ==================== Initial Data Load ====================
async function loadDashboard() {
    const notes = await loadNotes();
    const recent = notes.slice(0, 4);
    const hudRecent = document.getElementById('hudRecentNotes');
    if (hudRecent) {
        hudRecent.innerHTML = recent.map(n => `
            <div class="hnr" onclick="openNote('${n.id}')">
                <div class="hnr-pip" style="background:var(--acc)"></div>
                <div class="hnr-txt">${escapeHtml(n.title || n.content.substring(0, 50))}</div>
                <span class="hnr-t">${timeAgo(new Date(n.created_at))}</span>
            </div>
        `).join('');
        if (recent.length === 0) hudRecent.innerHTML = '<div class="empty-state" style="grid-column:1/-1;text-align:center;padding:20px">No notes yet. Create one.</div>';
    }
    const tasks = await loadTasks(); // updates counts
    const openTasksDiv = document.getElementById('hudOpenTasks');
    if (openTasksDiv) {
        // We need to fetch open tasks again
        const tasksData = await apiCall('/tasks');
        const openTasks = tasksData.tasks.filter(t => t.status !== 'done').slice(0, 3);
        openTasksDiv.innerHTML = openTasks.map(t => `
            <div class="htr">
                <div class="chk" onclick="event.stopPropagation(); completeTask('${t.id}', this)"></div>
                <div class="pri ${t.priority === 'high' ? 'ph' : (t.priority === 'medium' ? 'pm' : 'pl')}"></div>
                <span class="htr-txt">${escapeHtml(t.title || t.content?.substring(0, 50) || 'Untitled')}</span>
            </div>
        `).join('');
        if (openTasks.length === 0) openTasksDiv.innerHTML = '<div class="empty-state" style="text-align:center;padding:12px">No open tasks.</div>';
    }
    // Fetch today's schedule for dashboard
    const hudSched = document.getElementById('hudSchedulePreview');
    if (hudSched) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        const dateStr = `${year}-${month}-${day}`;
        const schedData = await apiCall(`/schedule/week?date=${dateStr}`);
        const todayBlocks = schedData.days[dateStr] || [];
        hudSched.innerHTML = todayBlocks.slice(0, 4).map(b => {
            const start = new Date(b.start_time);
            return `<div class="htr" onclick="showPage('schedule')"><div class="pri ${b.block_type === 'deep_work' ? 'ph' : 'pm'}"></div><span class="htr-txt">${start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} – ${escapeHtml(b.title || b.block_type)}</span></div>`;
        }).join('');
        if (todayBlocks.length === 0) hudSched.innerHTML = '<div class="empty-state" style="text-align:center;padding:12px">No events scheduled.</div>';
    }
    const stats = document.getElementById('hudStats');
    if (stats) {
        stats.innerHTML = `
            <div class="stat"><div class="stat-v">${notes.length}</div><div class="stat-l">notes</div></div>
            <div class="stat"><div class="stat-v">0</div><div class="stat-l">tasks</div></div>
            <div class="stat"><div class="stat-v">0</div><div class="stat-l">focus pts</div></div>
            <div class="stat"><div class="stat-v">${currentGraphNodes.length}</div><div class="stat-l">nodes</div></div>
        `;
    }
}

window.completeTask = async (id, el) => {
    await apiCall(`/tasks/${id}`, { 
        method: 'PUT',
        body: JSON.stringify({ status: 'done' })
    });
    el.classList.add('done');
    el.closest('.htr').style.opacity = '0.38';
    el.closest('.htr').querySelector('.htr-txt')?.classList.add('done');
    showToast('Task completed', 'Good job!', 'green');
    loadTasks();
    loadDashboard();
};

// Start everything
loadDashboard();
loadDivergence();
loadScheduleWeek();
loadFiles();
loadGraph();