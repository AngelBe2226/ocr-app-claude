// Selector de iconos: al pulsar una opción, fija el input oculto y resalta la selección.
function pickIcon(btn) {
  const picker = btn.closest('.icon-picker');
  if (!picker) return;
  picker.querySelector('.icon-input').value = btn.dataset.icon || '';
  picker.querySelectorAll('.icon-opt').forEach(b => b.classList.remove('sel'));
  btn.classList.add('sel');
}
