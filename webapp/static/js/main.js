(function () {
  const typeSelect = document.getElementById('message-type');
  const realisticCheckbox = document.getElementById('realistic');
  const messageBox = document.getElementById('message-box');
  const statusEl = document.getElementById('status');
  const fhirSection = document.getElementById('fhir-output-section');
  const fhirOutput = document.getElementById('fhir-output');

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (kind ? ' ' + kind : '');
  }

  fetch('/api/types')
    .then((r) => r.json())
    .then((types) => {
      for (const t of types) {
        const opt = document.createElement('option');
        opt.value = t.code;
        opt.textContent = `${t.code} — ${t.description}`;
        typeSelect.appendChild(opt);
      }
      const defaultIndex = types.findIndex((t) => t.code === 'ADT_A01');
      if (defaultIndex >= 0) typeSelect.selectedIndex = defaultIndex;
    })
    .catch(() => setStatus('Could not load message types.', 'err'));

  document.getElementById('generate-btn').addEventListener('click', () => {
    setStatus('Generating…');
    fhirSection.classList.add('hidden');
    fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_type: typeSelect.value,
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
      body: JSON.stringify({ message: messageBox.value }),
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
      body: JSON.stringify({ message: messageBox.value }),
    })
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Conversion failed.');
        return data;
      })
      .then((bundle) => {
        fhirOutput.textContent = JSON.stringify(bundle, null, 2);
        fhirSection.classList.remove('hidden');
        setStatus('Converted to FHIR.', 'ok');
      })
      .catch((err) => setStatus(err.message, 'err'));
  });
})();
