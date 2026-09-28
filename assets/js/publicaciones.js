// Filtro por tipo en /publicaciones/. Sin JavaScript se ve la lista completa.
(function () {
  var barra = document.querySelector('.filtros');
  if (!barra) return;
  barra.hidden = false;
  var botones = barra.querySelectorAll('button');
  barra.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    var f = b.dataset.filtro;
    botones.forEach(function (x) { x.setAttribute('aria-pressed', x === b); });
    document.querySelectorAll('.pub').forEach(function (p) {
      p.hidden = f !== 'todas' && p.dataset.categoria !== f;
    });
    document.querySelectorAll('[data-anio]').forEach(function (s) {
      s.hidden = !s.querySelector('.pub:not([hidden])');
    });
  });
})();
