// ============================================================
// State — keeps track of which deck is being deleted
// ============================================================
let deckToDelete = null;


// ============================================================
// On page load — fetch all decks and render them
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDecks();
});


// ============================================================
// Load and render decks
// ============================================================
async function loadDecks() {
    const grid = document.getElementById('deck-grid');
    grid.innerHTML = '<div class="loading">Loading decks...</div>';

    // fetch() sends an HTTP GET request to your FastAPI /decks endpoint
    // await means "wait for the response before continuing"
    const response = await fetch('/decks');
    const decks = await response.json();

    if (decks.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <h3>No decks yet</h3>
                <p>Create your first deck to get started</p>
            </div>
        `;
        return;
    }

    // Build HTML for each deck and join them together
    grid.innerHTML = decks.map(deck => `
        <div class="deck-card" onclick="openDeck(${deck.deck_id})">
            <div class="deck-card-name">${deck.name}</div>
            <div class="deck-card-meta">Created ${formatDate(deck.created_at)}</div>
            <div class="deck-card-actions">
                <button class="btn btn-secondary" onclick="event.stopPropagation(); openDeck(${deck.deck_id})">Open</button>
                <button class="btn btn-danger" onclick="event.stopPropagation(); openDeleteModal(${deck.deck_id}, '${deck.name}')">Delete</button>
            </div>
        </div>
    `).join('');
}


// ============================================================
// Create deck modal
// ============================================================
function openCreateModal() {
    document.getElementById('modal-overlay').classList.add('open');
    // Focus the input so the user can start typing immediately
    setTimeout(() => document.getElementById('deck-name-input').focus(), 50);
}

function closeCreateModal() {
    document.getElementById('modal-overlay').classList.remove('open');
    document.getElementById('deck-name-input').value = '';
}

async function createDeck() {
    const name = document.getElementById('deck-name-input').value.trim();
    if (!name) return;

    // POST request with a JSON body — mirrors the DeckCreate Pydantic model
    const response = await fetch('/decks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
    });

    if (response.ok) {
        closeCreateModal();
        loadDecks(); // Refresh the deck list
    }
}


// ============================================================
// Delete deck modal
// ============================================================
function openDeleteModal(deckId, deckName) {
    deckToDelete = { id: deckId, name: deckName };
    document.getElementById('delete-deck-name').textContent = deckName;
    document.getElementById('delete-modal-overlay').classList.add('open');
    setTimeout(() => document.getElementById('delete-confirm-input').focus(), 50);
}

function closeDeleteModal() {
    document.getElementById('delete-modal-overlay').classList.remove('open');
    document.getElementById('delete-confirm-input').value = '';
    deckToDelete = null;
}

async function confirmDelete() {
    const input = document.getElementById('delete-confirm-input').value.trim();

    // Only delete if the user typed the exact deck name
    if (input !== deckToDelete.name) {
        document.getElementById('delete-confirm-input').style.borderColor = 'var(--accent-danger)';
        return;
    }

    // DELETE request to the API
    const response = await fetch(`/decks/${deckToDelete.id}`, {
        method: 'DELETE'
    });

    if (response.ok) {
        closeDeleteModal();
        loadDecks(); // Refresh the deck list
    }
}


// ============================================================
// Navigation
// ============================================================
function openDeck(deckId) {
    // Navigate to the deck editor page — we'll build this next
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
