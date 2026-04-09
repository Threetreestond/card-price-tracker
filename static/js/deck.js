// ============================================================
// State
// ============================================================
// Extract deck ID from URL — /deck/3 gives us 3
const deckId = window.location.pathname.split('/').pop();
let deckData = null;       // full deck data from API
let activeZone = 'all';    // which zone tab is selected
let searchTimeout = null;  // debounce timer for search


// ============================================================
// On page load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDeck();
});


// ============================================================
// Load deck data from API
// ============================================================
async function loadDeck() {
    const response = await fetch(`/decks/${deckId}`);
    deckData = await response.json();

    // Update page title
    document.title = `${deckData.deck_name} — Sorcery Tracker`;
    document.getElementById('deck-title').textContent = deckData.deck_name;
    document.getElementById('deck-created').textContent = `Created ${formatDate(deckData.deck_created)}`;

    renderCardList();
    renderStats();
}


// ============================================================
// Render the card list filtered by active zone
// ============================================================
function renderCardList() {
    const list = document.getElementById('card-list');

    // Filter cards by active zone (or show all)
    const cards = activeZone === 'all'
        ? deckData.cards
        : deckData.cards.filter(c => c.zone === activeZone);

    if (cards.length === 0) {
        list.innerHTML = `<div class="empty-state" style="padding: 2rem 0;"><p>No cards in this zone</p></div>`;
        return;
    }

    if (activeZone === 'all') {
        // Group by zone
        const zones = ['avatar', 'maindeck', 'sitedeck', 'collection', 'maybeboard'];
        let html = '';
        for (const zone of zones) {
            const zoneCards = cards.filter(c => c.zone === zone);
            if (zoneCards.length === 0) continue;
            const total = zoneCards.reduce((sum, c) => sum + c.quantity, 0);
            html += `<div class="zone-section">
                <div class="zone-section-title">${formatZoneName(zone)} (${total})</div>
                ${zoneCards.map(c => cardRowHTML(c)).join('')}
            </div>`;
        }
        // Cards with null zone
        const nullCards = cards.filter(c => !c.zone);
        if (nullCards.length > 0) {
            html += `<div class="zone-section">
                <div class="zone-section-title">Unassigned</div>
                ${nullCards.map(c => cardRowHTML(c)).join('')}
            </div>`;
        }
        list.innerHTML = html || '<div class="empty-state" style="padding: 2rem 0;"><p>No cards yet</p></div>';
    } else {
        list.innerHTML = cards.map(c => cardRowHTML(c)).join('');
    }
}

function cardRowHTML(card) {
    return `
        <div class="card-row">
            <span class="card-row-qty">${card.quantity}×</span>
            <span class="card-row-name">${card.name}</span>
            <span class="card-row-meta">
                <span>${card.element || '—'}</span>
                <span>${card.cost !== null ? card.cost : '—'}</span>
                <span>${card.rarity || ''}</span>
            </span>
            <div class="card-row-actions">
                <button class="btn-icon" onclick="incrementCard(${card.product_id}, '${card.zone}')" title="Add one">+</button>
                <button class="btn-icon" onclick="decrementCard(${card.product_id}, '${card.zone}')" title="Remove one">−</button>
                <button class="btn-icon danger" onclick="removeCard(${card.product_id}, '${card.zone}')" title="Remove all">×</button>
            </div>
        </div>
    `;
}


// ============================================================
// Zone tab switching
// ============================================================
function switchZone(zone, btn) {
    activeZone = zone;
    document.querySelectorAll('.zone-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    renderCardList();
}


// ============================================================
// Stats panel
// ============================================================
function renderStats() {
    const cards = deckData.cards;

    // Count totals per zone
    const countByZone = (zone) => cards
        .filter(c => c.zone === zone)
        .reduce((sum, c) => sum + c.quantity, 0);

    const total = cards.reduce((sum, c) => sum + c.quantity, 0);

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-maindeck').textContent = countByZone('maindeck');
    document.getElementById('stat-sitedeck').textContent = countByZone('sitedeck');
    document.getElementById('stat-collection').textContent = countByZone('collection');

    renderManaCurve();
    renderElementDistribution();
    renderTypeDistribution();
}


// ============================================================
// Mana curve (maindeck only, excludes X and null cost)
// ============================================================
function renderManaCurve() {
    const maindeck = deckData.cards.filter(c => c.zone === 'maindeck');

    // Build cost counts 0–10
    const costs = {};
    for (let i = 0; i <= 10; i++) costs[String(i)] = 0;

    for (const card of maindeck) {
        if (card.cost && card.cost !== 'X' && costs[card.cost] !== undefined) {
            costs[card.cost] += card.quantity;
        }
    }

    const maxCount = Math.max(...Object.values(costs), 1);
    const barsEl = document.getElementById('mana-bars');
    const labelsEl = document.getElementById('mana-labels');

    barsEl.innerHTML = Object.entries(costs).map(([cost, count]) => `
        <div class="chart-bar-wrap">
            <div class="chart-bar" style="height: ${(count / maxCount) * 100}%;" title="${count} card${count !== 1 ? 's' : ''} at cost ${cost}"></div>
        </div>
    `).join('');

    labelsEl.innerHTML = Object.keys(costs).map(cost => `
        <div class="chart-label">${cost}</div>
    `).join('');
}


// ============================================================
// Element distribution
// ============================================================
function renderElementDistribution() {
    const maindeck = deckData.cards.filter(c => c.zone === 'maindeck');
    const elementColours = { Fire: 'bar-fire', Water: 'bar-water', Earth: 'bar-earth', Air: 'bar-air' };

    const counts = {};
    for (const card of maindeck) {
        if (!card.element) {
            counts['None'] = (counts['None'] || 0) + card.quantity;
            continue;
        }
        for (const el of card.element.split(';')) {
            counts[el] = (counts[el] || 0) + card.quantity;
        }
    }

    const max = Math.max(...Object.values(counts), 1);
    const el = document.getElementById('element-list');
    el.innerHTML = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => `
            <div class="element-row">
                <span class="element-label">${name}</span>
                <div class="element-bar-bg">
                    <div class="element-bar ${elementColours[name] || 'bar-none'}" style="width: ${(count / max) * 100}%"></div>
                </div>
                <span class="element-count">${count}</span>
            </div>
        `).join('');
}


