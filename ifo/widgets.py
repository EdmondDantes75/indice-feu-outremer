"""Widget « Indice feu Outre-mer » pour le site : un petit script construit le widget en HTML dans la page.

Contenu du dossier déposé à la racine du site (/indice-feu-outremer/) :
  w.js                  script du widget (aucune dépendance), chargé une fois par page
  accueil.json          données de la page d'accueil (îles, niveaux, dates)
  c/<insee>.json        données d'une commune (trois jours, conditions, sources, tracé de la commune)
  iles/<id>.svg         carte de l'île, communes colorées selon le niveau du jour (accueil)
  iles/fond-<id>.svg    carte de l'île en gris, sans couleur ni texte (pages communes, ne change jamais)
  accueil.html          code à coller dans la page d'accueil
  communes.csv          code à coller dans chaque page commune
  .htaccess             types, compression, cache, scripts serveur interdits

Le texte est produit en HTML par w.js : il prend la police du thème et se réorganise selon la largeur
de l'emplacement (grilles CSS auto-adaptatives), sans dépendre de la largeur de l'écran.
"""
import csv
import datetime as dt
import json
import os
import re
import shutil
from zoneinfo import ZoneInfo

from .config import TERRITOIRES, TZ_COMMUNE

ICI = os.path.dirname(os.path.abspath(__file__))
GEOMETRIE = os.path.join(ICI, '..', 'docs', 'data', 'geometry.json')
SCRIPT = os.path.join(ICI, 'w.js')
DOSSIER_SITE = '/indice-feu-outremer'
FOND = ('#5DB346', '#FFE066', '#F59F00', '#C92A2A')
LIB = ('Faible', 'Modéré', 'Élevé', 'Très élevé')
JOURS = ('lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.')
MOIS = ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.')
VILLE_FUSEAU = {'Europe/Paris': 'Paris', 'America/Guadeloupe': 'Guadeloupe', 'America/Martinique': 'Martinique',
                'America/Marigot': 'Saint-Martin', 'America/St_Barthelemy': 'Saint-Barthélemy', 'America/Cayenne': 'Cayenne',
                'Indian/Reunion': 'La Réunion', 'Indian/Mayotte': 'Mayotte', 'Pacific/Noumea': 'Nouméa',
                'Pacific/Tahiti': 'Tahiti', 'Pacific/Marquesas': 'Marquises', 'Pacific/Gambier': 'Gambier',
                'Pacific/Wallis': 'Wallis', 'America/Miquelon': 'Saint-Pierre'}
SOUS_LIEU = {'pfs': 'îles de la Société', 'pfm': 'Marquises', 'pfa': 'Tuamotu, Gambier, Australes',
             'wl': 'Wallis', 'ft': 'Futuna et Alofi'}
TITRE_ILE = {'pfs': 'Polynésie · Société', 'pfm': 'Polynésie · Marquises', 'pfa': 'Polynésie · archipels',
             'ft': 'Futuna et Alofi'}
CALCULS_UTC = ((5, 55), (15, 55))  # fin habituelle des deux calculs quotidiens
MER, TERRE, BORD = '#E4ECEE', '#D3DAD2', '#FFFFFF'

HTACCESS = '''# Indice feu Outre-mer : fichiers statiques uniquement.
AddType image/svg+xml .svg
AddType application/json .json
AddType text/javascript .js
AddType text/csv .csv
<FilesMatch "\\.(php\\d?|phtml|phar|pl|py|cgi|sh)$">
  Require all denied
</FilesMatch>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE image/svg+xml application/json text/javascript
</IfModule>
<IfModule mod_headers.c>
  Header set X-Content-Type-Options "nosniff"
  <FilesMatch "\\.(json|svg)$">
    Header set Cache-Control "public, max-age=1800"
  </FilesMatch>
  <FilesMatch "^fond-.*\\.svg$">
    Header set Cache-Control "public, max-age=604800"
  </FilesMatch>
  <FilesMatch "\\.js$">
    Header set Cache-Control "public, max-age=86400"
  </FilesMatch>
  <FilesMatch "\\.svg$">
    Header set Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'"
  </FilesMatch>
</IfModule>
'''


