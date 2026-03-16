(() => {
  const state = {
    mode: 'full',
    sectionIndex: 0,
    sections: [],
    chapters: [],
    hasMath: false
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  async function init() {
    try {
      const resp = await fetch('content.json');
      const data = await resp.json();
      state.chapters = data.chapters;
      state.hasMath = data.meta?.hasMath ?? false;
      state.sections = data.chapters.flatMap((ch, ci) =>
        ch.sections.map((s, si) => ({ ...s, chapterTitle: ch.title, chapterId: ch.id, chapterIndex: ci }))
      );
      buildSidebar();
      bindEvents();
      loadFromHash();
      $('#loading')?.remove();
    } catch (e) {
      $('#loading').textContent = 'Failed to load content: ' + e.message;
    }
  }

  function buildSidebar() {
    const container = $('#sidebar-content');
    let html = '';
    let sectionIdx = 0;
    for (const ch of state.chapters) {
      html += `<div class="nav-chapter">${escapeHtml(ch.title)}</div>`;
      for (const s of ch.sections) {
        const label = s.id.match(/^\d/) ? `${s.id} ${s.title}` : s.title;
        html += `<a class="nav-section" data-index="${sectionIdx}" data-id="${s.id}">${escapeHtml(label)}</a>`;
        sectionIdx++;
      }
    }
    container.innerHTML = html;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function bindEvents() {
    for (const btn of $$('.mode-btn')) {
      btn.addEventListener('click', () => setMode(btn.dataset.mode));
    }

    $('#sidebar-content').addEventListener('click', (e) => {
      const link = e.target.closest('.nav-section');
      if (link) navigateTo(parseInt(link.dataset.index));
    });

    $('#prev-btn').addEventListener('click', () => navigateTo(state.sectionIndex - 1));
    $('#next-btn').addEventListener('click', () => navigateTo(state.sectionIndex + 1));
    $('#sidebar-toggle').addEventListener('click', toggleSidebar);

    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowLeft') navigateTo(state.sectionIndex - 1);
      else if (e.key === 'ArrowRight') navigateTo(state.sectionIndex + 1);
      else if (e.key === '1') setMode('eli5');
      else if (e.key === '2') setMode('medium');
      else if (e.key === '3') setMode('full');
    });

    window.addEventListener('hashchange', loadFromHash);
  }

  function loadFromHash() {
    const hash = location.hash.slice(1);
    if (hash) {
      const idx = state.sections.findIndex(s => s.id === hash);
      if (idx >= 0) { navigateTo(idx); return; }
    }
    navigateTo(0);
  }

  function setMode(mode) {
    state.mode = mode;
    for (const btn of $$('.mode-btn')) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    }
    renderSection();
  }

  function navigateTo(index) {
    if (index < 0 || index >= state.sections.length) return;
    state.sectionIndex = index;
    location.hash = state.sections[index].id;

    for (const link of $$('.nav-section')) {
      link.classList.toggle('active', parseInt(link.dataset.index) === index);
    }

    const activeNav = $('.nav-section.active');
    if (activeNav) activeNav.scrollIntoView({ block: 'nearest' });

    $('#prev-btn').disabled = index === 0;
    $('#next-btn').disabled = index === state.sections.length - 1;
    $('#section-indicator').textContent = `${index + 1} / ${state.sections.length}`;

    renderSection();
    $('main').scrollTo(0, 0);
  }

  function renderSection() {
    const section = state.sections[state.sectionIndex];
    if (!section) return;

    const modeLabels = { eli5: 'ELI5', medium: 'Medium', full: 'Full' };
    const content = section[state.mode] || section.full || '<p>Content not yet available.</p>';

    const imagesHtml = (section.images || []).map(img =>
      `<div class="figure"><img src="images/${encodeURIComponent(img)}" alt="Figure from ${escapeHtml(section.title)}" loading="lazy"></div>`
    ).join('');

    const notesHtml = (section.agentNotes && section.agentNotes.length > 0)
      ? `<div class="agent-notes">
          <div class="agent-notes-header">Additional Notes</div>
          ${section.agentNotes.map(note => `<div class="agent-note-card">${note}</div>`).join('')}
        </div>`
      : '';

    const sectionLabel = section.id.match(/^\d/) ? `${section.id} ${section.title}` : section.title;

    const html = `
      <div class="section-content">
        <span class="mode-badge ${state.mode}">${modeLabels[state.mode]}</span>
        <div class="chapter-label">${escapeHtml(section.chapterTitle)}</div>
        <h2>${escapeHtml(sectionLabel)}</h2>
        <div class="section-body">${content}</div>
        ${imagesHtml}
        ${notesHtml}
      </div>
    `;

    const main = $('main');
    main.innerHTML = html;

    if (state.hasMath && typeof renderMathInElement === 'function') {
      renderMathInElement(main, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false }
        ],
        throwOnError: false
      });
    }
  }

  function toggleSidebar() {
    const sidebar = $('#sidebar');
    const main = $('main');
    const isMobile = window.innerWidth <= 768;

    if (isMobile) {
      sidebar.classList.toggle('open');
    } else {
      sidebar.classList.toggle('collapsed');
      main.classList.toggle('expanded');
    }
  }

  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && e.target.closest('.nav-section')) {
      $('#sidebar').classList.remove('open');
    }
  });

  init();
})();
