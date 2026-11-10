/* Indice feu Outre-mer, Météo des Forêts. Widget sans dépendance.
   Usage : <div data-ifo="accueil"></div> ou <div data-ifo="97209"></div>
           <script src="/indice-feu-outremer/w.js" defer></script> */
(function () {
  var s = document.currentScript, B = (s && s.src ? s.src : '/indice-feu-outremer/w.js').replace(/w\.js(\?.*)?$/, '');
  var L = ['Faible', 'Modéré', 'Élevé', 'Très élevé'], F = ['#5DB346', '#FFE066', '#F59F00', '#C92A2A'],
      E = ['#0F2A12', '#3A2E00', '#2E1A00', '#fff'];
  var M = 'Indice personnel calculé par Météo des Forêts (méthode IFM), non produit par Météo-France, ' +
          'à partir des données Météo-France. Consignes officielles prioritaires. ';
  var C = '.ifo{box-sizing:border-box;border:1px solid #D8E0D6;border-radius:12px;background:#fff;color:#13241A;' +
    'padding:16px;margin:1em 0;line-height:1.45;text-align:left}.ifo *{box-sizing:border-box}.ifo.ifo p{margin:0;padding:0}' +
    '.ifo-t{font-weight:700;font-size:1.3em;line-height:1.2;color:#0A2F19}.ifo-s{color:#58675D;font-size:.9em;margin-top:2px!important}' +
    '.ifo-p{display:inline-block;padding:.1em .6em;border-radius:5px;font-weight:700;font-size:.85em;white-space:nowrap}' +
    '.ifo-lg{display:flex;flex-wrap:wrap;gap:4px 14px;margin:10px 0 12px;font-size:.85em;color:#58675D}' +
    '.ifo-sq{display:inline-block;width:.8em;height:.8em;border-radius:2px;margin-right:5px;vertical-align:-.05em}' +
    '.ifo-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,180px),1fr));gap:10px}' +
    '.ifo-k{border:1px solid #D8E0D6;border-radius:9px;padding:10px;display:flex;flex-direction:column;gap:6px;min-width:0}' +
    '.ifo-n{font-weight:700;color:#0A2F19}.ifo-r{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;font-size:.9em;color:#58675D}' +
    '.ifo.ifo img{display:block;width:100%;height:auto;margin:0;border-radius:7px;background:#E4ECEE;box-shadow:none}' +
    '.ifo-k img{aspect-ratio:4/3;object-fit:contain}.ifo-dm{font-size:.85em;color:#58675D;margin-top:auto!important}.ifo-f{font-size:.78em;color:#58675D;margin-top:12px!important}' +
    '.ifo-c{display:flex;flex-wrap:wrap;gap:16px 20px}.ifo-m{flex:1 1 220px;max-width:440px;min-width:0}' +
    '.ifo-i{flex:999 1 300px;min-width:0}.ifo-map{position:relative}.ifo-map svg{position:absolute;inset:0;width:100%;height:100%}' +
    '.ifo-j{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:10px;margin:14px 0}' +
    '.ifo-j div{display:flex;flex-direction:column;gap:3px;font-size:.9em}.ifo-j b{color:#0A2F19}.ifo-j .ifo-p{align-self:flex-start}.ifo-j span{color:#58675D}' +
    '.ifo-h{font-weight:700;font-size:.9em;color:#0A2F19}' +
    '.ifo-dl{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,210px),1fr));gap:2px 20px;margin:6px 0 10px;font-size:.9em}' +
    '.ifo-dl div{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #EEF1EC;padding:3px 0}' +
    '.ifo-dl dt{color:#58675D;margin:0;font-weight:400}.ifo-dl dd{margin:0;font-weight:700;white-space:nowrap}.ifo-src{font-size:.82em;color:#58675D}';

  function e(t) { return String(t).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }
  function p(n) {
    return n >= 0 ? '<span class="ifo-p" style="background:' + F[n] + ';color:' + E[n] + '">' + L[n] + '</span>'
                  : '<span class="ifo-p" style="background:#E2E6E1;color:#4A554D">n.d.</span>';
  }
  function sq(n) { return '<i class="ifo-sq" style="background:' + F[n] + '"></i>'; }

  function accueil(d) {
    var h = '<p class="ifo-t">Indice feu Outre-mer</p><p class="ifo-s">Niveau du jour par commune, dates en heure locale de chaque territoire</p><div class="ifo-lg">';
    for (var k = 0; k < 4; k++) h += '<span>' + sq(k) + L[k] + '</span>';
    h += '</div><div class="ifo-g">';
    d.iles.forEach(function (i) {
      h += '<div class="ifo-k"><p class="ifo-n">' + e(i.n) + '</p><div class="ifo-r">' + p(i.a) + '<span>' + e(i.d) + '</span></div>' +
        '<img src="' + B + e(i.c) + '" width="300" height="225" loading="lazy" decoding="async" alt="Carte : ' +
        e(i.n) + ', communes colorées selon le niveau du jour">' +
        '<p class="ifo-dm">Demain : ' + (i.b >= 0 ? sq(i.b) + L[i.b].toLowerCase() : 'n.d.') + '</p></div>';
    });
    return h + '</div><p class="ifo-f">' + M + e(d.maj) + '</p>';
  }

  function commune(d) {
    var c = d.carte, j = d.j[0], col = j.n >= 0 ? F[j.n] : '#B9C2BA', r = c.w * 0.045, o = '';
    if (c.p) o += '<path d="' + e(c.p) + '" fill="' + col + '" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    if (c.k) o += '<circle cx="' + c.k[0] + '" cy="' + c.k[1] + '" r="7" fill="' + col + '" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    if (c.o) o += '<circle cx="' + c.o[0] + '" cy="' + c.o[1] + '" r="' + r.toFixed(1) + '" fill="none" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    var h = '<div class="ifo-c"><div class="ifo-m"><div class="ifo-map"><img src="' + B + e(c.c) + '" width="' + c.w + '" height="' + c.h +
      '" loading="lazy" decoding="async" alt="Carte : ' + e(d.ile) + ', ' + e(d.n) + ' mise en évidence">' +
      '<svg viewBox="0 0 ' + c.w + ' ' + c.h + '" aria-hidden="true">' + o + '</svg></div></div><div class="ifo-i">' +
      '<p class="ifo-t">' + e(d.n) + '</p><p class="ifo-s">' + e(d.lieu) + ' · Indice feu Outre-mer</p><div class="ifo-j">';
    d.j.forEach(function (x) {
      h += '<div><b>' + e(x.l) + '</b><span>' + e(x.d) + '</span>' + p(x.n) + '<span>IFM ' + e(x.v) + '</span></div>';
    });
    h += '</div>';
    if (d.m.length) {
      h += '<p class="ifo-h">Conditions prévues aujourd\'hui à midi (heure locale)</p><dl class="ifo-dl">';
      d.m.forEach(function (x) { h += '<div><dt>' + e(x[0]) + '</dt><dd>' + e(x[1]) + '</dd></div>'; });
      h += '</dl>';
    }
    d.s.forEach(function (x) { h += '<p class="ifo-src">' + e(x) + '</p>'; });
    return h + '</div></div><p class="ifo-f">' + M + e(d.maj) + '</p>';
  }

  function go() {
    if (!document.getElementById('ifo-css')) {
      var st = document.createElement('style'); st.id = 'ifo-css'; st.textContent = C; document.head.appendChild(st);
    }
    var els = document.querySelectorAll('[data-ifo]');
    Array.prototype.forEach.call(els, function (el) {
      if (el.getAttribute('data-ifo-ok')) return;
      el.setAttribute('data-ifo-ok', '1');
      var k = el.getAttribute('data-ifo'), acc = k === 'accueil';
      if (!acc && !/^\d{5}$/.test(k)) return;
      fetch(B + (acc ? 'accueil.json' : 'c/' + k + '.json'))
        .then(function (r) { if (!r.ok) throw r.status; return r.json(); })
        .then(function (d) { el.className += ' ifo'; el.innerHTML = acc ? accueil(d) : commune(d); el.style.minHeight = ''; })
        .catch(function () { el.style.minHeight = ''; });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
