// Related-letters block on the individual letter pages (html/letters/*.html).
// Reads the precomputed neuro-symbolic suggestions from json/explore/related.json
// (scripts/export_related.py: BGE-M3 cosine neighbors + shared register mentions +
// correspondence context) and renders them with their reasons - no model download,
// no server. Pages without an entry (register-only letters) simply show nothing.
document.addEventListener('DOMContentLoaded', async function () {
    const container = document.getElementById('related-letters');
    if (!container) return;

    const letterId = window.location.pathname.split('/').pop().replace(/\.html$/, '');
    let payload;
    try {
        payload = await (await fetch('../../json/explore/related.json')).json();
    } catch (err) {
        console.error('Could not load related.json:', err);
        return;
    }
    const entries = payload.letters[letterId];
    if (!entries || entries.length === 0) return;

    const section = document.createElement('section');
    section.className = 'mb-4';
    const heading = document.createElement('h2');
    heading.textContent = 'Related Letters';
    section.appendChild(heading);

    const note = document.createElement('p');
    note.className = 'text-muted small';
    note.textContent = 'Computed from the edition’s embeddings and knowledge graph: ' + payload.method;
    section.appendChild(note);

    for (const entry of entries) {
        const card = document.createElement('div');
        card.className = 'rag-card';

        if (entry.score != null) {
            const score = document.createElement('span');
            score.className = 'score';
            score.textContent = entry.score.toFixed(3);
            card.appendChild(score);
        }

        const link = document.createElement('a');
        if (entry.has_page) {
            link.href = `${entry.id}.html`;
        } else {
            link.href = `../letters.html?q=${encodeURIComponent(entry.id)}`;
        }
        const strong = document.createElement('strong');
        strong.textContent = entry.id;
        link.appendChild(strong);
        card.appendChild(link);

        if (entry.preview) {
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.textContent = 'unreviewed preview';
            card.appendChild(badge);
        }

        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = `${entry.date || 'undated'} · ${entry.sender || '?'} → ${entry.recipient || '?'}`;
        card.appendChild(meta);

        const reasons = document.createElement('ul');
        reasons.className = 'small mb-0';
        for (const reason of entry.reasons) {
            const li = document.createElement('li');
            li.textContent = reason;
            reasons.appendChild(li);
        }
        card.appendChild(reasons);
        section.appendChild(card);
    }
    container.appendChild(section);
});
