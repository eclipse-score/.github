// Tab and category state share the URL hash so dashboard views can be bookmarked.
const TAB_IDS = ['overview', 'versions', 'tech-stack', 'naming', 'traceability', 'policy-sync'];

function getHashState() {
  const [hashTab, query = ''] = location.hash.slice(1).split('?');
  const tab = hashTab === 'modules' ? 'naming' : hashTab;
  const params = new URLSearchParams(query);
  const requestedCategory = params.get('category');
  const integration = params.get('integration');
  const docs = params.get('docs');
  return {
    tab: TAB_IDS.includes(tab) ? tab : 'overview',
    category: categories.includes(requestedCategory) ? requestedCategory : 'all',
    integration: ['included', 'excluded'].includes(integration) ? integration : 'all',
    docs: ['yes', 'no'].includes(docs) ? docs : 'all',
  };
}

function writeHashState(tab, category, integration, docs) {
  const params = new URLSearchParams();
  if (category !== 'all') params.set('category', category);
  if (integration !== 'all') params.set('integration', integration);
  if (docs !== 'all') params.set('docs', docs);
  const serialized = params.toString();
  const query = serialized ? `?${serialized}` : '';
  const hash = `#${tab}${query}`;
  if (location.hash !== hash) location.hash = hash;
}

let activeVersionView = 'table';
const versionViewToggle = document.getElementById('version-view-toggle');

function applyVisibility() {
  document.querySelectorAll('.section').forEach(s => {
    const matchTab = s.dataset.tab === activeTab;
    const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
    s.classList.toggle('hidden', !(matchTab && matchCat));
  });
  document.querySelectorAll('[data-repo-filter]').forEach(item => {
    const matchCategory = activeCategory === 'all' || item.dataset.repositoryCategory === activeCategory;
    const matchIntegration = activeIntegration === 'all' || item.dataset.integration === activeIntegration;
    const matchDocs = activeDocs === 'all' || item.dataset.docsAsCode === activeDocs;
    item.classList.toggle('repo-filter-hidden', !(matchCategory && matchIntegration && matchDocs));
  });
  document.querySelectorAll('.section:not(.hidden)').forEach(section => {
    const items = section.querySelectorAll('[data-repo-filter]');
    if (items.length && !Array.from(items).some(item => !item.classList.contains('repo-filter-hidden'))) {
      section.classList.add('hidden');
    }
  });
  document.querySelectorAll('.versions-table-view').forEach(view => {
    view.classList.toggle('hidden', activeVersionView !== 'table');
  });
  document.querySelectorAll('.versions-cards-view').forEach(view => {
    view.classList.toggle('hidden', activeVersionView !== 'cards');
  });
  versionViewToggle.querySelectorAll('.view-toggle-btn').forEach(button => {
    const isActive = button.dataset.versionView === activeVersionView;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-pressed', String(isActive));
  });
}

function activateState(tab, category, integration, docs) {
  activeTab = tab;
  activeCategory = category;
  activeIntegration = integration;
  activeDocs = docs;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('filters').style.display = '';
  renderFilters();
  versionViewToggle.style.display = tab === 'versions' ? 'flex' : 'none';
  applyVisibility();
}

// `categories` is injected by the preceding <script> block.
const filtersEl = document.getElementById('filters');
const categoryCounts = new Map(
  Array.from(document.querySelectorAll('.section[data-tab="overview"][data-category]'))
    .map(section => [section.dataset.category, Number(section.querySelector('.section-count')?.textContent || 0)])
);

let {tab: activeTab, category: activeCategory, integration: activeIntegration, docs: activeDocs} = getHashState();
activateState(activeTab, activeCategory, activeIntegration, activeDocs);

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    writeHashState(btn.dataset.tab, activeCategory, activeIntegration, activeDocs);
  });
});

window.addEventListener('hashchange', () => {
  const state = getHashState();
  activateState(state.tab, state.category, state.integration, state.docs);
});

versionViewToggle.querySelectorAll('.view-toggle-btn').forEach(button => {
  button.addEventListener('click', () => {
    activeVersionView = button.dataset.versionView;
    applyVisibility();
  });
});

function renderFilters() {
  filtersEl.replaceChildren();
  const intro = document.createElement('div');
  intro.className = 'filter-intro';
  const label = document.createElement('span');
  label.className = 'filter-label';
  label.textContent = 'Filter repositories';
  const hint = document.createElement('span');
  hint.className = 'filter-hint';
  hint.textContent = 'Combine group and repository filters';
  intro.append(label, hint);

  const current = document.createElement('span');
  current.className = 'filter-current';
  current.setAttribute('aria-live', 'polite');
  const groupChoices = categories.map(category => {
    const count = category === 'all'
      ? Array.from(categoryCounts.values()).reduce((total, value) => total + value, 0)
      : categoryCounts.get(category) || 0;
    return [category, `${category === 'all' ? 'All groups' : category} (${count})`];
  });
  const groupSelect = createFilterSelect(
    'Group', 'group-filter', activeCategory, groupChoices,
  );
  const integrationSelect = createFilterSelect(
    'Reference integration', 'integration-filter', activeIntegration,
    [['all', 'All'], ['included', 'Included'], ['excluded', 'Not included']],
  );
  const docsSelect = createFilterSelect(
    'Docs-as-Code', 'docs-filter', activeDocs,
    [['all', 'All'], ['yes', 'Uses it'], ['no', 'Does not use it']],
  );
  const updateCurrent = () => {
    const active = [];
    if (activeCategory !== 'all') active.push(`group: ${activeCategory}`);
    if (activeIntegration !== 'all') active.push(activeIntegration === 'included' ? 'in reference integration' : 'not in reference integration');
    if (activeDocs !== 'all') active.push(activeDocs === 'yes' ? 'uses Docs-as-Code' : 'does not use Docs-as-Code');
    current.textContent = active.length ? `Filtered by ${active.join(' · ')}` : 'Showing all repositories';
  };
  updateCurrent();
  filtersEl.append(intro, groupSelect.wrapper, integrationSelect.wrapper, docsSelect.wrapper, current);
  groupSelect.select.addEventListener('change', () => {
    writeHashState(activeTab, groupSelect.select.value, activeIntegration, activeDocs);
  });
  integrationSelect.select.addEventListener('change', () => {
    writeHashState(activeTab, activeCategory, integrationSelect.select.value, activeDocs);
  });
  docsSelect.select.addEventListener('change', () => {
    writeHashState(activeTab, activeCategory, activeIntegration, docsSelect.select.value);
  });
}

function createFilterSelect(labelText, id, value, choices) {
  const wrapper = document.createElement('label');
  wrapper.className = 'filter-select';
  wrapper.htmlFor = id;
  const label = document.createElement('span');
  label.textContent = labelText;
  const select = document.createElement('select');
  select.id = id;
  select.setAttribute('aria-label', labelText);
  choices.forEach(([choice, text]) => {
    const option = document.createElement('option');
    option.value = choice;
    option.textContent = text;
    option.selected = choice === value;
    select.append(option);
  });
  wrapper.append(label, select);
  return {wrapper, select};
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
