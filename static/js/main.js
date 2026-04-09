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

    // Build one deck card HTML per deck and join them all together.
    // Template literals (backtick strings) allow multi-line HTML with
    // ${...} variable interpolation — same idea as Python f-strings.
    grid.innerHTML = decks.map(deck => `
        <div class="deck-card" onclick="openDeck(${deck.deck_id})">

            <!-- Avatar thumbnail — shows card art or "?" placeholder -->
            <div class="deck-card-avatar">
                ${deck.avatar_image
                    ? `<img src="${deck.avatar_image}" alt="Avatar" loading="lazy">`
                    : `<span class="deck-card-avatar-placeholder">?</span>`
                }
            </div>

            <div class="deck-card-name">${deck.name}</div>
            <div class="deck-card-meta">Created ${formatDate(deck.created_at)}</div>

            <div class="deck-card-actions">
                <!-- event.stopPropagation() prevents the click bubbling up to
                     the parent div's onclick which would open the deck -->
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

    // POST /decks with JSON body matching the DeckCreate Pydantic model
    const response = await fetch('/decks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });

    if (response.ok) {
        closeCreateModal();
        loadDecks();  // refresh the grid to show the new deck
    }
}


// ============================================================
// Delete deck modal
// Requires typing the exact deck name to confirm — prevents accidents
// ============================================================
function openDeleteModal(deckId, deckName) {
    deckToDelete = { id: deckId, name: deckName };
    document.getElementById('delete-deck-name').textContent = deckName;
    document.getElementById('delete-modal-overlay').classList.add('open');
    // Reset border colour in case it was turned red from a previous failed attempt
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

    // Highlight input red if name doesn't match
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
