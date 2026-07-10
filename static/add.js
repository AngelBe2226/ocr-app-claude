// Modal global "Añadir movimiento": gasto / ingreso / transferencia.
let addOptions = null;

function openAddModal() {
  document.getElementById('add-modal').style.display = 'flex';
  if (!addOptions) loadAddOptions();
}
function closeAddModal() {
  document.getElementById('add-modal').style.display = 'none';
}
function switchAddTab(tab) {
  document.querySelectorAll('#add-modal .seg').forEach(s => s.classList.toggle('active', s.dataset.tab === tab));
  ['expense', 'income', 'transfer'].forEach(t => {
    document.getElementById('form-' + t).style.display = (t === tab) ? 'flex' : 'none';
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function loadAddOptions() {
  try {
    const r = await fetch('/add/options');
    addOptions = await r.json();
  } catch (e) { return; }
  const today = new Date().toISOString().slice(0, 10);
  document.querySelectorAll('#add-modal .js-today').forEach(i => { if (!i.value) i.value = today; });

  const accHtml = addOptions.accounts.map(a => `<option value="${a.id}">${esc(a.name)}</option>`).join('');
  document.querySelectorAll('#add-modal .js-account').forEach(sel => { sel.innerHTML = accHtml; });

  // Autocompletado de tiendas ya usadas.
  const storeList = document.getElementById('store-list');
  if (storeList) storeList.innerHTML = (addOptions.stores || []).map(s => `<option value="${esc(s)}">`).join('');
  // En transferencia, la cuenta destino por defecto es distinta de la origen.
  const tForm = document.getElementById('form-transfer');
  if (tForm && addOptions.accounts.length > 1) {
    tForm.querySelector('[name=to_account_id]').selectedIndex = 1;
  }

  const profHtml = addOptions.profiles.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  document.querySelectorAll('#add-modal .js-profile').forEach(sel => {
    sel.innerHTML = profHtml;
    sel.addEventListener('change', () => refreshCategories(sel.closest('form')));
  });
  ['expense', 'income'].forEach(t => {
    const form = document.getElementById('form-' + t);
    const catSel = form && form.querySelector('.js-category');
    if (catSel) catSel.addEventListener('change', () => refreshSubcategories(form));
    refreshCategories(form);
  });
}

function refreshCategories(form) {
  if (!form || !addOptions) return;
  const profSel = form.querySelector('.js-profile');
  const catSel = form.querySelector('.js-category');
  if (!profSel || !catSel) return;
  const kind = profSel.dataset.kind;
  const cats = addOptions.categories.filter(c => c.profile === profSel.value && c.kind === kind);
  catSel.innerHTML = cats.length
    ? cats.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('')
    : '<option value="">(sin categorías)</option>';
  refreshSubcategories(form);
}

function refreshSubcategories(form) {
  if (!form || !addOptions) return;
  const profSel = form.querySelector('.js-profile');
  const catSel = form.querySelector('.js-category');
  const subSel = form.querySelector('.js-subcategory');
  if (!subSel || !profSel || !catSel) return;
  const kind = profSel.dataset.kind;
  const cat = addOptions.categories.find(c => c.profile === profSel.value && c.kind === kind && c.name === catSel.value);
  const subs = (cat && cat.subs) || [];
  subSel.innerHTML = '<option value="">Subcategoría (opcional)</option>' +
    subs.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('');
  subSel.style.display = subs.length ? '' : 'none';
}

function showFileName(input) {
  const el = input.closest('form').querySelector('.file-name');
  el.textContent = input.files && input.files[0] ? input.files[0].name : '';
}

function captureLocation(btn) {
  const form = btn.closest('form');
  const status = form.querySelector('.loc-status');
  if (!navigator.geolocation) { status.textContent = 'Geolocalización no disponible'; return; }
  status.textContent = 'Obteniendo ubicación…';
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const { latitude, longitude } = pos.coords;
    form.querySelector('[name=latitude]').value = latitude;
    form.querySelector('[name=longitude]').value = longitude;
    status.textContent = `📍 ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
    // Reverse geocoding best-effort (si no hay red, guardamos solo las coordenadas).
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=16&addressdetails=1`, { headers: { 'Accept': 'application/json' } });
      if (r.ok) {
        const d = await r.json();
        const a = d.address || {};
        const place = d.name || a.road || a.suburb || a.city || a.town || a.village || d.display_name;
        if (place) { form.querySelector('[name=place_name]').value = place; status.textContent = '📍 ' + place; }
      }
    } catch (e) { /* sin conexión */ }
  }, () => { status.textContent = 'No se pudo obtener la ubicación'; }, { enableHighAccuracy: true, timeout: 8000 });
}

// Cerrar con la tecla Escape.
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAddModal(); });
