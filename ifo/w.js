/* Indice feu Outre-mer, Météo des Forêts. Widget sans dépendance.
   Usage : <div data-ifo="accueil"></div> ou <div data-ifo="97209"></div>
           puis le script /indice-feu-outremer/w.js chargé avec defer (voir accueil.html). */
(function () {
  var s = document.currentScript, B = (s && s.src ? s.src : '/indice-feu-outremer/w.js').replace(/w\.js(\?.*)?$/, '');
  var L = ['Faible', 'Modéré', 'Élevé', 'Très élevé'], F = ['#5DB346', '#FFE066', '#F59F00', '#C92A2A'],
      E = ['#0F2A12', '#3A2E00', '#2E1A00', '#fff'];
  var M = 'Indice personnel calculé par Météo des Forêts (méthode IFM), non produit par Météo-France, ' +
          'à partir des données Météo-France. Consignes officielles prioritaires. ';
  var K = ['Risque faible : restez vigilant avec tout feu en extérieur.',
           'Évitez les feux en plein air et ne jetez pas de mégots dans la végétation.',
           'Pas de feu ni de brûlage de végétaux ; évitez les travaux à étincelles près de la végétation sèche.',
           'Aucun feu en extérieur ; reportez les travaux à étincelles ; signalez immédiatement toute fumée suspecte.'];
  var C = '.ifo{box-sizing:border-box;border:1px solid #D8E0D6;border-radius:12px;background:#fff;color:#13241A;' +
    'padding:16px;margin:1em 0;line-height:1.45;text-align:left}.ifo *{box-sizing:border-box}.ifo.ifo p{margin:0;padding:0}' +
    '.ifo.ifo a{color:#1F5A3A;text-decoration:underline;text-underline-offset:2px}' +
    '.ifo-t{font-weight:700;font-size:1.3em;line-height:1.2;color:#0A2F19}.ifo-s{color:#58675D;font-size:.9em;margin-top:2px!important}' +
    '.ifo-p{display:inline-block;padding:.1em .6em;border-radius:5px;font-weight:700;font-size:.85em;white-space:nowrap}' +
    '.ifo-lg{display:flex;flex-wrap:wrap;gap:4px 14px;margin:10px 0 12px;font-size:.85em;color:#58675D}' +
    '.ifo-sq{display:inline-block;width:.8em;height:.8em;border-radius:2px;margin-right:5px;vertical-align:-.05em}' +
    '.ifo-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,128px),1fr));gap:10px}' +
    '.ifo-k{border:1px solid #D8E0D6;border-radius:9px;padding:10px;display:flex;flex-direction:column;gap:6px;min-width:0}' +
    '.ifo-n{font-weight:700;color:#0A2F19;line-height:1.25}.ifo.ifo .ifo-n a{color:#0A2F19}' +
    '.ifo-r{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;font-size:.9em;color:#58675D}' +
    '.ifo.ifo img{display:block;width:100%;height:auto;margin:0;border-radius:7px;background:#E4ECEE;box-shadow:none}' +
    '.ifo-k img{aspect-ratio:4/3;object-fit:contain}.ifo-ag{font-size:.75em;color:#58675D;font-style:italic}' +
    '.ifo-m .ifo-ag{margin-top:4px!important}.ifo-dm,.ifo-x{font-size:.85em;color:#58675D}.ifo-dm{margin-top:auto!important}' +
    '.ifo-f{font-size:.78em;color:#58675D;margin-top:12px!important}' +
    '.ifo-w{background:#FFF4E5;border:1px solid #F59F00;border-radius:8px;padding:8px 10px;font-size:.88em;margin-bottom:12px!important}' +
    '.ifo-c{display:flex;flex-wrap:wrap;gap:16px 20px}.ifo-m{flex:1 1 220px;max-width:440px;min-width:0}' +
    '.ifo-i{flex:999 1 300px;min-width:0}.ifo-map{position:relative;margin:0 auto}.ifo-map svg{position:absolute;inset:0;width:100%;height:100%}' +
    '.ifo-j{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:10px;margin:14px 0 8px}' +
    '.ifo-j div{display:flex;flex-direction:column;gap:3px;font-size:.9em}.ifo-j b{color:#0A2F19}.ifo-j span{color:#58675D}' +
    '.ifo-j .ifo-q{display:flex;align-items:center;gap:6px}.ifo-a{font-weight:700;color:#13241A}' +
    '.ifo-h{font-weight:700;font-size:.9em;color:#0A2F19}.ifo-fp{font-size:.9em;margin-bottom:12px!important}' +
    '.ifo-dl{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,210px),1fr));gap:2px 20px;margin:6px 0 10px;font-size:.9em}' +
    '.ifo-dl div{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #EEF1EC;padding:3px 0}' +
    '.ifo-dl dt{color:#58675D;margin:0;font-weight:400}.ifo-dl dd{margin:0;font-weight:700;white-space:nowrap}' +
    '.ifo-src{font-size:.82em;color:#58675D}' +
    '.ifo-cs{border-left:4px solid;padding:6px 12px;margin:12px 0 6px!important;font-size:.9em;background:#F7F9F5;border-radius:0 6px 6px 0}' +
    '.ifo-u{font-size:.9em;font-weight:700;margin-bottom:10px!important}';

  function e(t) { return String(t).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }
  function a(href, txt) { return href ? '<a href="' + e((window.IFO_ORIGINE || '') + href) + '">' + txt + '</a>' : txt; }
  function p(n) {
    return n >= 0 ? '<span class="ifo-p" style="background:' + F[n] + ';color:' + E[n] + '">' + L[n] + '</span>'
                  : '<span class="ifo-p" style="background:#E2E6E1;color:#4A554D">n.d.</span>';
  }
  function sq(n) { return '<i class="ifo-sq" style="background:' + F[n] + '"></i>'; }
  function vieux(d) {
    var t = Date.parse(d.gen);
    return t && Date.now() - t > 30 * 3600e3 ? '<p class="ifo-w">Attention : ces données ont plus de 30 heures et ne sont peut-être plus à jour. ' + e(d.maj) + '</p>' : '';
  }
  function pied(d) {
    return '<p class="ifo-f">' + M + e(d.maj) + (d.me ? ' ' + a(d.me, 'Méthode et sources') : '') + '</p>';
  }

  function accueil(d) {
    var h = vieux(d) + '<p class="ifo-t">Indice feu Outre-mer</p><p class="ifo-s">Niveau du jour par commune, dates en heure locale de chaque territoire</p><div class="ifo-lg">';
    for (var k = 0; k < 4; k++) h += '<span>' + sq(k) + L[k] + '</span>';
    h += '</div><div class="ifo-g">';
    d.iles.forEach(function (i) {
      h += '<div class="ifo-k"><p class="ifo-n">' + a(i.l, e(i.n)) + '</p><div class="ifo-r">' + p(i.a) + '<span>' + e(i.d) + '</span></div>' +
        '<img src="' + B + e(i.c) + '" width="300" height="225" loading="lazy" decoding="async" alt="Carte : ' +
        e(i.n) + ', communes colorées selon le niveau du jour">' +
        (i.g ? '<p class="ifo-ag">Îles agrandies pour rester visibles</p>' : '') +
        (i.e ? '<p class="ifo-x">À surveiller : ' + a(i.e[1], e(i.e[0])) + '</p>' : '') +
        '<p class="ifo-dm">Demain : ' + (i.b >= 0 ? sq(i.b) + L[i.b].toLowerCase() : 'n.d.') + '</p></div>';
    });
    return h + '</div>' + pied(d);
  }

  function commune(d) {
    var c = d.carte, j = d.j[0], col = j.n >= 0 ? F[j.n] : '#B9C2BA', r = c.w * 0.045, o = '';
    if (c.p) o += '<path d="' + e(c.p) + '" fill="' + col + '" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    if (c.k) o += '<circle cx="' + c.k[0] + '" cy="' + c.k[1] + '" r="7" fill="' + col + '" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    if (c.o) o += '<circle cx="' + c.o[0] + '" cy="' + c.o[1] + '" r="' + r.toFixed(1) + '" fill="none" stroke="#13241A" stroke-width="2" vector-effect="non-scaling-stroke"/>';
    var h = vieux(d) + '<div class="ifo-c"><div class="ifo-m"><div class="ifo-map" style="max-width:' + Math.round(320 * c.w / c.h) + 'px"><img src="' + B + e(c.c) + '" width="' + c.w + '" height="' + c.h +
      '" loading="lazy" decoding="async" alt="Carte : ' + e(d.ile) + ', ' + e(d.n) + ' mise en évidence">' +
      '<svg viewBox="0 0 ' + c.w + ' ' + c.h + '" aria-hidden="true">' + o + '</svg></div>' +
      (c.g ? '<p class="ifo-ag">Îles agrandies pour rester visibles</p>' : '') + '</div><div class="ifo-i">' +
      '<p class="ifo-t">' + e(d.n) + '</p><p class="ifo-s">' + e(d.lieu) + ' · Indice feu Outre-mer</p><div class="ifo-j">';
    d.j.forEach(function (x, k) {
      var prev = k ? d.j[k - 1].n : -1, t = '';
      if (k && x.n >= 0 && prev >= 0) {
        t = x.n > prev ? ['↗', 'en hausse'] : x.n < prev ? ['↘', 'en baisse'] : ['→', 'stable'];
        t = '<span class="ifo-a" title="' + t[1] + '" aria-label="' + t[1] + '">' + t[0] + '</span>';
      }
      h += '<div><b>' + e(x.l) + '</b><span>' + e(x.d) + '</span><span class="ifo-q">' + p(x.n) + t + '</span><span>IFM ' + e(x.v) + '</span></div>';
    });
    h += '</div>';
    if (d.f) h += '<p class="ifo-fp">Facteur principal aujourd\'hui : <b>' + e(d.f) + '</b></p>';
    if (j.n >= 0) h += '<p class="ifo-cs" style="border-color:' + F[j.n] + '">' + K[j.n] + '</p>';
    if (d.u) h += '<p class="ifo-u">En cas de départ de feu : appelez le ' + e(d.u) + '.</p>';
    if (d.m.length) {
      h += '<p class="ifo-h">Conditions prévues aujourd\'hui à midi (heure locale)</p><dl class="ifo-dl">';
      d.m.forEach(function (x) { h += '<div><dt>' + e(x[0]) + '</dt><dd>' + e(x[1]) + '</dd></div>'; });
      h += '</dl>';
    }
    d.s.forEach(function (x) { h += '<p class="ifo-src">' + e(x) + '</p>'; });
    if (d.lt) h += '<p class="ifo-src" style="margin-top:6px!important">' + a(d.lt, 'Toutes les informations pour ' + e(d.t)) + '</p>';
    return h + '</div></div>' + pied(d);
  }

  function charge(el) {
    var k = el.getAttribute('data-ifo'), acc = k === 'accueil';
    if (!acc && !/^\d{5}$/.test(k)) return;
    el.setAttribute('role', 'region');
    el.setAttribute('aria-label', 'Indice feu Outre-mer');
    fetch(B + (acc ? 'accueil.json' : 'c/' + k + '.json'))
      .then(function (r) { if (!r.ok) throw r.status; return r.json(); })
      .then(function (d) { el.className += ' ifo'; el.innerHTML = acc ? accueil(d) : commune(d); })
      .catch(function () {
        el.className = el.className.replace(/\bifo-res(-a)?\b/g, '') + ' ifo';
        el.innerHTML = '<p class="ifo-f">Indice feu Outre-mer momentanément indisponible.</p>';
      });
  }

  function go() {
    if (!document.getElementById('ifo-css')) {
      var st = document.createElement('style'); st.id = 'ifo-css'; st.textContent = C; document.head.appendChild(st);
    }
    var io = 'IntersectionObserver' in window && new IntersectionObserver(function (es) {
      es.forEach(function (x) { if (x.isIntersecting) { io.unobserve(x.target); charge(x.target); } });
    }, { rootMargin: '600px 0px' });
    Array.prototype.forEach.call(document.querySelectorAll('[data-ifo]'), function (el) {
      if (el.getAttribute('data-ifo-ok')) return;
      el.setAttribute('data-ifo-ok', '1');
      if (io) io.observe(el); else charge(el);
    });
  }
  window.IFO_GO = go;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
