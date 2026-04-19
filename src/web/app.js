let entries = [];
let filteredEntries = [];
let selectedIndex = 0;
let isDarkMode = true;
let imageLabelText = "Image";

const historyList = document.getElementById('history-list');
const searchInput = document.getElementById('search');
const themeToggle = document.getElementById('theme-toggle');

async function loadHistory() {
    try {
        entries = await window.pywebview.api.getHistory();
        filterEntries();
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

function filterEntries() {
    const query = searchInput.value.toLowerCase().trim();
    
    if (!query) {
        filteredEntries = [...entries];
    } else {
        filteredEntries = entries.filter(entry => {
            if (entry.isImage) {
                const imageLabel = imageLabelText.toLowerCase();
                return query === imageLabel || query === 'image';
            }
            return entry.content.toLowerCase().includes(query);
        });
    }
    
    selectedIndex = 0;
    render();
}

function render() {
    if (filteredEntries.length === 0) {
        historyList.innerHTML = '<div class="empty-state">No clipboard history</div>';
        return;
    }
    
    historyList.innerHTML = filteredEntries.map((entry, index) => {
        const isSelected = index === selectedIndex;
        const pinIcon = entry.isPinned ? '\uE840' : '\uE718';
        
        let contentHtml = '';
        if (entry.isImage) {
            contentHtml = `
                <img src="${entry.imagePath || ''}" class="item-image" alt="Image" onerror="this.style.display='none'">
                <div class="item-content">
                    <div class="item-text">[${imageLabelText}] ${formatTime(entry.timestamp)}</div>
                </div>
            `;
        } else {
            const preview = entry.content.length > 60 ? entry.content.substring(0, 60) + '...' : entry.content;
            contentHtml = `
                <div class="item-content">
                    <div class="item-text">${escapeHtml(preview)}</div>
                    <div class="item-meta">${formatTime(entry.timestamp)}</div>
                </div>
            `;
        }
        
        return `
            <div class="item ${isSelected ? 'selected' : ''}" data-index="${index}" data-hash="${entry.contentHash}">
                ${contentHtml}
                <div class="item-actions">
                    <button class="action-btn" data-action="pin" data-index="${index}" title="Pin">${pinIcon}</button>
                    <button class="action-btn danger" data-action="remove" data-index="${index}" title="Remove">&#xE74D;</button>
                </div>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function selectItem(index) {
    if (index < 0) index = filteredEntries.length - 1;
    if (index >= filteredEntries.length) index = 0;
    selectedIndex = index;
    render();
    
    const item = historyList.children[selectedIndex];
    if (item) {
        item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
}

async function copyEntry(index) {
    const entry = filteredEntries[index];
    if (!entry) return;
    
    try {
        await window.pywebview.api.copyEntry(entry.contentHash);
    } catch (e) {
        console.error('Failed to copy:', e);
    }
}

async function pinEntry(index) {
    const entry = filteredEntries[index];
    if (!entry) return;
    
    try {
        await window.pywebview.api.pinEntry(entry.contentHash);
        await loadHistory();
    } catch (e) {
        console.error('Failed to pin:', e);
    }
}

async function removeEntry(index) {
    const entry = filteredEntries[index];
    if (!entry) return;
    
    try {
        await window.pywebview.api.removeEntry(entry.contentHash);
        await loadHistory();
    } catch (e) {
        console.error('Failed to remove:', e);
    }
}

async function toggleTheme() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('light', !isDarkMode);
    themeToggle.innerHTML = isDarkMode ? '\uE708' : '\uE706';
    
    try {
        await window.pywebview.api.setTheme(isDarkMode);
    } catch (e) {
        console.error('Failed to save theme:', e);
    }
}

function closeWindow() {
    try {
        window.pywebview.api.closeWindow();
    } catch (e) {
        console.error('Failed to close:', e);
    }
}

searchInput.addEventListener('input', filterEntries);

historyList.addEventListener('click', (e) => {
    const actionBtn = e.target.closest('.action-btn');
    if (actionBtn) {
        const action = actionBtn.dataset.action;
        const index = parseInt(actionBtn.dataset.index);
        
        if (action === 'pin') {
            pinEntry(index);
        } else if (action === 'remove') {
            removeEntry(index);
        }
        return;
    }
    
    const item = e.target.closest('.item');
    if (item) {
        const index = parseInt(item.dataset.index);
        copyEntry(index);
    }
});

const previewPopup = document.createElement('div');
previewPopup.id = 'image-preview-popup';
document.body.appendChild(previewPopup);

historyList.addEventListener('mouseover', (e) => {
    if (e.target.classList.contains('item-image')) {
        previewPopup.style.backgroundImage = `url(${e.target.src})`;
        previewPopup.style.display = 'block';
    }
});

historyList.addEventListener('mousemove', (e) => {
    if (previewPopup.style.display === 'block') {
        const x = e.clientX + 15;
        const y = e.clientY + 15;
        const maxX = window.innerWidth - 260;
        const maxY = window.innerHeight - 260;
        previewPopup.style.left = `${Math.min(x, maxX)}px`;
        previewPopup.style.top = `${Math.min(y, maxY)}px`;
    }
});

historyList.addEventListener('mouseout', (e) => {
    if (e.target.classList.contains('item-image')) {
        previewPopup.style.display = 'none';
    }
});

document.addEventListener('keydown', (e) => {
    if (e.target === searchInput) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectItem(selectedIndex + 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectItem(selectedIndex - 1);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            copyEntry(selectedIndex);
        }
        return;
    }
    
    switch (e.key) {
        case 'ArrowDown':
        case 'j':
            e.preventDefault();
            selectItem(selectedIndex + 1);
            break;
        case 'ArrowUp':
        case 'k':
            e.preventDefault();
            selectItem(selectedIndex - 1);
            break;
        case 'Enter':
        case ' ':
            e.preventDefault();
            copyEntry(selectedIndex);
            break;
        case 'Delete':
        case 'Backspace':
            e.preventDefault();
            removeEntry(selectedIndex);
            break;
        case 'p':
            e.preventDefault();
            pinEntry(selectedIndex);
            break;
        case 'Escape':
            e.preventDefault();
            closeWindow();
            break;
    }
});

themeToggle.addEventListener('click', toggleTheme);

window.addEventListener('pywebviewready', async function() {
    try {
        imageLabelText = await window.pywebview.api.getImageLabel();
    } catch(e) {}
    await loadHistory();
});

window.refreshData = async function() {
    await loadHistory();
};

window.setTheme = function(dark) {
    isDarkMode = dark;
    document.body.classList.toggle('light', !isDarkMode);
    themeToggle.innerHTML = isDarkMode ? '\uE708' : '\uE706';
};

window.onerror = function(msg, url, line) {
    console.error('JS Error:', msg, 'at', line);
};
