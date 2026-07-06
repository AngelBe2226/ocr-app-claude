// Tablas de transacciones: colapsar meses, seleccionar todo y barra de acciones flotante.
function toggleMonth(header) {
  header.parentElement.classList.toggle('collapsed');
}

// Colapso genérico de secciones (grupos de cuentas, categorías, etc.).
function toggleGroup(header) {
  header.parentElement.classList.toggle('collapsed');
}

function _form(el) { return el.closest('.tx-form'); }

function toggleSelectAll(cb) {
  const form = _form(cb);
  form.querySelectorAll('.tx-check').forEach(x => { x.checked = cb.checked; });
  updateBulkBar(form);
}

function cancelBulk(btn) {
  const form = _form(btn);
  form.querySelectorAll('.tx-check').forEach(x => { x.checked = false; });
  const sa = form.querySelector('.tx-select-all');
  if (sa) sa.checked = false;
  updateBulkBar(form);
}

function updateBulkBar(form) {
  const n = form.querySelectorAll('.tx-check:checked').length;
  const bar = form.querySelector('.bulk-bar');
  if (bar) {
    bar.style.display = n > 0 ? 'flex' : 'none';
    const c = bar.querySelector('.bulk-count');
    if (c) c.textContent = n;
  }
  const sa = form.querySelector('.tx-select-all');
  if (sa) {
    const total = form.querySelectorAll('.tx-check').length;
    sa.checked = total > 0 && n === total;
    sa.indeterminate = n > 0 && n < total;
  }
}

document.addEventListener('change', e => {
  if (e.target.classList && e.target.classList.contains('tx-check')) {
    updateBulkBar(_form(e.target));
  }
});
