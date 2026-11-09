"""Images SVG statiques à intégrer par <picture>/<img> : aucun script, aucun plugin.

docs/widgets/accueil.svg, accueil-mobile.svg      carte de chaque île, niveau du jour par commune
docs/widgets/commune/<insee>.svg, -mobile.svg     carte de l'île avec la commune, trois jours et conditions du jour
docs/widgets/communes.csv                         code INSEE, commune, territoire, code HTML prêt à coller
docs/widgets/.htaccess                            réglages Apache du dossier déposé sur le site

La version « mobile » est choisie par le navigateur sous 700 px (accueil) ou 640 px (commune)
grâce à <picture><source media=…>, sans JavaScript.
"""
import csv
import datetime as dt
import json
import os
import re
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from .config import TERRITOIRES, TZ_COMMUNE

FOND = ('#5DB346', '#FFE066', '#F59F00', '#C92A2A')
ENCRE = ('#0F2A12', '#3A2E00', '#2E1A00', '#FFFFFF')
LIB = ('Faible', 'Modéré', 'Élevé', 'Très élevé')
POLICE = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
JOURS = ('lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.')
MOIS = ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.')
VILLE_FUSEAU = {'Europe/Paris': 'Paris', 'America/Guadeloupe': 'Guadeloupe', 'America/Martinique': 'Martinique',
                'America/Marigot': 'Saint-Martin', 'America/St_Barthelemy': 'Saint-Barthélemy', 'America/Cayenne': 'Cayenne',
                'Indian/Reunion': 'La Réunion', 'Indian/Mayotte': 'Mayotte', 'Pacific/Noumea': 'Nouméa',
                'Pacific/Tahiti': 'Tahiti', 'Pacific/Marquesas': 'Marquises', 'Pacific/Gambier': 'Gambier',
                'Pacific/Wallis': 'Wallis', 'America/Miquelon': 'Saint-Pierre'}
SOUS_LIEU = {'pfs': 'îles de la Société', 'pfm': 'Marquises', 'pfa': 'Tuamotu, Gambier, Australes',
             'wl': 'Wallis', 'ft': 'Futuna et Alofi'}
TITRE_COURT = {'pfs': 'Polynésie · Société', 'pfm': 'Polynésie · Marquises', 'pfa': 'Polynésie · archipels',
               'ft': 'Futuna et Alofi'}
CALCULS_UTC = ((5, 55), (15, 55))  # fin habituelle des deux calculs quotidiens
BASE_URL = 'https://edmonddantes75.github.io/indice-feu-outremer'
DOSSIER_SITE = '/indice-feu-outremer'
GEOMETRIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'data', 'geometry.json')

STYLE = ('<style>.m path,.m circle{stroke:#fff;stroke-width:.6;vector-effect:non-scaling-stroke}'
         '.l0{fill:#5DB346}.l1{fill:#FFE066}.l2{fill:#F59F00}.l3{fill:#C92A2A}.lx{fill:#B9C2BA}.g{fill:#D3DAD2}'
         '.b{fill:#C9D2CA;stroke:none!important}.t{fill:#13241A}.s{fill:#58675D}.e{fill:#0A2F19}'
         '.h{stroke:#13241A!important;stroke-width:2!important}</style>')

HTACCESS = '''# Dossier d'images de l'indice feu Outre-mer : fichiers statiques uniquement.
AddType image/svg+xml .svg
AddType text/csv .csv
<FilesMatch "\\.(php\\d?|phtml|phar|pl|py|cgi|sh)$">
  Require all denied
</FilesMatch>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE image/svg+xml
</IfModule>
<IfModule mod_headers.c>
  <FilesMatch "\\.svg$">
    Header set Cache-Control "public, max-age=1800"
    Header set X-Content-Type-Options "nosniff"
    Header set Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'"
  </FilesMatch>
</IfModule>
'''


# ------------------------------------------------------------------ outils

def nb(v, d=1):
    if v is None:
        return '–'
    s = f'{v:.{d}f}'.replace('.', ',')
    return s


def date_courte(iso):
    d = dt.date.fromisoformat(iso)
    return f'{JOURS[d.weekday()]}\u00a0{d.day}\u00a0{MOIS[d.month - 1]}'


def heure(t):
    return f'{t.hour}\u00a0h\u00a0{t.minute:02d}'


def quand(gen_iso, tz):
    t = dt.datetime.fromisoformat(gen_iso.replace('Z', '+00:00')).astimezone(ZoneInfo(tz))
    return f'{t.day}\u00a0{MOIS[t.month - 1]} à {heure(t)}'