// ============================================================
// Card type distribution
// ============================================================
function renderTypeDistribution() {
    const maindeck = deckData.cards.filter(c => c.zone === 'maindeck');
    const counts = {};

    for (const card of maindeck) {
        const type = card.card_type || 'Unknown';
        counts[type] = (counts[type] || 0) + card.quantity;
    }

    const max = Math.max(...Object.values(counts), 1);
    const el = document.getElementById('type-list');
    el.innerHTML = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => `
            <div class="element-row">
                <span class="element-label">${name}</span>
                <div class="element-bar-bg">
                    <div class="element-bar bar-default" style="width: ${(count / max) * 100}%"></div>
                </div>
                <span class="element-count">${count}</span>
            </div>
        `).join('');
}


// ============================================================
// Card actions (add / remove)
// ============================================================
async function incrementCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, zone: zone, quantity: 1 })
    });
    await loadDeck();
}

async function decrementCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards/${productId}?zone=${zone}&remove_all=false&quantity=1`, {
        method: 'DELETE'
    });
    await loadDeck();
}

async function removeCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards/${productId}?zone=${zone}&remove_all=true`, {
        method: 'DELETE'
    });
    await loadDeck();
}


// ============================================================
// Add card modal
// ============================================================
function openAddCardModal() {
    document.getElementById('add-card-overlay').classList.add('open');
    setTimeout(() => document.getElementById('search-name').focus(), 50);
}

function closeAddCardModal() {
    document.getElementById('add-card-overlay').classList.remove('open');
    document.getElementById('search-name').value = '';
    document.getElementById('search-results').innerHTML = '<p class="search-hint">Search for a card above to add it to your deck</p>';
}

function searchCards() {
    // Debounce — wait 300ms after user stops typing before searching
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(doSearch, 300);
}

async function doSearch() {
    const name = document.getElementById('search-name').value.trim();
    const element = document.getElementById('search-element').value;
    const cardType = document.getElementById('search-type').value;

    if (!name && !element && !cardType) {
        document.getElementById('search-results').innerHTML = '<p class="search-hint">Search for a card above to add it to your deck</p>';
        return;
    }

    // Build query string from non-empty filters
    const params = new URLSearchParams();
    if (element) params.append('element', element);
    if (cardType) params.append('card_type', cardType);
    params.append('foil', 'false');

    const response = await fetch(`/cards?${params.toString()}`);
    let cards = await response.json();

    // Filter by name client-side (case insensitive)
    if (name) {
        cards = cards.filter(c => c.clean_name.toLowerCase().includes(name.toLowerCase()));
    }

    // Limit to 50 results for performance
    cards = cards.slice(0, 50);

    const resultsEl = document.getElementById('search-results');

    if (cards.length === 0) {
        resultsEl.innerHTML = '<p class="search-hint">No cards found</p>';
        return;
    }

    resultsEl.innerHTML = cards.map(card => `
        <div class="search-result-row">
            <span class="search-result-name">${card.name}</span>
            <span class="search-result-meta">
                <span>${card.element || '—'}</span>
                <span>Cost ${card.cost !== null ? card.cost : '—'}</span>
                <span class="badge badge-rarity-${(card.rarity || '').toLowerCase()}">${card.rarity || ''}</span>
            </span>
            <button class="btn-add-card" onclick="addCardFromSearch(${card.product_id})">+ Add</button>
        </div>
    `).join('');
}

async function addCardFromSearch(productId) {
    const zone = document.getElementById('add-zone').value;
    await fetch(`/decks/${deckId}/cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, zone: zone, quantity: 1 })
    });
    // Reload deck data so counts update
    await loadDeck();
}


// ============================================================
// Utilities
// ============================================================
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatZoneName(zone) {
    const names = {
        maindeck: 'Maindeck',
        sitedeck: 'Site Deck',
        collection: 'Collection',
        avatar: 'Avatar',
        maybeboard: 'Maybeboard'
    };
    return names[zone] || zone;
}
