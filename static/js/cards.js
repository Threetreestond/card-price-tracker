// ============================================================
// State
// ============================================================
let allCards = [];        // raw results from API (includes all printings)
let groupedCards = [];    // [{cleanName, cards:[...printings]}] — one entry per unique card name
let searchTimeout = null;

const RARITY_ORDER = { Ordinary: 0, Exceptional: 1, Elite: 2, Unique: 3 };

const SET_NAMES = {
    23335: 'Alpha', 23336: 'Beta', 23588: 'Arthurian Legends',
    23778: 'Arthurian Legends Promo', 23514: 'Dust Reward Promos',
    24378: 'Dragonlord', 24471: 'Gothic'
};


// ============================================================
// On page load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const setSelect = document.getElementById('filter-set');
    for (const [id, name] of Object.entries(SET_NAMES)) {
        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = name;
        setSelect.appendChild(opt);
    }
    fetchCards();
});


// ============================================================
// Fetch from API and group by clean_name
// Cards with the same clean_name (e.g. "Accursed Albatross" across
// Alpha and Beta) are merged into one gallery tile. The panel
// lets you switch between set versions.
// ============================================================
async function fetchCards() {
    document.getElementById('card-gallery').innerHTML =
        '<div class="loading" style="grid-column:1/-1">Loading...</div>';

    const params = new URLSearchParams();
    const groupId  = document.getElementById('filter-set').value;
    const element  = document.getElementById('filter-element').value;
    const cardType = document.getElementById('filter-type').value;
    const rarity   = document.getElementById('filter-rarity').value;
    const cost     = document.getElementById('filter-cost').value;
    const foilOnly = document.getElementById('filter-foil').checked;

    if (groupId)  params.append('group_id', groupId);
    if (element)  params.append('element', element);
    if (cardType) params.append('card_type', cardType);
    if (rarity)   params.append('rarity', rarity);
    if (cost)     params.append('cost', cost);
    // Default to non-foil unless foil-only is checked
    params.append('foil', foilOnly ? 'true' : 'false');

    const response = await fetch(`/cards?${params.toString()}`);
    allCards = await response.json();

    // Group cards by clean_name so each unique card name gets one tile.
    // Within each group, cards are sorted by set chronologically.
    const map = new Map();
    for (const card of allCards) {
        const key = card.clean_name || card.name;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(card);
    }
    // Convert map to array of {cleanName, cards} objects
    groupedCards = Array.from(map.entries()).map(([cleanName, cards]) => ({
        cleanName,
        cards: cards.sort((a, b) => a.group_id - b.group_id)  // oldest set first
    }));

    applyNameFilter();
}

function debouncedSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(applyNameFilter, 300);
}

function applyNameFilter() {
    const name = document.getElementById('filter-name').value.trim().toLowerCase();
    const filtered = name
        ? groupedCards.filter(g => g.cleanName.toLowerCase().includes(name))
        : groupedCards;
    renderGallery(filtered);
}


// ============================================================
// Render the image grid — one tile per unique card name
// ============================================================
function renderGallery(groups) {
    if (!groups) { applyNameFilter(); return; }

    const gallery = document.getElementById('card-gallery');
    document.getElementById('result-count').textContent =
        `${groups.length} card${groups.length !== 1 ? 's' : ''}`;

    if (groups.length === 0) {
        gallery.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <h3>No cards found</h3>
                <p>Try adjusting your filters</p>
            </div>`;
        return;
    }

    // Sort groups
    const sortBy = document.getElementById('gallery-sort').value;
    const sorted = [...groups].sort((a, b) => {
        // Use the first printing of each group for comparison
        const ca = a.cards[0], cb = b.cards[0];
        if (sortBy === 'name')    return a.cleanName.localeCompare(b.cleanName);
        if (sortBy === 'cost') {
            const va = ca.cost === 'X' || ca.cost == null ? 99 : parseInt(ca.cost);
            const vb = cb.cost === 'X' || cb.cost == null ? 99 : parseInt(cb.cost);
            return va - vb;
        }
        if (sortBy === 'rarity')  return (RARITY_ORDER[ca.rarity]??99) - (RARITY_ORDER[cb.rarity]??99);
        if (sortBy === 'element') return (ca.element||'').localeCompare(cb.element||'');
        return 0;
    });

    // Each tile uses the first (oldest) printing's image but shows set count badge
    gallery.innerHTML = sorted.map(group => {
        const rep = group.cards[0];  // representative card for the tile
        const setCount = group.cards.length;
        // Encode the clean_name for passing to the onclick handler
        const escapedName = group.cleanName.replace(/'/g, "\\'");
        return `
            <div class="gallery-card" onclick="openCardPanel('${escapedName}')">
                ${rep.image_url
                    ? `<img class="gallery-card-img" src="${rep.image_url}"
                            alt="${rep.name}" loading="lazy"
                            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
                    : ''}
                <div class="gallery-card-img-placeholder"
                    style="${rep.image_url ? 'display:none' : ''}">No image</div>
                <div class="gallery-card-info">
                    <div class="gallery-card-name">${group.cleanName}</div>
                    <div class="gallery-card-meta">
                        <span>${rep.element || '—'} · ${rep.cost !== null ? rep.cost : '—'}</span>
                        <span class="badge badge-rarity-${(rep.rarity||'').toLowerCase()}">${rep.rarity||''}</span>
                    </div>
                    ${setCount > 1
                        ? `<div class="gallery-card-sets">${setCount} sets</div>`
                        : `<div class="gallery-card-sets">${SET_NAMES[rep.group_id] || ''}</div>`}
                </div>
            </div>`;
    }).join('');
}