def prochain(gen_iso, tz):
    t = dt.datetime.fromisoformat(gen_iso.replace('Z', '+00:00'))
    for jour in (0, 1):
        for h, m in CALCULS_UTC:
            c = t.replace(hour=h, minute=m, second=0, microsecond=0) + dt.timedelta(days=jour)
            if c > t + dt.timedelta(minutes=30):
                lc = c.astimezone(ZoneInfo(tz))
                return f'{lc.hour}\u00a0h' if lc.minute < 30 else f'{(lc.hour + 1) % 24}\u00a0h'
    return ''


def largeur(texte, taille, gras=False):
    """Largeur approximative d'un texte en police sans empattement."""
    return len(texte) * taille * (0.58 if gras else 0.53)


def ajuste(texte, taille, dispo, gras=False, mini=9):
    while taille > mini and largeur(texte, taille, gras) > dispo:
        taille -= 0.5
    return taille


def txt(x, y, s, taille, cls='t', gras=False, ancre=None, extra=''):
    a = f' text-anchor="{ancre}"' if ancre else ''
    g = ' font-weight="700"' if gras else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{taille}" class="{cls}"{g}{a}{extra}>{escape(s)}</text>'


def pastille(x, y, w, h, lvl, taille=12):
    if lvl is None or lvl < 0:
        return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="5" fill="#E2E6E1"/>'
                + txt(x + w / 2, y + h / 2 + taille * 0.36, 'n.d.', taille, 's', True, 'middle'))
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="5" fill="{FOND[lvl]}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + taille * 0.36:.1f}" font-size="{taille}" font-weight="700" '
            f'text-anchor="middle" fill="{ENCRE[lvl]}">{LIB[lvl]}</text>')


def legende(x, y, taille=11.5):
    out, cx = [], x
    for k, l in enumerate(LIB):
        out.append(f'<rect x="{cx:.1f}" y="{y - taille + 2:.1f}" width="{taille}" height="{taille}" rx="3" fill="{FOND[k]}"/>')
        out.append(txt(cx + taille + 5, y, l, taille, 's'))
        cx += taille + 5 + largeur(l, taille) + 14
    return ''.join(out), cx - x


def svg(w, h, titre, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h:.0f}" viewBox="0 0 {w} {h:.0f}" role="img" '
            f'font-family="{POLICE}"><title>{escape(titre)}</title>{STYLE}'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1:.0f}" rx="12" fill="#FFFFFF" stroke="#D8E0D6"/>{corps}</svg>')


# ------------------------------------------------------------------ cartes

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


def carte(ins, x, y, bw, bh, classe, mise_en_avant=None):
    """Île `ins` centrée dans la boîte (x, y, bw, bh). classe(insee) -> classe CSS de remplissage."""
    s = min(bw / ins['w'], bh / ins['h'])
    tx, ty = x + (bw - ins['w'] * s) / 2, y + (bh - ins['h'] * s) / 2
    out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="7" fill="#E4ECEE"/>',
           f'<g class="m" transform="translate({tx:.1f} {ty:.1f}) scale({s:.4f})">']
    if ins['base']:
        out.append(f'<path class="b" d="{ins["base"]}"/>')
    repere = None
    for z in ins['shapes']:
        h = ' h' if z['i'] == mise_en_avant else ''
        out.append(f'<path class="{classe(z["i"])}{h}" d="{z["d"]}"/>')
        if h:
            repere = _centre(z['d'])
    r_dot = 5.5 / max(s, .5) if s < 1 else 5.5
    for z in ins['dots']:
        h = ' h' if z['i'] == mise_en_avant else ''
        out.append(f'<circle class="{classe(z["i"])}{h}" cx="{z["x"]}" cy="{z["y"]}" r="{r_dot * (1.4 if h else 1):.1f}"/>')
        if h:
            repere = (z['x'], z['y'], 0)
    out.append('</g>')
    if repere:
        cx, cy, taille = repere
        px, py = tx + cx * s, ty + cy * s
        if taille * s < 26:  # petite commune : cercle repère autour
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="11" fill="none" stroke="#13241A" stroke-width="2"/>')
    return ''.join(out)


# ------------------------------------------------------------------ accueil

def _niveaux_ile(ins, units, j):
    m = -1
    for z in ins['shapes'] + ins['dots']:
        u = units.get(z['i'])
        if u and len(u['d']) > j and u['d'][j]:
            m = max(m, u['d'][j][0])
    return m