# ------------------------------------------------------------------ dates et nombres

def nb(v, d=1):
    return '–' if v is None else f'{v:.{d}f}'.replace('.', ',')


def date_courte(iso):
    d = dt.date.fromisoformat(iso)
    return f'{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}'


def quand(gen_iso, tz):
    t = dt.datetime.fromisoformat(gen_iso.replace('Z', '+00:00')).astimezone(ZoneInfo(tz))
    return f'{t.day} {MOIS[t.month - 1]} à {t.hour} h {t.minute:02d}'


def prochain(gen_iso, tz):
    t = dt.datetime.fromisoformat(gen_iso.replace('Z', '+00:00'))
    for jour in (0, 1):
        for h, m in CALCULS_UTC:
            c = t.replace(hour=h, minute=m, second=0, microsecond=0) + dt.timedelta(days=jour)
            if c > t + dt.timedelta(minutes=30):
                lc = c.astimezone(ZoneInfo(tz))
                return f'{lc.hour if lc.minute < 30 else (lc.hour + 1) % 24} h'
    return ''


def mise_a_jour(gen, tz):
    return f'Mis à jour le {quand(gen, tz)} (heure de {VILLE_FUSEAU.get(tz, tz)}), prochain calcul vers {prochain(gen, tz)}.'


# ------------------------------------------------------------------ cartes (sans texte)

_NUM = re.compile(r'-?\d+(?:\.\d+)?')


def _anneaux(d):
    for part in re.findall(r'M[^M]*', d):
        v = [float(x) for x in _NUM.findall(part)]
        yield list(zip(v[0::2], v[1::2]))


def _simplifie(d, tol):
    """Douglas-Peucker par anneau, coupé en deux moitiés pour garder les anneaux fermés."""
    def dp(pts):
        if len(pts) < 3:
            return pts
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        n = (dx * dx + dy * dy) ** .5 or 1e-9
        i, m = 0, -1.0
        for k in range(1, len(pts) - 1):
            e = abs(dy * (pts[k][0] - x1) - dx * (pts[k][1] - y1)) / n
            if e > m:
                i, m = k, e
        if m <= tol:
            return [pts[0], pts[-1]]
        return dp(pts[:i + 1])[:-1] + dp(pts[i:])
    out = []
    for r in _anneaux(d):
        if len(r) > 6:
            h = len(r) // 2
            r = dp(r[:h + 1])[:-1] + dp(r[h:])
        if len(r) >= 3:
            out.append(_trace(r))
    return ''.join(out)


def _n(v):
    s = f'{v:.1f}'.rstrip('0').rstrip('.')
    s = s.replace('-0.', '-.') if s.startswith('-0.') else (s[1:] if s.startswith('0.') else s)
    return s if s not in ('', '-') else '0'


def _trace(r):
    """Anneau en coordonnées relatives arrondies au dixième (tracé plus court)."""
    x0, y0 = round(r[0][0], 1), round(r[0][1], 1)
    out, px, py = [f'M{_n(x0)} {_n(y0)}l'], x0, y0
    for x, y in r[1:]:
        x, y = round(x, 1), round(y, 1)
        dx, dy = _n(x - px), _n(y - py)
        if dx == '0' and dy == '0':
            continue
        out.append(dx + ('' if dy.startswith('-') else ' ') + dy + ' ')
        px, py = x, y
    return ''.join(out).rstrip() + 'z'


