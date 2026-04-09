// ============================================================
// State
// ============================================================
let deckToDelete = null;  // tracks which deck the delete modal is targeting


// ============================================================
// On page load — fetch all decks from the API and render them
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDecks();
});


// ============================================================
// Load and render the deck grid
// GET /decks returns [{deck_id, name, created_at, avatar_image}]
// avatar_image is the image_url of the avatar zone card, or null
// ============================================================
async function loadDecks() {
    const grid = document.getElementById('deck-grid');
    grid.innerHTML = '<div class="loading">Loading decks...</div>';

    const response = await fetch('/decks');
    const decks = await response.json();

    if (decks.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <h3>No decks yet</h3>
                <p>Click "+ New Deck" to create your first deck</p>
            </div>`;
        return;
    }

    grid.innerHTML = decks.map(deck => `
        <div class="deck-card" onclick="openDeck(${deck.deck_id})">

            <div class="deck-card-avatar">
                ${deck.avatar_image
                    ? `<img src="${deck.avatar_image}" alt="Avatar" loading="lazy">`
                    : `<span class="deck-card-avatar-placeholder">?</span>`
                }
            </div>

            <div class="deck-card-name">${deck.name}</div>
            <div class="deck-card-meta">Created ${formatDate(deck.created_at)}</div>

            <div class="deck-card-actions">
                <button class="btn btn-secondary"
                    onclick="event.stopPropagation(); openDeck(${deck.deck_id})">Open</button>
                <button class="btn btn-danger"
                    onclick="event.stopPropagation(); openDeleteModal(${deck.deck_id}, '${deck.name.replace(/'/g, "\\'")}')">Delete</button>
            </div>
        </div>
    `).join('');
}


// ============================================================
// Create deck modal
// ============================================================
function openCreateModal() {
    document.getElementById('modal-overlay').classList.add('open');
    setTimeout(() => document.getElementById('deck-name-input').focus(), 50);
}

function closeCreateModal() {
    document.getElementById('modal-overlay').classList.remove('open');
    document.getElementById('deck-name-input').value = '';
}

async function createDeck() {
    const name = document.getElementById('deck-name-input').value.trim();
    if (!name) return;

    const response = await fetch('/decks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });

    if (response.ok) {
        closeCreateModal();
        loadDecks();
    }
}


// ============================================================
// Import from Curiosa modal
// ============================================================
function openImportModal() {
    document.getElementById('import-modal-overlay').classList.add('open');
    document.getElementById('import-result').style.display = 'none';
    document.getElementById('import-result').textContent = '';
    document.getElementById('import-btn').disabled = false;
    document.getElementById('import-btn').textContent = 'Import';
    setTimeout(() => document.getElementById('curiosa-url-input').focus(), 50);
}

function closeImportModal() {
    document.getElementById('import-modal-overlay').classList.remove('open');
    document.getElementById('curiosa-url-input').value = '';
    document.getElementById('import-result').style.display = 'none';
}

async function importCuriosaDeck() {
    const url = document.getElementById('curiosa-url-input').value.trim();
    if (!url) return;

    const btn = document.getElementById('import-btn');
    const resultEl = document.getElementById('import-result');

    // Disable button and show loading state while request is in flight
    btn.disabled = true;
    btn.textContent = 'Importing...';
    resultEl.style.display = 'none';
    resultEl.className = 'import-result';

    const response = await fetch('/decks/import-curiosa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ curiosa_url: url })
    });

    const data = await response.json();

    if (response.ok) {
        // Build a success message summarising the import
        let msg = `✓ "${data.deck_name}" imported — ${data.imported} card(s) added.`;
        if (data.unmatched.length > 0) {
            msg += ` ${data.unmatched.length} card(s) not found in database: ${data.unmatched.join(', ')}.`;
        }
        resultEl.textContent = msg;
        resultEl.classList.add('import-result--success');
        resultEl.style.display = 'block';

        // Refresh the deck grid so the new deck appears immediately
        loadDecks();

        // Reset button — user can close manually or import another
        btn.disabled = false;
        btn.textContent = 'Import Another';
    } else {
        // Show the error message from the API
        const detail = data.detail || 'Import failed. Check the URL and try again.';
        resultEl.textContent = `✗ ${detail}`;
        resultEl.classList.add('import-result--error');
        resultEl.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Import';
    }
}


// ============================================================
// Delete deck modal
// ============================================================
function openDeleteModal(deckId, deckName) {
    deckToDelete = { id: deckId, name: deckName };
    document.getElementById('delete-deck-name').textContent = deckName;
    document.getElementById('delete-modal-overlay').classList.add('open');
    document.getElementById('delete-confirm-input').style.borderColor = '';
    setTimeout(() => document.getElementById('delete-confirm-input').focus(), 50);
}

function closeDeleteModal() {
    document.getElementById('delete-modal-overlay').classList.remove('open');
    document.getElementById('delete-confirm-input').value = '';
    deckToDelete = null;
}

async function confirmDelete() {
    const input = document.getElementById('delete-confirm-input').value.trim();

    if (input !== deckToDelete.name) {
        document.getElementById('delete-confirm-input').style.borderColor = 'var(--accent-danger)';
        return;
    }

    const response = await fetch(`/decks/${deckToDelete.id}`, { method: 'DELETE' });

    if (response.ok) {
        closeDeleteModal();
        loadDecks();
    }
}


// ============================================================
// Navigation
// ============================================================
function openDeck(deckId) {
    window.location.href = `/deck/${deckId}`;
}


// ============================================================
// Utilities
// ============================================================
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
