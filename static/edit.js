// Modal para editar una transacción existente. Reutiliza addOptions/esc/loadAddOptions de add.js.
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
  refreshEditCategories();
  const catSel = form.querySelector('.js-ecategory');
  catSel.value = t.category;
  // Si la categoría actual no está en la lista (p.ej. "Sin categoría"), la añadimos.
  if (catSel.value !== t.category) {
    const o = document.createElement('option');
    o.value = t.category; o.textContent = t.category;
    catSel.appendChild(o); catSel.value = t.category;
  }
  form.querySelector('.js-eaccount').value = t.account_id;
  form.querySelector('.js-eamount').value = t.amount;
  form.querySelector('.js-edate').value = t.date;
  form.querySelector('.js-enote').value = t.note;
}

function closeEditModal() {
  document.getElementById('edit-modal').style.display = 'none';
}

function refreshEditCategories() {
  const form = document.getElementById('form-edit');
  if (!addOptions) return;
  const kind = form.querySelector('.js-etype').value;
  const profile = form.querySelector('.js-eprofile').value;
  const cats = addOptions.categories.filter(c => c.profile === profile && c.kind === kind);
  form.querySelector('.js-ecategory').innerHTML = cats.length
    ? cats.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('')
    : '<option value="">(sin categorías)</option>';
}

document.addEventListener('change', e => {
  if (e.target.classList && (e.target.classList.contains('js-etype') || e.target.classList.contains('js-eprofile'))) {
    refreshEditCategories();
  }
});