def _anneaux_abs(d):
    """Anneaux d'un tracé relatif « Mx yl dx dy … z » en coordonnées absolues."""
    for part in re.findall(r'M[^M]*', d):
        v = [float(x) for x in _NUM.findall(part)]
        x, y = v[0], v[1]
        pts = [(x, y)]
        for k in range(2, len(v) - 1, 2):
            x, y = x + v[k], y + v[k + 1]
            pts.append((x, y))
        yield pts


def _centre(d):
    """Centre et taille du plus grand anneau (les îlots ne déplacent pas le repère)."""
    def aire(r):
        return abs(sum(r[k][0] * r[k - 1][1] - r[k - 1][0] * r[k][1] for k in range(len(r)))) / 2
    r = max(_anneaux_abs(d), key=aire)
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys))


def charge_geometrie(path=GEOMETRIE, tol=0.5):
    with open(path, encoding='utf-8') as f:
        g = json.load(f)
    for ins in g['insets']:
        for z in ins['shapes']:
            z['d'] = _simplifie(z['d'], tol)
        if ins['base']:
            ins['base'] = _simplifie(ins['base'], tol)
    return g['insets']




def _svg_carte(ins, remplissage):
    """Carte de l'île seule, au cadrage de l'encart : aucun texte, redimensionnable sans perte."""
    w, h = ins['w'], ins['h']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           f'<rect width="{w}" height="{h}" fill="{MER}"/>'
           f'<g stroke="{BORD}" stroke-width=".6" stroke-linejoin="round" vector-effect="non-scaling-stroke">']
    if ins['base']:
        out.append(f'<path fill="#C9D2CA" stroke="none" d="{ins["base"]}"/>')
    for z in ins['shapes']:
        out.append(f'<path fill="{remplissage(z["i"])}" d="{z["d"]}"/>')
    for z in ins['dots']:
        out.append(f'<circle fill="{remplissage(z["i"])}" cx="{z["x"]}" cy="{z["y"]}" r="5"/>')
    out.append('</g></svg>')
    return ''.join(out)


def _niveau(units, i, j):
    u = units.get(i)
    if u and len(u['d']) > j and u['d'][j]:
        return u['d'][j][0]
    return -1


def _max_ile(ins, units, j):
    return max([_niveau(units, z['i'], j) for z in ins['shapes'] + ins['dots']] or [-1])


# ------------------------------------------------------------------ données des widgets

def donnees_accueil(insets, full, small):
    units, dates = full['units'], small['dates']
    iles = []
    for ins in insets:
        iles.append({'n': TITRE_ILE.get(ins['id'], ins['title']), 'd': date_courte(dates[ins['terr']][0]),
                     'a': _max_ile(ins, units, 0), 'b': _max_ile(ins, units, 1),
                     'c': f'iles/{ins["id"]}.svg', 'r': round(ins['w'] / ins['h'], 3)})
    return {'maj': mise_a_jour(small['genere'], 'Europe/Paris'), 'iles': iles}


def _source(r):
    m = 'AROME Outre-mer' if r[13].startswith('AROME') else 'ARPEGE'
    return f'prévision Météo-France {m}' + (', pluie de la veille mesurée' if r[14] == 'pluie mesurée' else '')


