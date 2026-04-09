// ============================================================
// State
// ============================================================
const deckId = window.location.pathname.split('/').pop();

let deckData        = null;
let activeZone      = 'all';
let searchTimeout   = null;
let browserTimeout  = null;

// Raw browser cards from API — grouped by clean_name for display
let browserAllCards    = [];
let browserGrouped     = [];

const SET_NAMES = {
    23335: 'Alpha', 23336: 'Beta', 23588: 'Arthurian Legends',
    23778: 'Arthurian Legends Promo', 23514: 'Dust Reward Promos',
    24378: 'Dragonlord', 24471: 'Gothic'
};
const RARITY_ORDER = { Ordinary: 0, Exceptional: 1, Elite: 2, Unique: 3 };
const ALL_ZONES = ['maindeck', 'sitedeck', 'collection', 'avatar', 'maybeboard'];


// ============================================================
// On page load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const setSelect = document.getElementById('browser-set');
    for (const [id, name] of Object.entries(SET_NAMES)) {
        const opt = document.createElement('option');
        opt.value = id; opt.textContent = name;
        setSelect.appendChild(opt);
    }
    loadDeck();
});


// ============================================================
// Load deck from API
// ============================================================
async function loadDeck() {
    const res = await fetch(`/decks/${deckId}`);
    deckData = await res.json();

    document.title = `${deckData.deck_name} — Sorcery Tracker`;
    document.getElementById('deck-title').textContent   = deckData.deck_name;
    document.getElementById('deck-created').textContent =
        `Created ${formatDate(deckData.deck_created)}`;

    renderCardList();
    renderStats();
}


// ============================================================
// Helper: get currently checked zones from price checkboxes
// Used by charts AND price summary so they stay in sync
// ============================================================
function getCheckedZones() {
    return [...document.querySelectorAll('.price-zone-checks input:checked')]
        .map(el => el.value);
}


// ============================================================
// Card list — tabular rows with up to three levels of grouping
// ============================================================
function renderCardList() {
    const list = document.getElementById('card-list');

    // 1. Zone filter from tab
    let cards = activeZone === 'all'
        ? deckData.cards
        : deckData.cards.filter(c => c.zone === activeZone);

    if (cards.length === 0) {
        list.innerHTML = `<div class="empty-state" style="padding:2rem 0"><p>No cards in this view</p></div>`;
        return;
    }

    // 2. Sort
    const sortBy = document.getElementById('sort-by').value;
    cards = [...cards].sort((a, b) => sortCards(a, b, sortBy));

    // 3. Multi-level grouping (up to 3 levels)
    const g1 = document.getElementById('group-by-1').value;
    const g2 = document.getElementById('group-by-2').value;
    const g3 = document.getElementById('group-by-3').value;

    if (g1 === 'none') {
        list.innerHTML = cards.map(c => cardRowHTML(c)).join('');
        return;
    }

    list.innerHTML = buildGroupHtml(cards, g1, g2, g3, 0);
}

// Recursive group builder — depth 0 = level1, 1 = level2, 2 = level3
function buildGroupHtml(cards, g1, g2, g3, depth) {
    if (g1 === 'none' || !g1) return cards.map(c => cardRowHTML(c)).join('');

    const level = groupCards(cards, g1);
    let html = '';
    const indentClass = depth > 0 ? 'zone-section-inner' : '';
    const titleClass  = depth > 0 ? 'zone-section-title zone-section-title-inner' : 'zone-section-title';

    for (const [key, groupCards_] of level) {
        const label = groupLabel(key, g1);
        const total = groupCards_.reduce((s, c) => s + c.quantity, 0);
        const price = groupPriceStr(groupCards_);

        // Next group level — shift g2→g1, g3→g2 for the recursion
        const nextG1 = g2 || 'none';
        const nextG2 = g3 || 'none';

        const inner = (nextG1 !== 'none' && depth < 2)
            ? buildGroupHtml(groupCards_, nextG1, nextG2, 'none', depth + 1)
            : groupCards_.map(c => cardRowHTML(c)).join('');

        html += `
            <div class="zone-section ${indentClass}">
                <div class="${titleClass}">
                    ${label}
                    <span class="group-count">(${total})</span>
                    <span class="group-price">${price}</span>
                </div>
                ${inner}
            </div>`;
    }
    return html;
}

function groupCards(cards, groupBy) {
    const map = new Map();
    for (const card of cards) {
        const key = groupKey(card, groupBy);
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(card);
    }
    return map;
}