def _carte_ile(ins, units, x, y, w, mh, dates, mobile):
    terr = ins['terr']
    titre = TITRE_COURT.get(ins['id'], ins['title']) if not mobile else TITRE_COURT.get(ins['id'], ins['title']).replace('Saint-Pierre-et-Miquelon', 'St-Pierre-et-Miquelon')
    pad = 10
    t_size = ajuste(titre, 14 if not mobile else 13, w - 2 * pad, True)
    l0, l1 = _niveaux_ile(ins, units, 0), _niveaux_ile(ins, units, 1)

    def cls(i):
        u = units.get(i)
        return f'l{u["d"][0][0]}' if u and u['d'] and u['d'][0] else 'lx'
    out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{mh + 78:.1f}" rx="9" fill="#FFFFFF" stroke="#D8E0D6"/>',
           txt(x + pad, y + 21, titre, t_size, 'e', True)]
    pw = min(92, w - 2 * pad - 70)
    out.append(pastille(x + pad, y + 29, pw, 20, l0, 11.5))
    out.append(txt(x + pad + pw + 6, y + 43, date_courte(dates[terr][0]), 11, 's'))
    out.append(carte(ins, x + pad, y + 56, w - 2 * pad, mh, cls))
    ly = y + 56 + mh + 16
    out.append(txt(x + pad, ly, 'Demain', 11, 's'))
    if l1 >= 0:
        out.append(f'<rect x="{x + pad + 46:.1f}" y="{ly - 9:.1f}" width="10" height="10" rx="2" fill="{FOND[l1]}"/>')
        out.append(txt(x + pad + 61, ly, LIB[l1].lower(), 11, 't'))
    return ''.join(out), mh + 78


def _entete_accueil(w, pad, resume, mobile):
    out = [txt(pad, 34, 'Indice feu Outre-mer', 21 if not mobile else 19, 'e', True)]
    sous = "Niveau du jour par commune · jours en heure locale"
    out.append(txt(pad, 54, sous, 12, 's'))
    leg, lw = legende(pad, 78 if mobile else 54, 11.5)
    if mobile:
        out.append(leg)
        return ''.join(out), 92
    # légende alignée à droite sur la ligne du titre
    out.append(legende(w - pad - lw + 14, 34, 11.5)[0])
    return ''.join(out), 70


def lignes(texte, taille, dispo):
    mots, out, cur = texte.split(' '), [], ''
    for m in mots:
        essai = (cur + ' ' + m).strip()
        if cur and len(essai) * taille * 0.56 > dispo:
            out.append(cur)
            cur = m
        else:
            cur = essai
    return out + [cur] if cur else out


def _pied(x, y, gen, tz, w):
    lieu = VILLE_FUSEAU.get(tz, tz)
    texte = ('Indice personnel calculé par Météo des Forêts (méthode IFM), non produit par Météo-France, '
             'à partir des données Météo-France. Consignes officielles prioritaires. '
             f'Mis à jour le {quand(gen, tz)} (heure de {lieu}), prochain calcul vers {prochain(gen, tz)}.')
    t, out = 10.5, []
    ls = lignes(texte, t, w)
    for k, l in enumerate(ls):
        out.append(txt(x, y + k * (t + 4), l, t, 's'))
    return ''.join(out), len(ls) * (t + 4) - 4


def accueil(full, small, insets, mobile=False):
    units, dates, gen = full['units'], small['dates'], small['genere']
    pad, gap = 16, 10
    W = 420 if mobile else 900
    head, hh = _entete_accueil(W, pad, small, mobile)
    corps, y = [head], hh
    inner = W - 2 * pad
    if mobile:
        cw = (inner - gap) / 2
        mh = 118
        for k, ins in enumerate(insets):
            cx = pad + (k % 2) * (cw + gap)
            if k % 2 == 0 and k:
                y += mh + 78 + gap
            c, _ = _carte_ile(ins, units, cx, y, cw, mh, dates, True)
            corps.append(c)
        y += mh + 78 + gap
    else:
        base_h, mini_w = 150, 168
        larg = lambda ins, h: max(mini_w, ins['w'] * h / ins['h'] + 20)
        rangee = []
        def pose(rangee, y, justifie):
            tot = sum(larg(i, base_h) for i in rangee) + gap * (len(rangee) - 1)
            f = (inner - gap * (len(rangee) - 1)) / (tot - gap * (len(rangee) - 1)) if justifie else 1
            h = base_h * f
            x = pad
            for ins in rangee:
                cw = larg(ins, base_h) * f
                c, ch = _carte_ile(ins, units, x, y, cw, h, dates, False)
                corps.append(c)
                x += cw + gap
            return y + h + 78 + gap
        for ins in insets:
            rangee.append(ins)
            tot = sum(larg(i, base_h) for i in rangee) + gap * (len(rangee) - 1)
            if tot >= inner * 0.92:
                if tot > inner * 1.12 and len(rangee) > 1:
                    der = rangee.pop()
                    y = pose(rangee, y, True)
                    rangee = [der]
                else:
                    y = pose(rangee, y, True)
                    rangee = []
        if rangee:
            tot = sum(larg(i, base_h) for i in rangee) + gap * (len(rangee) - 1)
            y = pose(rangee, y, inner / tot < 1.35)
    p, ph = _pied(pad, y + 8, gen, 'Europe/Paris', inner)
    corps.append(p)
    H = y + 8 + ph + 12
    return svg(W, H, "Indice feu Outre-mer de Météo des Forêts : carte de chaque territoire, niveau du jour par commune", ''.join(corps)), W, H