def donnees_commune(insee, u, ins, full, small):
    stations, dates, terr = full['stations'], small['dates'], u['t']
    tz = TZ_COMMUNE.get(insee, TERRITOIRES[terr]['tz'])
    jours = []
    for k, lib in enumerate(("Aujourd'hui", 'Demain', 'Après-demain')):
        r = u['d'][k] if len(u['d']) > k else None
        jours.append({'l': lib, 'd': date_courte(r[17] if r else dates[terr][k]),
                      'n': r[0] if r else -1, 'v': nb(r[1]) if r else 'n.d.'})
    r = u['d'][0] if u['d'] else None
    cond, src = [], []
    if r:
        cond = [['Température', f'{nb(r[9], 0)} °C'], ["Humidité de l'air", f'{nb(r[10], 0)} %'],
                ['Vent moyen', f'{nb(r[11], 0)} km/h'], ['Pluie sur 24 h', f'{nb(r[12])} mm'],
                ['Sécheresse du sol (DC)', nb(r[6], 0)], ['Inflammabilité (FFMC)', nb(r[4], 0)]]
        st = stations.get(u['s'])
        if st:
            l1 = f'Sécheresse suivie à la station Météo-France {st["n"]} ({nb(u["sd"])} km)'
            if r[2] == 's':
                l1 += ', niveau donné par la station de la commune'
            src.append(l1 + '.')
        src.append('Météo : ' + _source(r) + '.')
    # tracé de la commune, posé sur la carte grise de l'île
    trace = {'c': f'iles/fond-{ins["id"]}.svg', 'w': ins['w'], 'h': ins['h']}
    for z in ins['shapes']:
        if z['i'] == insee:
            cx, cy, taille = _centre(z['d'])
            trace['p'] = z['d']
            if taille < 22:
                trace['o'] = [round(cx, 1), round(cy, 1)]
    for z in ins['dots']:
        if z['i'] == insee and 'p' not in trace:
            trace['o'] = [z['x'], z['y']]
            trace['k'] = [z['x'], z['y']]
    return {'n': u['n'], 'lieu': f"{terr} · {SOUS_LIEU[ins['id']]}" if ins['id'] in SOUS_LIEU else terr,
            'ile': TITRE_ILE.get(ins['id'], ins['title']), 'carte': trace,
            'j': jours, 'm': cond, 's': src, 'maj': mise_a_jour(small['genere'], tz)}


def code_html(cle, hauteur, script=f'{DOSSIER_SITE}/w.js'):
    return (f'<div data-ifo="{cle}" style="min-height:{hauteur}px"></div>'
            f'<script src="{script}" defer></script>')


def _ecrit_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def ecrire(full, small, out_dir, geometrie=GEOMETRIE):
    insets = charge_geometrie(geometrie)
    units = full['units']
    wd = os.path.join(out_dir, 'widgets')
    if os.path.isdir(wd):
        shutil.rmtree(wd)
    for sous in ('c', 'iles'):
        os.makedirs(os.path.join(wd, sous), exist_ok=True)

    for ins in insets:
        with open(os.path.join(wd, 'iles', f'{ins["id"]}.svg'), 'w', encoding='utf-8') as f:
            f.write(_svg_carte(ins, lambda i: FOND[_niveau(units, i, 0)] if _niveau(units, i, 0) >= 0 else '#B9C2BA'))
        with open(os.path.join(wd, 'iles', f'fond-{ins["id"]}.svg'), 'w', encoding='utf-8') as f:
            f.write(_svg_carte(ins, lambda i: TERRE))
    _ecrit_json(os.path.join(wd, 'accueil.json'), donnees_accueil(insets, full, small))

    ile = {}
    for ins in insets:
        for z in ins['shapes']:
            ile.setdefault(z['i'], ins)
    for ins in insets:
        for z in ins['dots']:
            ile.setdefault(z['i'], ins)
    rows = []
    for insee, u in sorted(units.items()):
        if insee not in ile:
            continue
        _ecrit_json(os.path.join(wd, 'c', f'{insee}.json'), donnees_commune(insee, u, ile[insee], full, small))
        rows.append((insee, u['n'], u['t'], code_html(insee, 520)))
    with open(os.path.join(wd, 'communes.csv'), 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f, delimiter=';')
        wr.writerow(('code_insee', 'commune', 'territoire', 'code_html'))
        wr.writerows(rows)
    with open(os.path.join(wd, 'accueil.html'), 'w', encoding='utf-8') as f:
        f.write(code_html('accueil', 900) + '\n')
    shutil.copy(SCRIPT, os.path.join(wd, 'w.js'))
    with open(os.path.join(wd, '.htaccess'), 'w', encoding='utf-8') as f:
        f.write(HTACCESS)