function groupKey(card, groupBy) {
    if (groupBy === 'zone')      return card.zone || 'Unassigned';
    if (groupBy === 'element')   return card.element || 'None';
    if (groupBy === 'rarity')    return card.rarity || 'Unknown';
    if (groupBy === 'cost')      return card.cost !== null ? card.cost : '—';
    if (groupBy === 'card_type') return card.card_type || 'Unknown';
    if (groupBy === 'group_id')  return String(card.group_id);
    return 'All';
}

function groupLabel(key, groupBy) {
    if (groupBy === 'zone')     return formatZoneName(key);
    if (groupBy === 'group_id') return SET_NAMES[key] || `Set ${key}`;
    if (groupBy === 'cost')     return `Cost ${key}`;
    return key;
}

function groupPriceStr(cards) {
    let total = 0;
    for (const c of cards) {
        const mp = c.latest_price?.market_price;
        if (mp != null) total += mp * c.quantity;
    }
    return total > 0 ? `$${total.toFixed(2)}` : '';
}

function sortCards(a, b, sortBy) {
    if (sortBy === 'name')    return (a.name||'').localeCompare(b.name||'');
    if (sortBy === 'cost') {
        const ca = a.cost === 'X' || a.cost == null ? 99 : parseInt(a.cost);
        const cb = b.cost === 'X' || b.cost == null ? 99 : parseInt(b.cost);
        return ca - cb;
    }
    if (sortBy === 'rarity')  return (RARITY_ORDER[a.rarity]??99) - (RARITY_ORDER[b.rarity]??99);
    if (sortBy === 'element') return (a.element||'').localeCompare(b.element||'');
    if (sortBy === 'price')   return (b.latest_price?.market_price??0) - (a.latest_price?.market_price??0);
    return 0;
}

function cardRowHTML(card) {
    const price = card.latest_price?.market_price;
    const priceStr = price != null ? `$${price.toFixed(2)}` : '—';
    const desc = (card.description||'').replace(/<[^>]+>/g,'').replace(/\r\n/g,' ');

    return `
        <div class="card-row" onclick="openCardPanel(${card.product_id})" title="${desc}">
            <span class="col-qty card-row-qty">${card.quantity}×</span>
            <span class="col-name card-row-name">${card.name}</span>
            <span class="col-elem card-row-meta-cell">${card.element || '—'}</span>
            <span class="col-cost card-row-meta-cell">${card.cost !== null ? card.cost : '—'}</span>
            <span class="col-rarity card-row-meta-cell">
                <span class="badge badge-rarity-${(card.rarity||'').toLowerCase()}">${card.rarity||'—'}</span>
            </span>
            <span class="col-price card-row-price">${priceStr}</span>
            <div class="col-actions card-row-actions" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="incrementCard(${card.product_id},'${card.zone}')" title="Add one">+</button>
                <button class="btn-icon" onclick="decrementCard(${card.product_id},'${card.zone}')" title="Remove one">−</button>
                <button class="btn-icon danger" onclick="removeCard(${card.product_id},'${card.zone}')" title="Remove all">×</button>
            </div>
        </div>`;
}


