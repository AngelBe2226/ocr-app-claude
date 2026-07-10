// Menú cascada in-app para elegir categoría → subcategoría (reemplaza los <select>
// nativos del navegador). Usa addOptions.categories (cargado por add.js). Las categorías
// son globales, así que sólo dependen del tipo (gasto/ingreso).

function _esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function _cascadeKind(el) {
  if (el.dataset.kind) return el.dataset.kind;                 // add modal: tipo fijo por formulario
  const form = el.closest('form');
  const t = form && form.querySelector('.js-etype');
  return t ? t.value : 'expense';                             // edit modal: tipo del <select>
}

function cascadeLabel(el) {
  const cat = el.querySelector('input[data-role=category]').value;
  const sub = el.querySelector('input[data-role=subcategory]').value;
  const lab = el.querySelector('.cascade-label');
  if (!lab) return;
  lab.textContent = cat ? (sub ? cat + ' · ' + sub : cat) : 'Selecciona categoría';
  lab.style.color = cat ? 'var(--ink)' : 'var(--muted)';
}

// Reconstruye el panel del cascada según el tipo. keep=true conserva la selección.
function renderCascade(el, keep) {
  const cats = ((typeof addOptions !== 'undefined' && addOptions && addOptions.categories) || [])
    .filter(c => c.kind === _cascadeKind(el));
  const panel = el.querySelector('.cascade-panel');
  if (!keep) {
    el.querySelector('input[data-role=category]').value = '';
    el.querySelector('input[data-role=subcategory]').value = '';
  }
  // Si no hay categoría elegida, se preselecciona la primera para no enviar vacío.
  const catIn = el.querySelector('input[data-role=category]');
  if (!catIn.value && cats.length) catIn.value = cats[0].name;
  panel.innerHTML = cats.length ? cats.map(c => {
    const hasSubs = c.subs && c.subs.length;
    const subs = hasSubs ? `<div class="cascade-subs">${c.subs.map(s =>
      `<button type="button" class="cascade-sub" data-cat="${_esc(c.name)}" data-sub="${_esc(s)}">${_esc(s)}</button>`).join('')}</div>` : '';
    return `<div class="cascade-cat-row">
      <div class="cascade-cat-head">
        <button type="button" class="cascade-cat" data-cat="${_esc(c.name)}">${_esc(c.name)}</button>
        ${hasSubs ? `<button type="button" class="cascade-exp" title="Ver subcategorías">›</button>` : ''}
      </div>${subs}
    </div>`;
  }).join('') : '<div style="padding:10px;color:var(--muted);font-size:12px;">(sin categorías)</div>';
  cascadeLabel(el);
}

function cascadeInit(scope) {
  (scope || document).querySelectorAll('.cascade').forEach(el => renderCascade(el, true));
}

// Fija la selección (usado al abrir el modal de editar).
function cascadeSet(el, category, subcategory) {
  el.querySelector('input[data-role=category]').value = category || '';
  el.querySelector('input[data-role=subcategory]').value = subcategory || '';
  renderCascade(el, true);
}

function toggleCascade(trigger) {
  const el = trigger.closest('.cascade');
  const panel = el.querySelector('.cascade-panel');
  const open = getComputedStyle(panel).display === 'none';
  document.querySelectorAll('.cascade-panel').forEach(p => { p.style.display = 'none'; });
  if (open) { renderCascade(el, true); panel.style.display = 'block'; }
}

document.addEventListener('click', e => {
  const t = e.target;
  if (!(t instanceof Element)) return;
  if (t.classList.contains('cascade-exp')) {
    const row = t.closest('.cascade-cat-row');
    const subs = row && row.querySelector('.cascade-subs');
    if (subs) { subs.classList.toggle('open'); t.classList.toggle('open'); }
    return;
  }
  if (t.classList.contains('cascade-cat')) {
    const el = t.closest('.cascade');
    el.querySelector('input[data-role=category]').value = t.dataset.cat;
    el.querySelector('input[data-role=subcategory]').value = '';
    cascadeLabel(el);
    el.querySelector('.cascade-panel').style.display = 'none';
    return;
  }
  if (t.classList.contains('cascade-sub')) {
    const el = t.closest('.cascade');
    el.querySelector('input[data-role=category]').value = t.dataset.cat;
    el.querySelector('input[data-role=subcategory]').value = t.dataset.sub;
    cascadeLabel(el);
    el.querySelector('.cascade-panel').style.display = 'none';
    return;
  }
  if (!t.closest('.cascade')) {
    document.querySelectorAll('.cascade-panel').forEach(p => { p.style.display = 'none'; });
  }
});
