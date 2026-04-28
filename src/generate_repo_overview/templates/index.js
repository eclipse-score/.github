// Tab switching
let activeTab = 'overview';
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    activeTab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.section').forEach(s => {
      const matchTab = s.dataset.tab === activeTab;
      const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
      s.classList.toggle('hidden', !(matchTab && matchCat));
    });
  });
});

// Category filtering
let activeCategory = 'all';
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
      document.querySelectorAll('.section').forEach(s => {
        const matchTab = s.dataset.tab === activeTab;
        const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
        s.classList.toggle('hidden', !(matchTab && matchCat));
      });
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