// ============================================================
// Zone tab switching
// ============================================================
function switchZone(zone, btn) {
    activeZone = zone;
    document.querySelectorAll('.zone-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    const g1 = document.getElementById('group-by-1');
    if (zone === 'all' && g1.value === 'none') g1.value = 'zone';
    renderCardList();
}


// ============================================================
// Stats panel
// All charts now respect the checked zones from price checkboxes.
// This means ticking "Maindeck + Collection" shows stats for both.
// ============================================================
function renderStats() {
    const cards = deckData.cards;
    const countZone = z => cards.filter(c => c.zone === z).reduce((s,c) => s+c.quantity, 0);

    document.getElementById('stat-total').textContent      = cards.reduce((s,c)=>s+c.quantity,0);
    document.getElementById('stat-maindeck').textContent   = countZone('maindeck');
    document.getElementById('stat-sitedeck').textContent   = countZone('sitedeck');
    document.getElementById('stat-collection').textContent = countZone('collection');

    renderPriceSummary();
    renderManaCurve();
    renderDistribution('element-list', getElementCounts(), true);
    renderDistribution('type-list',    getTypeCounts(),    false);
}

// When a zone checkbox changes, re-render price summary AND all charts
function onZoneCheckChange() {
    renderPriceSummary();
    renderManaCurve();
    renderDistribution('element-list', getElementCounts(), true);
    renderDistribution('type-list',    getTypeCounts(),    false);
}

function renderPriceSummary() {
    const checked = getCheckedZones();
    let marketTotal = 0, lowTotal = 0;

    for (const card of deckData.cards) {
        if (!checked.includes(card.zone)) continue;
        const p = card.latest_price;
        if (!p) continue;
        marketTotal += (p.market_price||0) * card.quantity;
        lowTotal    += (p.low_price||0)    * card.quantity;
    }

    const zoneLabel = checked.length === ALL_ZONES.length
        ? 'All zones'
        : checked.map(z => formatZoneName(z)).join(' + ') || 'No zones selected';

    document.getElementById('price-totals').innerHTML = `
        <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.4rem">${zoneLabel}</div>
        <div class="price-total-row">
            <span class="price-total-label">Market value</span>
            <span class="price-total-value">$${marketTotal.toFixed(2)}</span>
        </div>
        <div class="price-total-row">
            <span class="price-total-label">Low value</span>
            <span class="price-total-value">$${lowTotal.toFixed(2)}</span>
        </div>`;
}

// Mana curve — uses checked zones (defaults were maindeck-only before)
function renderManaCurve() {
    const checked = getCheckedZones();
    const relevant = deckData.cards.filter(c => checked.includes(c.zone));
    const costs = {};
    for (let i = 0; i <= 10; i++) costs[String(i)] = 0;
    for (const card of relevant) {
        if (card.cost && card.cost !== 'X' && costs[card.cost] !== undefined)
            costs[card.cost] += card.quantity;
    }
    const max = Math.max(...Object.values(costs), 1);
    document.getElementById('mana-bars').innerHTML =
        Object.entries(costs).map(([c, n]) =>
            `<div class="chart-bar-wrap">
                <div class="chart-bar" style="height:${(n/max)*100}%"
                    title="${n} card${n!==1?'s':''} at cost ${c}"></div>
            </div>`).join('');
    document.getElementById('mana-labels').innerHTML =
        Object.keys(costs).map(c => `<div class="chart-label">${c}</div>`).join('');
}

// Element distribution — uses checked zones
function getElementCounts() {
    const checked = getCheckedZones();
    const counts = {};
    const COLOURS = {Fire:'bar-fire',Water:'bar-water',Earth:'bar-earth',Air:'bar-air'};
    for (const card of deckData.cards.filter(c => checked.includes(c.zone))) {
        if (!card.element) { counts['None']=(counts['None']||0)+card.quantity; continue; }
        for (const el of card.element.split(';'))
            counts[el] = (counts[el]||0) + card.quantity;
    }
    return { counts, colours: COLOURS };
}

// Card type distribution — uses checked zones
function getTypeCounts() {
    const checked = getCheckedZones();
    const counts = {};
    for (const card of deckData.cards.filter(c => checked.includes(c.zone))) {
        const t = card.card_type || 'Unknown';
        counts[t] = (counts[t]||0) + card.quantity;
    }
    return { counts, colours: {} };
}

function renderDistribution(elId, {counts, colours}, useColours) {
    const max = Math.max(...Object.values(counts), 1);
    const isEmpty = Object.values(counts).every(v => v === 0);
    document.getElementById(elId).innerHTML = isEmpty
        ? '<div style="font-size:0.8rem;color:var(--text-muted)">No cards in selected zones</div>'
        : Object.entries(counts)
            .sort((a,b) => b[1]-a[1])
            .map(([name, count]) => `
                <div class="element-row">
                    <span class="element-label">${name}</span>
                    <div class="element-bar-bg">
                        <div class="element-bar ${useColours?(colours[name]||'bar-none'):'bar-default'}"
                            style="width:${(count/max)*100}%"></div>
                    </div>
                    <span class="element-count">${count}</span>
                </div>`).join('');
}


// ============================================================
// Card detail panel
// ============================================================
async function openCardPanel(productId) {
    const card = deckData.cards.find(c => c.product_id === productId);
    if (!card) return;

    document.getElementById('panel-card-name').textContent = card.name;
    document.getElementById('panel-overlay').classList.add('open');
    document.getElementById('card-panel').classList.add('open');

    const priceRes = await fetch(`/cards/${productId}/prices`);
    const prices   = await priceRes.json();
    const p        = (prices.length ? prices[prices.length-1] : null) || {};

    const descClean = (card.description||'')
        .replace(/<br\s*\/?>/gi,'\n').replace(/<[^>]+>/g,'').trim();

    document.getElementById('panel-body').innerHTML = `
        ${card.image_url ? `<img class="panel-card-image" src="${card.image_url}" alt="${card.name}">` : ''}
        <div class="panel-attrs">
            ${attr('Rarity',   card.rarity)}
            ${attr('Element',  card.element)}
            ${attr('Cost',     card.cost)}
            ${attr('Threshold',card.threshold)}
            ${attr('Type',     card.card_type)}
            ${attr('Subtype',  card.card_subtype)}
            ${card.power_rating  !=null?attr('Power',  card.power_rating):''}
            ${card.defense_power !=null?attr('Defence',card.defense_power):''}
            ${card.life          !=null?attr('Life',   card.life):''}
            ${attr('Set', SET_NAMES[card.group_id]||`Set ${card.group_id}`)}
            ${attr('Zone', formatZoneName(card.zone))}
        </div>
        ${descClean?`<div><div class="panel-section-title">Card Text</div>
            <div class="panel-text">${descClean.replace(/\n/g,'<br>')}</div></div>`:''}
        ${card.flavor_text?`<div><div class="panel-section-title">Flavour Text</div>
            <div class="panel-text" style="font-style:italic">${card.flavor_text}</div></div>`:''}
        <div>
            <div class="panel-section-title">Current Price</div>
            <div class="price-row"><span class="price-label">Market</span>
                <span class="price-value">${p.market_price!=null?'$'+p.market_price.toFixed(2):'—'}</span></div>
            <div class="price-row"><span class="price-label">Low</span>
                <span class="price-value">${p.low_price!=null?'$'+p.low_price.toFixed(2):'—'}</span></div>
            <div class="price-row"><span class="price-label">High</span>
                <span class="price-value">${p.high_price!=null?'$'+p.high_price.toFixed(2):'—'}</span></div>
        </div>
        ${prices.length>1?`<div><div class="panel-section-title">Price History</div>
            ${buildSparkline(prices)}</div>`:''}
        ${card.url?`<a href="${card.url}" target="_blank" class="btn btn-secondary"
            style="text-align:center">View on TCGPlayer ↗</a>`:''}`;
}

function closeCardPanel() {
    document.getElementById('panel-overlay').classList.remove('open');
    document.getElementById('card-panel').classList.remove('open');
}

function attr(label, value) {
    if (value==null||value==='') return '';
    return `<div class="panel-attr">
        <div class="panel-attr-label">${label}</div>
        <div class="panel-attr-value">${value}</div>
    </div>`;
}

function buildSparkline(prices) {
    const vals = prices.map(p=>p.market_price).filter(v=>v!=null);
    if (vals.length<2) return '';
    const W=280,H=50,pad=4;
    const minV=Math.min(...vals),maxV=Math.max(...vals),rangeV=maxV-minV||1;
    const points = vals.map((v,i)=>{
        const x=pad+(i/(vals.length-1))*(W-2*pad);
        const y=pad+(1-(v-minV)/rangeV)*(H-2*pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const latest=vals[vals.length-1];
    const colour=latest>=vals[0]?'#5ae0a0':'#e05a5a';
    return `<svg class="price-chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        <polyline points="${points}" fill="none" stroke="${colour}"
            stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
    </svg>
    <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:var(--text-muted)">
        <span>${prices[0].date_fetched}</span>
        <span style="color:${colour}">$${latest.toFixed(2)}</span>
    </div>`;
}


// ============================================================
// Card add/remove
// ============================================================
async function incrementCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({product_id:productId, zone, quantity:1})
    });
    await loadDeck();
}

async function decrementCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards/${productId}?zone=${zone}&remove_all=false&quantity=1`,
        {method:'DELETE'});
    await loadDeck();
}

async function removeCard(productId, zone) {
    await fetch(`/decks/${deckId}/cards/${productId}?zone=${zone}&remove_all=true`,
        {method:'DELETE'});
    await loadDeck();
}


// ============================================================
// Quick Add modal
// ============================================================
function openAddCardModal() {
    document.getElementById('add-card-overlay').classList.add('open');
    setTimeout(()=>document.getElementById('search-name').focus(), 50);
}

function closeAddCardModal() {
    document.getElementById('add-card-overlay').classList.remove('open');
    document.getElementById('search-name').value='';
    document.getElementById('search-results').innerHTML=
        '<p class="search-hint">Search for a card above to add it to your deck</p>';
}

function searchCards() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(doSearch, 300);
}

async function doSearch() {
    const name    = document.getElementById('search-name').value.trim();
    const element = document.getElementById('search-element').value;
    const type    = document.getElementById('search-type').value;
    const rarity  = document.getElementById('search-rarity').value;

    if (!name&&!element&&!type&&!rarity) {
        document.getElementById('search-results').innerHTML=
            '<p class="search-hint">Search for a card above to add it to your deck</p>';
        return;
    }

    const params = new URLSearchParams();
    if (element) params.append('element',element);
    if (type)    params.append('card_type',type);
    if (rarity)  params.append('rarity',rarity);
    params.append('foil','false');

    let cards = await (await fetch(`/cards?${params}`)).json();
    if (name) cards = cards.filter(c=>c.clean_name.toLowerCase().includes(name.toLowerCase()));
    cards = cards.slice(0,60);

    const el = document.getElementById('search-results');
    if (!cards.length) { el.innerHTML='<p class="search-hint">No cards found</p>'; return; }

    el.innerHTML = cards.map(card=>`
        <div class="search-result-row">
            <span class="search-result-name">${card.name}</span>
            <span class="search-result-meta">
                <span>${card.element||'—'}</span>
                <span>Cost ${card.cost!==null?card.cost:'—'}</span>
                <span class="badge badge-rarity-${(card.rarity||'').toLowerCase()}">${card.rarity||''}</span>
            </span>
            <button class="btn-add-card" onclick="addCardFromSearch(${card.product_id})">+ Add</button>
        </div>`).join('');
}

async function addCardFromSearch(productId) {
    const zone = document.getElementById('add-zone').value;
    await fetch(`/decks/${deckId}/cards`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({product_id:productId, zone, quantity:1})
    });
    await loadDeck();
}


// ============================================================
// Gallery Browser modal
// Groups cards by clean_name (same as the card gallery page)
// so you see one tile per unique card name. The count badge
// shows how many total copies you have across all zones.
// ============================================================
function openBrowser() {
    document.getElementById('browser-overlay').classList.add('open');
    if (!browserAllCards.length) fetchBrowserCards();
}

function closeBrowser() {
    document.getElementById('browser-overlay').classList.remove('open');
}

function debouncedBrowserSearch() {
    clearTimeout(browserTimeout);
    browserTimeout = setTimeout(applyBrowserNameFilter, 300);
}

async function fetchBrowserCards() {
    document.getElementById('browser-gallery').innerHTML=
        '<div class="loading" style="grid-column:1/-1">Loading...</div>';

    const params = new URLSearchParams();
    const set     = document.getElementById('browser-set').value;
    const element = document.getElementById('browser-element').value;
    const type    = document.getElementById('browser-type').value;
    const rarity  = document.getElementById('browser-rarity').value;
    const cost    = document.getElementById('browser-cost').value;

    if (set)     params.append('group_id',set);
    if (element) params.append('element',element);
    if (type)    params.append('card_type',type);
    if (rarity)  params.append('rarity',rarity);
    if (cost)    params.append('cost',cost);
    params.append('foil','false');

    browserAllCards = await (await fetch(`/cards?${params}`)).json();

    // Group by clean_name — same pattern as cards.js
    // Within each group cards are sorted oldest set first
    const map = new Map();
    for (const card of browserAllCards) {
        const key = card.clean_name || card.name;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(card);
    }
    browserGrouped = Array.from(map.entries()).map(([cleanName, cards]) => ({
        cleanName,
        cards: cards.sort((a, b) => a.group_id - b.group_id)
    }));

    applyBrowserNameFilter();
}

function applyBrowserNameFilter() {
    const name = document.getElementById('browser-name').value.trim().toLowerCase();
    const groups = name
        ? browserGrouped.filter(g => g.cleanName.toLowerCase().includes(name))
        : browserGrouped;
    renderBrowserGallery(groups);
}

function renderBrowserGallery(groups) {
    if (!groups) { applyBrowserNameFilter(); return; }

    const gallery = document.getElementById('browser-gallery');
    if (!groups.length) {
        gallery.innerHTML='<div class="empty-state" style="grid-column:1/-1"><p>No cards found</p></div>';
        return;
    }

    // Count how many of each product_id is in the deck across all zones
    const deckCounts = {};
    for (const dc of deckData.cards)
        deckCounts[dc.product_id] = (deckCounts[dc.product_id]||0) + dc.quantity;

    gallery.innerHTML = groups.slice(0,120).map(group => {
        const rep = group.cards[0];  // representative printing for the tile image
        // Total copies of any printing of this card across all zones
        const inDeck = group.cards.reduce((s, c) => s + (deckCounts[c.product_id]||0), 0);
        const setCount = group.cards.length;
        const escaped = group.cleanName.replace(/'/g, "\\'");

        return `
            <div class="gallery-card browser-card">
                ${rep.image_url
                    ? `<img class="gallery-card-img" src="${rep.image_url}"
                            alt="${rep.name}" loading="lazy"
                            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
                    : ''}
                <div class="gallery-card-img-placeholder"
                    style="${rep.image_url?'display:none':''}">No image</div>
                <div class="gallery-card-info">
                    <div class="gallery-card-name">${group.cleanName}</div>
                    <div class="gallery-card-meta">
                        <span>${rep.element||'—'} · ${rep.cost!==null?rep.cost:'—'}</span>
                        <span class="badge badge-rarity-${(rep.rarity||'').toLowerCase()}">${rep.rarity||''}</span>
                    </div>
                    ${setCount > 1
                        ? `<div class="gallery-card-sets">${setCount} sets</div>`
                        : `<div class="gallery-card-sets">${SET_NAMES[rep.group_id]||''}</div>`}
                    <div class="browser-card-controls">
                        <button class="btn-icon" onclick="browserDecrement('${escaped}')" title="Remove one">−</button>
                        <span class="browser-card-count ${inDeck>0?'in-deck':''}">${inDeck}</span>
                        <button class="btn-icon" onclick="browserIncrement('${escaped}')" title="Add one">+</button>
                    </div>
                </div>
            </div>`;
    }).join('');
}