// ============================================================
// Card detail panel
// Shows full details for a card name, with a set selector
// so the user can switch between printings.
// ============================================================
async function openCardPanel(cleanName) {
    // Find the group for this card name
    const group = groupedCards.find(g => g.cleanName === cleanName);
    if (!group) return;

    // Show panel immediately with the first printing selected
    document.getElementById('panel-card-name').textContent = group.cleanName;
    document.getElementById('panel-overlay').classList.add('open');
    document.getElementById('card-panel').classList.add('open');

    await renderPanelForCard(group, group.cards[0].product_id);
}

// Renders the panel body for a specific printing (product_id)
// Called on initial open and when the user changes the set selector
async function renderPanelForCard(group, selectedProductId) {
    const card = group.cards.find(c => c.product_id === selectedProductId) || group.cards[0];

    // Fetch price history for this specific printing
    const priceRes = await fetch(`/cards/${card.product_id}/prices`);
    const prices   = await priceRes.json();
    const latest   = prices.length ? prices[prices.length - 1] : null;
    const p        = latest || {};

    const descClean = (card.description || '')
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<[^>]+>/g, '')
        .trim();

    // Build set selector if there are multiple printings
    const setSelector = group.cards.length > 1 ? `
        <div>
            <div class="panel-section-title">Set Version</div>
            <select class="form-input"
                onchange="renderPanelForCard(
                    groupedCards.find(g => g.cleanName === '${group.cleanName.replace(/'/g, "\\'")}'),
                    parseInt(this.value)
                )">
                ${group.cards.map(c => `
                    <option value="${c.product_id}"
                        ${c.product_id === card.product_id ? 'selected' : ''}>
                        ${SET_NAMES[c.group_id] || `Set ${c.group_id}`}
                    </option>`).join('')}
            </select>
        </div>` : '';

    document.getElementById('panel-body').innerHTML = `
        ${card.image_url
            ? `<img class="panel-card-image" src="${card.image_url}" alt="${card.name}">`
            : ''}

        ${setSelector}

        <div class="panel-attrs">
            ${attr('Rarity',    card.rarity)}
            ${attr('Element',   card.element)}
            ${attr('Cost',      card.cost)}
            ${attr('Threshold', card.threshold)}
            ${attr('Type',      card.card_type)}
            ${attr('Subtype',   card.card_subtype)}
            ${card.power_rating  != null ? attr('Power',   card.power_rating)  : ''}
            ${card.defense_power != null ? attr('Defence', card.defense_power) : ''}
            ${card.life          != null ? attr('Life',    card.life)          : ''}
            ${attr('Set', SET_NAMES[card.group_id] || `Set ${card.group_id}`)}
        </div>

        ${descClean ? `
            <div>
                <div class="panel-section-title">Card Text</div>
                <div class="panel-text">${descClean.replace(/\n/g, '<br>')}</div>
            </div>` : ''}

        ${card.flavor_text ? `
            <div>
                <div class="panel-section-title">Flavour Text</div>
                <div class="panel-text" style="font-style:italic">${card.flavor_text}</div>
            </div>` : ''}

        <div>
            <div class="panel-section-title">Current Price (${SET_NAMES[card.group_id] || 'this set'})</div>
            <div class="price-row">
                <span class="price-label">Market price</span>
                <span class="price-value">${p.market_price != null ? '$'+p.market_price.toFixed(2) : '—'}</span>
            </div>
            <div class="price-row">
                <span class="price-label">Low price</span>
                <span class="price-value">${p.low_price != null ? '$'+p.low_price.toFixed(2) : '—'}</span>
            </div>
            <div class="price-row">
                <span class="price-label">High price</span>
                <span class="price-value">${p.high_price != null ? '$'+p.high_price.toFixed(2) : '—'}</span>
            </div>
        </div>

        ${prices.length > 1 ? `
            <div>
                <div class="panel-section-title">Price History</div>
                ${buildSparkline(prices)}
            </div>` : ''}

        ${card.url ? `
            <a href="${card.url}" target="_blank" class="btn btn-secondary" style="text-align:center">
                View on TCGPlayer ↗
            </a>` : ''}
    `;
}

function closeCardPanel() {
    document.getElementById('panel-overlay').classList.remove('open');
    document.getElementById('card-panel').classList.remove('open');
}

function attr(label, value) {
    if (value == null || value === '') return '';
    return `
        <div class="panel-attr">
            <div class="panel-attr-label">${label}</div>
            <div class="panel-attr-value">${value}</div>
        </div>`;
}

function buildSparkline(prices) {
    const vals = prices.map(p => p.market_price).filter(v => v != null);
    if (vals.length < 2) return '';
    const W = 280, H = 50, pad = 4;
    const minV = Math.min(...vals), maxV = Math.max(...vals);
    const rangeV = maxV - minV || 1;
    const points = vals.map((v, i) => {
        const x = pad + (i / (vals.length - 1)) * (W - 2 * pad);
        const y = pad + (1 - (v - minV) / rangeV) * (H - 2 * pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const latest = vals[vals.length - 1];
    const colour = latest >= vals[0] ? '#5ae0a0' : '#e05a5a';
    return `
        <svg class="price-chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
            <polyline points="${points}" fill="none" stroke="${colour}"
                stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
        </svg>
        <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:var(--text-muted)">
            <span>${prices[0].date_fetched}</span>
            <span style="color:${colour}">$${latest.toFixed(2)}</span>
        </div>`;
}
