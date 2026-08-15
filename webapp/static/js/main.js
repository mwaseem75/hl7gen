(function () {
  /* ---- Theme toggle: system -> light -> dark -> system ---- */
  const THEME_KEY = 'hl7gen-theme';
  const toggleBtn = document.getElementById('theme-toggle');
  const root = document.documentElement;

  function applyTheme(mode) {
    if (mode === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', mode);
    }
    toggleBtn.setAttribute('data-mode', mode);
  }

  let currentMode = localStorage.getItem(THEME_KEY) || 'system';
  applyTheme(currentMode);

  toggleBtn.addEventListener('click', () => {
    const order = ['system', 'light', 'dark'];
    currentMode = order[(order.indexOf(currentMode) + 1) % order.length];
    localStorage.setItem(THEME_KEY, currentMode);
    applyTheme(currentMode);
  });

  /* ---- Shared state ---- */
  const typeSelect = document.getElementById('message-type');
  const structureTypeSelect = document.getElementById('structure-type');
  const versionSelect = document.getElementById('hl7-version');
  const fhirVersionSelect = document.getElementById('fhir-version');
  const realisticCheckbox = document.getElementById('realistic');
  const messageBox = document.getElementById('message-box');
  const statusEl = document.getElementById('status');
  const fhirSection = document.getElementById('fhir-output-section');
  const fhirOutput = document.getElementById('fhir-output');
  const structureTree = document.getElementById('structure-tree');

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (kind ? ' ' + kind : '');
  }

  // A <textarea>'s .value getter normalizes all line breaks to \n per the HTML spec,
  // which corrupts HL7's literal \r segment separators the moment this box is read.
  // The backend also normalizes defensively, but fixing it here keeps the message the
  // user sees in the box consistent with what gets sent.
  function messageText() {
    return messageBox.value.replace(/\r\n|\n/g, '\r');
  }

  function populateSelect(select, items, valueKey, labelFn, preferredValue) {
    select.innerHTML = '';
    let preferredIndex = 0;
    items.forEach((item, i) => {
      const opt = document.createElement('option');
      opt.value = typeof item === 'string' ? item : item[valueKey];
      opt.textContent = labelFn(item);
      select.appendChild(opt);
      if (opt.value === preferredValue) preferredIndex = i;
    });
    select.selectedIndex = preferredIndex;
  }

  Promise.all([
    fetch('/api/types').then((r) => r.json()),
    fetch('/api/versions').then((r) => r.json()),
    fetch('/api/fhir-versions').then((r) => r.json()),
  ])
    .then(([types, versions, fhirVersions]) => {
      const label = (t) => `${t.code} — ${t.description}`;
      populateSelect(typeSelect, types, 'code', label, 'ADT_A01');
      populateSelect(structureTypeSelect, types, 'code', label, 'ADT_A01');
      populateSelect(versionSelect, versions, null, (v) => v, '2.5');
      populateSelect(fhirVersionSelect, fhirVersions, 'code', (v) => v.label, 'R5');
    })
    .catch(() => setStatus('Could not load message types/versions.', 'err'));

  /* ---- Generate / validate / FHIR ---- */
  document.getElementById('generate-btn').addEventListener('click', () => {
    setStatus('Generating…');
    fhirSection.classList.add('hidden');
    fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_type: typeSelect.value,
        version: versionSelect.value,
        realistic: realisticCheckbox.checked,
      }),
    })
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Generation failed.');
        return data;
      })
      .then((data) => {
        messageBox.value = data.message;
        setStatus('Generated.', 'ok');
      })
      .catch((err) => setStatus(err.message, 'err'));
  });

  document.getElementById('validate-btn').addEventListener('click', () => {
    setStatus('Validating…');
    fetch('/api/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: messageText() }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.valid) {
          setStatus('Valid HL7 message.', 'ok');
        } else {
          setStatus(`Invalid: ${data.error}`, 'err');
        }
      })
      .catch(() => setStatus('Validation request failed.', 'err'));
  });

  document.getElementById('fhir-btn').addEventListener('click', () => {
    setStatus('Converting…');
    fetch('/api/to-fhir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: messageText(), fhir_version: fhirVersionSelect.value }),
    })
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Conversion failed.');
        return data;
      })
      .then((bundle) => {
        fhirOutput.textContent = JSON.stringify(bundle, null, 2);
        fhirSection.classList.remove('hidden');
        setStatus(`Converted to FHIR (${fhirVersionSelect.value}).`, 'ok');
      })
      .catch((err) => setStatus(err.message, 'err'));
  });

  /* ---- Structure explorer ---- */
  function fieldNode(field) {
    const wrap = document.createElement('div');
    wrap.className = 'leaf ' + (field.required ? 'node-required' : 'node-optional');

    const name = document.createElement('span');
    name.className = 'node-name';
    name.textContent = field.name;
    wrap.appendChild(name);

    if (field.description) {
      const desc = document.createElement('span');
      desc.className = 'node-desc';
      desc.textContent = field.description;
      wrap.appendChild(desc);
    }

    if (field.datatype) {
      const dt = document.createElement('span');
      dt.className = 'node-desc';
      dt.textContent = `(${field.datatype})`;
      wrap.appendChild(dt);
    }

    if (field.repeating) {
      const pill = document.createElement('span');
      pill.className = 'pill pill-repeat';
      pill.textContent = '×N';
      wrap.appendChild(pill);
    }

    if (field.components && field.components.length) {
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.appendChild(wrap);
      details.appendChild(summary);
      field.components.forEach((c) => details.appendChild(fieldNode(c)));
      return details;
    }
    return wrap;
  }

  function segmentNode(segment) {
    const details = document.createElement('details');
    details.className = segment.required ? 'node-required' : 'node-optional';

    const summary = document.createElement('summary');
    const name = document.createElement('span');
    name.className = 'node-name';
    name.textContent = segment.name;
    summary.appendChild(name);

    const desc = document.createElement('span');
    desc.className = 'node-desc';
    desc.textContent = segment.description || (segment.type === 'group' ? 'GROUP' : '');
    summary.appendChild(desc);

    if (segment.type === 'group') {
      const pill = document.createElement('span');
      pill.className = 'pill pill-group';
      pill.textContent = 'GROUP';
      summary.appendChild(pill);
    }

    if (segment.repeating) {
      const pill = document.createElement('span');
      pill.className = 'pill pill-repeat';
      pill.textContent = '×N';
      summary.appendChild(pill);
    }

    details.appendChild(summary);

    const children = segment.type === 'group' ? segment.children : segment.fields;
    (children || []).forEach((child) => {
      const node = segment.type === 'group' ? segmentNode(child) : fieldNode(child);
      details.appendChild(node);
    });

    return details;
  }

  document.getElementById('structure-btn').addEventListener('click', () => {
    structureTree.innerHTML = '<p class="status">Loading…</p>';
    fetch(`/api/structure/${structureTypeSelect.value}?version=${versionSelect.value}`)
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Could not load structure.');
        return data;
      })
      .then((data) => {
        structureTree.innerHTML = '';
        data.segments.forEach((seg) => structureTree.appendChild(segmentNode(seg)));
      })
      .catch((err) => {
        structureTree.innerHTML = `<p class="status err">${err.message}</p>`;
      });
  });
})();
