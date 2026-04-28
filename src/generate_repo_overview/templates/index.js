// Tab switching with URL hash
const TAB_IDS = ['overview', 'versions', 'automation', 'timeline'];

function getHashTab() {
  const h = location.hash.slice(1);
  return TAB_IDS.includes(h) ? h : 'overview';
}

function applyVisibility() {
  document.querySelectorAll('.section').forEach(s => {
    const matchTab = s.dataset.tab === activeTab;
    const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
    s.classList.toggle('hidden', !(matchTab && matchCat));
  });
}

function activateTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  applyVisibility();
}

let activeTab = getHashTab();
let activeCategory = 'all';
activateTab(activeTab);

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    location.hash = btn.dataset.tab;
  });
});

window.addEventListener('hashchange', () => {
  activateTab(getHashTab());
});

// Category filtering
// `categories` is injected by the preceding <script> block
const filtersEl = document.getElementById('filters');
function renderFilters() {
  filtersEl.innerHTML = categories.map(c =>
    `<button class="filter-btn ${c === activeCategory ? 'active' : ''}" data-cat="${c}">`
    + `${c === 'all' ? 'All groups' : c}</button>`
  ).join('');
  filtersEl.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      activeCategory = btn.dataset.cat;
      renderFilters();
      applyVisibility();
    });
  });
}
renderFilters();

// Column sorting
document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const idx = Array.from(th.parentNode.children).indexOf(th);
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const asc = th.classList.toggle('sort-asc');
    th.parentNode.querySelectorAll('th').forEach(h => { if (h !== th) h.classList.remove('sort-asc'); });
    rows.sort((a, b) => {
      const av = a.children[idx]?.textContent.trim() || '';
      const bv = b.children[idx]?.textContent.trim() || '';
      const an = parseFloat(av), bn = parseFloat(bv);
      if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});