// For browser +/-, always use the first (oldest) set printing.
// If the user wants a specific set version they can use Quick Add.
async function browserIncrement(cleanName) {
    const group = browserGrouped.find(g => g.cleanName === cleanName);
    if (!group) return;
    const productId = group.cards[0].product_id;
    const zone = document.getElementById('browser-zone').value;

    await fetch(`/decks/${deckId}/cards`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({product_id:productId, zone, quantity:1})
    });
    const res = await fetch(`/decks/${deckId}`);
    deckData = await res.json();
    renderCardList();
    renderStats();
    applyBrowserNameFilter();
}

async function browserDecrement(cleanName) {
    const group = browserGrouped.find(g => g.cleanName === cleanName);
    if (!group) return;
    const zone = document.getElementById('browser-zone').value;

    // Find which printing of this card is in the deck for this zone
    const existing = deckData.cards.find(c =>
        group.cards.some(g => g.product_id === c.product_id) && c.zone === zone
    );
    if (!existing) return;

    await fetch(`/decks/${deckId}/cards/${existing.product_id}?zone=${zone}&remove_all=false&quantity=1`,
        {method:'DELETE'});
    const res = await fetch(`/decks/${deckId}`);
    deckData = await res.json();
    renderCardList();
    renderStats();
    applyBrowserNameFilter();
}


// ============================================================
// Rename deck modal
// ============================================================
function openRenameModal() {
    const input = document.getElementById('rename-input');
    input.value = deckData.deck_name;
    document.getElementById('rename-modal-overlay').classList.add('open');
    setTimeout(() => { input.focus(); input.select(); }, 50);
}

function closeRenameModal() {
    document.getElementById('rename-modal-overlay').classList.remove('open');
}

async function confirmRename() {
    const name = document.getElementById('rename-input').value.trim();
    if (!name || name === deckData.deck_name) { closeRenameModal(); return; }

    const res = await fetch(`/decks/${deckId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });

    if (res.ok) {
        deckData.deck_name = name;
        document.getElementById('deck-title').textContent = name;
        document.title = `${name} — Sorcery Tracker`;
        closeRenameModal();
    }
}


// ============================================================
// Utilities
// ============================================================
function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-GB',
        {day:'numeric', month:'short', year:'numeric'});
}

function formatZoneName(zone) {
    const names = {maindeck:'Maindeck', sitedeck:'Site Deck',
        collection:'Collection', avatar:'Avatar', maybeboard:'Maybeboard', Unassigned:'Unassigned'};
    return names[zone] || zone;
}
