// Tabs and filters share the URL hash so dashboard views can be bookmarked.
// Optional tabs cannot be activated through stale bookmarks when absent.
const TAB_IDS = Array.from(document.querySelectorAll('.tab-btn'), button => button.dataset.tab);

const organizationFilter = document.getElementById('organization-filter');
const organizationNames = new Set(Array.from(organizationFilter?.options ?? [], option => option.value));
const primaryOrg = organizationFilter?.dataset.primaryOrg ?? '';
function repositoryOwner(repository) {
  const [owner, repoName] = repository.split('/');
  return (repoName ? owner : primaryOrg).toLowerCase();
}

const categorySections = Array.from(document.querySelectorAll('.section[data-tab="overview"][data-category]'));
const categoryCounts = new Map(categorySections.map(section => [
  section.dataset.category,
  Number(section.querySelector('.section-count').textContent),
]));
const categoryOwners = new Map(categorySections.map(section => [
  section.dataset.category,
  repositoryOwner(section.querySelector('[data-repo-filter]').dataset.repoFilter),
]));

function getHashState() {
  const [hashTab, query = ''] = location.hash.slice(1).split('?');
  const tab = hashTab === 'modules' ? 'naming' : hashTab;
  const params = new URLSearchParams(query);
  const requestedOrg = params.get('org');
  const organization = organizationNames.has(requestedOrg) ? requestedOrg : '';
  const requestedCategory = params.get('category');
  const categoryMatchesOrg = !organization || categoryOwners.get(requestedCategory) === organization.toLowerCase();
  const integration = params.get('integration');
  const docs = params.get('docs');
  return {
    tab: TAB_IDS.includes(tab) ? tab : 'overview',
    category: categoryCounts.has(requestedCategory) && categoryMatchesOrg ? requestedCategory : 'all',
    organization,
    integration: ['included', 'excluded'].includes(integration) ? integration : 'all',
    docs: ['yes', 'no'].includes(docs) ? docs : 'all',
  };
}

function writeHashState(tab, category, integration, docs, organization = activeOrg) {
  const params = new URLSearchParams();
  if (organization) params.set('org', organization);
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
  const owner = activeOrg.toLowerCase();
  document.querySelectorAll('[data-summary-org]').forEach(summary => {
    summary.hidden = summary.dataset.summaryOrg !== activeOrg;
  });
  document.querySelectorAll('.section').forEach(s => {
    const matchTab = s.dataset.tab === activeTab;
    const matchCat = !s.dataset.category || activeCategory === 'all' || s.dataset.category === activeCategory;
    s.classList.toggle('hidden', !(matchTab && matchCat));
  });
  document.querySelectorAll('[data-repo-filter]').forEach(item => {
    const matchCategory = activeCategory === 'all' || item.dataset.repositoryCategory === activeCategory;
    const matchIntegration = activeIntegration === 'all' || item.dataset.integration === activeIntegration;
    const matchDocs = activeDocs === 'all' || item.dataset.docsAsCode === activeDocs;
    const matchOrg = !owner || owner === repositoryOwner(item.dataset.repoFilter);
    item.classList.toggle('repo-filter-hidden', !(matchOrg && matchCategory && matchIntegration && matchDocs));
  });
  document.querySelectorAll('.section:not(.hidden)').forEach(section => {
    const items = section.querySelectorAll('[data-repo-filter]');
    if (items.length && !Array.from(items).some(item => !item.classList.contains('repo-filter-hidden'))) {
      section.classList.add('hidden');
    }
  });
  document.getElementById('no-matching-repos').classList.toggle(
    'hidden', Boolean(document.querySelector('.section:not(.hidden):not([data-policy-summary])')),
  );
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

function activateState({tab, category, integration, docs, organization}) {
  activeTab = tab;
  activeCategory = category;
  activeIntegration = integration;
  activeDocs = docs;
  activeOrg = organization;
  if (organizationFilter) organizationFilter.value = activeOrg;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('filters').style.display = '';
  renderFilters();
  versionViewToggle.style.display = tab === 'versions' ? 'flex' : 'none';
  applyVisibility();
}

const filtersEl = document.getElementById('filters');
let activeTab, activeCategory, activeIntegration, activeDocs, activeOrg;
activateState(getHashState());

organizationFilter?.addEventListener('change', () => {
  writeHashState(activeTab, 'all', activeIntegration, activeDocs, organizationFilter.value);
});

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    writeHashState(btn.dataset.tab, activeCategory, activeIntegration, activeDocs);
  });
});

window.addEventListener('hashchange', () => {
  activateState(getHashState());
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
  const visibleGroups = Array.from(categoryCounts).filter(([category]) =>
    !activeOrg || categoryOwners.get(category) === activeOrg.toLowerCase(),
  );
  const groupChoices = [
    ['all', `All groups (${visibleGroups.reduce((total, [, count]) => total + count, 0)})`],
    ...visibleGroups.map(([category, count]) => [
      category, `${activeOrg ? category.slice(activeOrg.length + 3) : category} (${count})`,
    ]),
  ];
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
    if (activeOrg) active.push(activeOrg);
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


// Keep the native title in browsers that cannot position the styled tooltip.
if (CSS.supports('(position-anchor: --table-tooltip) and (left: anchor(center)) and (position-try-fallbacks: flip-block)')) {
  document.querySelectorAll('#sections :is(th, td)[title]').forEach(cell => {
    cell.dataset.tooltip = cell.title;
    cell.removeAttribute('title');
  });
}