# ------------------------------------------------------------------ commune

def _source(r):
    m = 'AROME Outre-mer' if r[13].startswith('AROME') else 'ARPEGE'
    return f'prévision Météo-France {m}' + (' et pluie mesurée' if r[14] == 'pluie mesurée' else '')


def _jours(x, y, w, u, dates, terr):
    out, cw = [], w / 3
    pw = min(104, cw - 12)
    for k, lib in enumerate(("Aujourd'hui", 'Demain', 'Après-demain')):
        r = u['d'][k] if len(u['d']) > k else None
        cx = x + k * cw
        iso = r[17] if r else dates[terr][k]
        out.append(txt(cx, y, lib, 11.5, 'e', True))
        out.append(txt(cx, y + 15, date_courte(iso), 11, 's'))
        out.append(pastille(cx, y + 22, pw, 24, r[0] if r else None, 12.5))
        out.append(txt(cx, y + 64, 'IFM ' + (nb(r[1]) if r else 'n.d.'), 12, 't'))
    return ''.join(out), 70


def _conditions(x, y, w, u, stations, cols):
    r = u['d'][0]
    out = [txt(x, y, "Conditions prévues aujourd'hui à midi (heure locale)", 11.5, 'e', True)]
    if not r:
        out.append(txt(x, y + 20, 'Prévision indisponible pour ce calcul.', 11.5, 's'))
        return ''.join(out), 30
    items = [('Température', f'{nb(r[9], 0)} °C'), ("Humidité de l'air", f'{nb(r[10], 0)} %'),
             ('Vent moyen', f'{nb(r[11], 0)} km/h'), ('Pluie sur 24 h', f'{nb(r[12])} mm'),
             ('Sécheresse du sol (DC)', nb(r[6], 0)), ('Inflammabilité (FFMC)', nb(r[4], 0))]
    cw = w / cols
    rows = (len(items) + cols - 1) // cols
    for k, (lib, val) in enumerate(items):
        cx, cy = x + (k % cols) * cw, y + 20 + (k // cols) * 19
        out.append(txt(cx, cy, lib, 11.5, 's'))
        out.append(txt(cx + cw - 12, cy, val, 12, 't', True, 'end'))
    yy = y + 20 + rows * 19
    st = stations.get(u['s'])
    l1 = (f'Sécheresse suivie à la station {st["n"]} ({nb(u["sd"])} km)' if st else 'Station de référence indisponible')
    if r[2] == 's' and stations.get(r[3]):
        l1 += ', niveau donné par la station de la commune'
    l2 = 'Météo : ' + _source(r)
    t, n = 11, 0
    for l in lignes(l1, t, w) + lignes(l2, t, w):
        out.append(txt(x, yy + 2 + n * (t + 4), l, t, 's'))
        n += 1
    return ''.join(out), yy - y + n * (t + 4) + 4


def commune(insee, u, ins, full, small, mobile=False):
    stations, dates, gen = full['stations'], small['dates'], small['genere']
    terr = u['t']
    tz = TZ_COMMUNE.get(insee, TERRITOIRES[terr]['tz'])
    lieu = f"{terr} · {SOUS_LIEU[ins['id']]}" if ins['id'] in SOUS_LIEU else terr
    lvl = u['d'][0][0] if u['d'] and u['d'][0] else None
    cls = lambda i: (f'l{lvl}' if lvl is not None else 'lx') if i == insee else 'g'
    pad = 16
    titre = f"Indice feu Outre-mer à {u['n']} ({terr}) : aujourd'hui, demain et après-demain, calcul Météo des Forêts"
    if mobile:
        W = 400
        inner = W - 2 * pad
        c = [txt(pad, 36, u['n'], ajuste(u['n'], 21, inner, True), 'e', True),
             txt(pad, 56, lieu, 12, 's'),
             carte(ins, pad, 68, inner, 170, cls, insee)]
        j, jh = _jours(pad, 262, inner, u, dates, terr)
        c.append(j)
        k, kh = _conditions(pad, 262 + jh + 18, inner, u, stations, 1)
        c.append(k)
        y = 262 + jh + 18 + kh + 8
    else:
        W = 760
        mw = 300
        c = [carte(ins, pad, pad, mw, 260, cls, insee)]
        x = pad + mw + 20
        inner = W - x - pad
        c.append(txt(x, 38, u['n'], ajuste(u['n'], 22, inner, True), 'e', True))
        c.append(txt(x, 58, lieu, 12.5, 's'))
        j, jh = _jours(x, 86, inner, u, dates, terr)
        c.append(j)
        k, kh = _conditions(x, 86 + jh + 18, inner, u, stations, 2)
        c.append(k)
        y = max(pad + 260 + 14, 86 + jh + 18 + kh + 4)
    p, ph = _pied(pad, y + 6, gen, tz, W - 2 * pad)
    c.append(p)
    H = y + 6 + ph + 12
    return svg(W, H, titre, ''.join(c)), W, H


# ------------------------------------------------------------------ écriture

def code_html(chemin_large, chemin_mobile, w, h, wm, hm, alt, bascule):
    return (f'<picture><source media="(max-width: {bascule}px)" srcset="{chemin_mobile}" width="{wm}" height="{hm:.0f}">'
            f'<img src="{chemin_large}" width="{w}" height="{h:.0f}" alt="{escape(alt, {chr(34): "&quot;"})}" '
            f'loading="lazy" decoding="async" style="width:100%;height:auto"></picture>')


def ecrire(full, small, out_dir, geometrie=GEOMETRIE):
    insets = charge_geometrie(geometrie)
    wd = os.path.join(out_dir, 'widgets')
    os.makedirs(os.path.join(wd, 'commune'), exist_ok=True)
    tailles = {}
    for mobile, nom in ((False, 'accueil.svg'), (True, 'accueil-mobile.svg')):
        s, w, h = accueil(full, small, insets, mobile)
        tailles[nom] = (w, h)
        with open(os.path.join(wd, nom), 'w', encoding='utf-8') as f:
            f.write(s)
    ile = {}
    for ins in insets:
        for z in ins['shapes']:
            ile.setdefault(z['i'], ins)
    for ins in insets:
        for z in ins['dots']:
            ile.setdefault(z['i'], ins)
    rows = []
    for insee, u in sorted(full['units'].items()):
        if insee not in ile:
            continue
        dims = []
        for mobile, suffixe in ((False, ''), (True, '-mobile')):
            s, w, h = commune(insee, u, ile[insee], full, small, mobile)
            dims.append((w, h))
            with open(os.path.join(wd, 'commune', f'{insee}{suffixe}.svg'), 'w', encoding='utf-8') as f:
                f.write(s)
        (w, h), (wm, hm) = dims
        alt = f"Indice feu Outre-mer à {u['n']} ({u['t']}) : niveaux d'aujourd'hui, demain et après-demain"
        rows.append((insee, u['n'], u['t'],
                     code_html(f'{DOSSIER_SITE}/commune/{insee}.svg', f'{DOSSIER_SITE}/commune/{insee}-mobile.svg',
                               w, h, wm, hm, alt, 640)))
    with open(os.path.join(wd, 'communes.csv'), 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f, delimiter=';')
        wr.writerow(('code_insee', 'commune', 'territoire', 'code_html'))
        wr.writerows(rows)
    (w, h), (wm, hm) = tailles['accueil.svg'], tailles['accueil-mobile.svg']
    with open(os.path.join(wd, 'accueil.html'), 'w', encoding='utf-8') as f:
        f.write(code_html(f'{DOSSIER_SITE}/accueil.svg', f'{DOSSIER_SITE}/accueil-mobile.svg', w, h, wm, hm,
                          "Indice feu Outre-mer de Météo des Forêts : carte de chaque territoire, niveau du jour par commune",
                          700) + '\n')
    with open(os.path.join(wd, '.htaccess'), 'w', encoding='utf-8') as f:
        f.write(HTACCESS)
