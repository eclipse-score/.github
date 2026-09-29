// Tab and category state share the URL hash so dashboard views can be bookmarked.
const TAB_IDS = ['overview', 'versions', 'tech-stack', 'naming', 'traceability', 'policy-sync'];

function getHashState() {
  const [hashTab, query = ''] = location.hash.slice(1).split('?');
  const tab = hashTab === 'modules' ? 'naming' : hashTab;
  const requestedCategory = new URLSearchParams(query).get('category');
  return {
    tab: TAB_IDS.includes(tab) ? tab : 'overview',
    category: categories.includes(requestedCategory) ? requestedCategory : 'all',
  };
}

function writeHashState(tab, category) {
  const query = category === 'all' ? '' : `?category=${encodeURIComponent(category)}`;
  const hash = `#${tab}${query}`;
  if (location.hash !== hash) location.hash = hash;
}

function applyVisibility() {
  document.querySelectorAll('.section').forEach(s => {
    const matchTab = s.dataset.tab === activeTab;
    const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
    s.classList.toggle('hidden', !(matchTab && matchCat));
  });
}

function activateState(tab, category) {
  activeTab = tab;
  activeCategory = category;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('filters').style.display = tab === 'traceability' ? 'none' : '';
  renderFilters();
  applyVisibility();
}

// `categories` is injected by the preceding <script> block.
const filtersEl = document.getElementById('filters');
const categoryCounts = new Map(
  Array.from(document.querySelectorAll('.section[data-tab="overview"][data-category]'))
    .map(section => [section.dataset.category, Number(section.querySelector('.section-count')?.textContent || 0)])
);

let {tab: activeTab, category: activeCategory} = getHashState();
activateState(activeTab, activeCategory);

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    writeHashState(btn.dataset.tab, activeCategory);
  });
});

window.addEventListener('hashchange', () => {
  const state = getHashState();
  activateState(state.tab, state.category);
});

function renderFilters() {
  filtersEl.replaceChildren();
  const intro = document.createElement('div');
  intro.className = 'filter-intro';
  const label = document.createElement('span');
  label.className = 'filter-label';
  label.textContent = 'Filter by group';
  const hint = document.createElement('span');
  hint.className = 'filter-hint';
  hint.textContent = 'Choose which repositories to show';
  intro.append(label, hint);

  const options = document.createElement('div');
  options.className = 'filter-options';
  options.setAttribute('role', 'group');
  options.setAttribute('aria-label', 'Filter repositories by group');
  categories.forEach(category => {
    const button = document.createElement('button');
    button.className = `filter-btn${category === activeCategory ? ' active' : ''}`;
    button.dataset.cat = category;
    button.setAttribute('aria-pressed', String(category === activeCategory));
    const name = document.createElement('span');
    name.textContent = category === 'all' ? 'All repositories' : category;
    const count = document.createElement('span');
    count.className = 'filter-count';
    count.textContent = String(category === 'all'
      ? Array.from(categoryCounts.values()).reduce((total, value) => total + value, 0)
      : categoryCounts.get(category) || 0);
    button.append(name, count);
    options.append(button);
  });
  const current = document.createElement('span');
  current.className = 'filter-current';
  current.setAttribute('aria-live', 'polite');
  current.textContent = activeCategory === 'all' ? 'Showing all groups' : `Showing ${activeCategory}`;
  filtersEl.append(intro, options, current);

  options.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      writeHashState(activeTab, btn.dataset.cat);
    });
  });
}

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
      const aCell = a.children[idx], bCell = b.children[idx];
      const av = aCell?.getAttribute('data-sort-value') ?? aCell?.textContent.trim() ?? '';
      const bv = bCell?.getAttribute('data-sort-value') ?? bCell?.textContent.trim() ?? '';
      const an = parseFloat(av), bn = parseFloat(bv);
      if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});
