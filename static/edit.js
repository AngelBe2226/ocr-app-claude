// Modal para editar una transacción existente. Reutiliza addOptions/esc/loadAddOptions de add.js
// y el menú cascada de cascade.js para elegir categoría → subcategoría.
async function openEditModal(id) {
  document.getElementById('edit-modal').style.display = 'flex';
  if (!addOptions) await loadAddOptions();
  const form = document.getElementById('form-edit');
  form.querySelector('.js-eprofile').innerHTML = addOptions.profiles.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  form.querySelector('.js-eaccount').innerHTML = addOptions.accounts.map(a => `<option value="${a.id}">${esc(a.name)}</option>`).join('');

  let t;
  try { t = await (await fetch(`/transactions/${id}/json`)).json(); } catch (e) { return; }
  form.setAttribute('action', `/transactions/${id}/edit`);
  form.querySelector('.js-etype').value = t.type;
  form.querySelector('.js-eprofile').value = t.profile;
  // Categoría/subcategoría vía menú cascada (depende del tipo, ya fijado arriba).
  const cascade = document.getElementById('edit-cascade');
  if (cascade && typeof cascadeSet === 'function') cascadeSet(cascade, t.category, t.subcategory);
  form.querySelector('.js-estore').value = t.store || '';
  const eqty = form.querySelector('.js-equantity');
  if (eqty) eqty.value = t.quantity || '-';
  form.querySelector('.js-eaccount').value = t.account_id;
  form.querySelector('.js-eamount').value = t.amount;
  form.querySelector('.js-edate').value = t.date;
  form.querySelector('.js-enote').value = t.note;
}

function closeEditModal() {
  document.getElementById('edit-modal').style.display = 'none';
}

// Al cambiar el tipo (gasto/ingreso), la lista de categorías del cascada cambia.
document.addEventListener('change', e => {
  if (e.target.classList && e.target.classList.contains('js-etype')) {
    const cascade = document.getElementById('edit-cascade');
    if (cascade && typeof renderCascade === 'function') renderCascade(cascade, false);
  }
});
