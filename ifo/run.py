"""Calcul de l'indice feu Outre-mer : une exécution produit les fichiers de docs/data/.

Usage : python -m ifo.run [--sonde]
"""
import argparse
import datetime as dt
import json
import logging
import math
import os
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np
from shapely.geometry import Point, shape

from . import fwi
from .config import DEPS, NIVEAUX, PENALITE_ALT_M_PAR_KM, SEUILS_ABS, TERRITOIRES, TZ_COMMUNE, DATASET_CLIMATO_QUOT
from .datagouv import dataset_resources
from .models import Arome, Arpege, arome_domain, weather_at_noon
from . import stations as stmod
from . import widgets

LOG = logging.getLogger('ifo')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'data')
GAP_MAX = 5  # jours au plus comblés par les modèles entre la dernière observation et aujourd'hui


def hav(a, b, c, d):
    t = math.pi / 180
    x = math.sin((c - a) * t / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin((d - b) * t / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def lvl_abs(f):
    return 0 if f < SEUILS_ABS[0] else 1 if f < SEUILS_ABS[1] else 2 if f < SEUILS_ABS[2] else 3


def lvl_rel(f, p):
    return 0 if f < p[1] else 1 if f < p[2] else 2 if f < p[3] else 3


def niveau(f, p):
    a, b = lvl_abs(f), lvl_rel(f, p)
    return max(a - 1, min(a + 1, b))


def std_noon_utc(day, tzname):
    """Midi heure locale standard (sans heure d'été), converti en UTC."""
    tz = ZoneInfo(tzname)
    d = dt.datetime.fromisoformat(day + 'T12:00:00').replace(tzinfo=tz)
    off = d.utcoffset() - (d.dst() or dt.timedelta(0))
    return (dt.datetime.fromisoformat(day + 'T12:00:00') - off).replace(tzinfo=dt.timezone.utc)


def local_today(tzname, now):
    return now.astimezone(ZoneInfo(tzname)).date()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--sonde', action='store_true', help='journalise les inventaires sans écrire de résultats')
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    t0 = time.time()
    now = dt.datetime.now(dt.timezone.utc)

    communes = json.load(open(os.path.join(ROOT, 'data', 'communes.json')))
    zones = {k: shape(v) for k, v in json.load(open(os.path.join(ROOT, 'data', 'zones.json'))).items()}
    clim_path = os.path.join(ROOT, 'data', 'climatologie.json')
    clim = json.load(open(clim_path)) if os.path.exists(clim_path) else {}

    # ---------------------------------------------------------- stations
    resources = dataset_resources(DATASET_CLIMATO_QUOT)
    ST = {}
    for dep in DEPS:
        S = stmod.load_department(resources, dep)
        if not S:
            continue
        last_dep = max(max(s['d']) for s in S.values() if s['d'])
        kept = 0
        for s in S.values():
            if stmod.completeness(s, last_dep) < 100:
                continue
            res = stmod.run_series(s)
            if res is None:
                continue
            s.update(res)
            c = clim.get(s['key'])
            if c and c.get('fp'):
                s['fp'], s['fp_src'] = c['fp'], f"{c.get('debut', '?')}-{c.get('fin', '?')}"
            else:
                vals = [x[1]['fwi'] for x in res['series'] if x[0] >= '2025-04-01']
                s['fp'], s['fp_src'] = stmod.percentiles(vals), 'série récente'
            ST[s['key']] = s
            kept += 1
        LOG.info('département %s : %d stations complètes sur %d', dep, kept, len(S))
    if not ST:
        LOG.error('aucune station exploitable')
        sys.exit(1)

    # ---------------------------------------------------------- points (communes + stations)
    for c in communes:
        c['tz'] = TZ_COMMUNE.get(c['insee'], TERRITOIRES[c['territoire']]['tz'])
        c['dep'] = TERRITOIRES[c['territoire']]['dep']
    tz_dep = {}
    for t in TERRITOIRES.values():
        tz_dep.setdefault(t['dep'], t['tz'])
    for s in ST.values():
        s['tz'] = tz_dep[s['dep']]
    points = [('c', c['insee'], c['lat'], c['lon'], c['tz']) for c in communes] + \
             [('s', k, s['lat'], s['lon'], s['tz']) for k, s in ST.items()]
    latlon = [(p[2], p[3]) for p in points]

    arome = {}
    by_dom = {}
    for i, p in enumerate(points):
        dom = arome_domain(p[2], p[3])
        if dom:
            by_dom.setdefault(dom, []).append(i)
    for dom in by_dom:
        arome[dom] = Arome(dom, latlon)
    dom_sets = {dom: set(ix) for dom, ix in by_dom.items()}
    arpege = Arpege(latlon)

    runs = {}
    for dom, m in arome.items():
        runs[dom] = [r for r in m.runs_candidates(now, back_days=6) if m.available(r)]
        LOG.info('AROME %s : runs disponibles %s', dom, [r.strftime('%d/%H') for r in runs[dom][:6]])
    runs['ARPEGE'] = [r for r in arpege.runs_candidates(now, back_days=6) if arpege.available(r)]
    LOG.info('ARPEGE : runs disponibles %s', [r.strftime('%d/%H') for r in runs['ARPEGE'][:6]])
    if args.sonde:
        for dom, m in arome.items():
            if runs[dom]:
                m.fields(runs[dom][0], 12)
        if runs['ARPEGE']:
            arpege.fields(runs['ARPEGE'][0], 12)
        LOG.info('sonde terminée en %.0f s', time.time() - t0)
        return

    # ---------------------------------------------------------- météo de midi par point et par jour
    wx = {}  # (point_index, day) -> (T, H, W, R, modèle)
    groups = {}
    for i, p in enumerate(points):
        today = local_today(p[4], now)
        for k in range(-GAP_MAX, 3):
            day = (today + dt.timedelta(days=k)).isoformat()
            groups.setdefault((p[4], day), []).append(i)
    for (tzname, day), idx in sorted(groups.items(), key=lambda x: x[0][1]):
        noon = std_noon_utc(day, tzname)
        remaining = list(idx)
        for dom, m in arome.items():
            sel = [i for i in remaining if i in dom_sets[dom]]
            if not sel or not runs[dom]:
                continue
            res = weather_at_noon(m, runs[dom], noon, sel)
            if res is None:
                continue
            T, H, W, R, run = res
            for j, i in enumerate(sel):
                if not any(np.isnan(v[j]) for v in (T, H, W, R)):
                    wx[(i, day)] = (float(T[j]), float(H[j]), float(W[j]), float(R[j]), f'AROME {run:%d/%H}h')
            remaining = [i for i in remaining if (i, day) not in wx]
        if remaining and runs['ARPEGE']:
            res = weather_at_noon(arpege, runs['ARPEGE'], noon, remaining)
            if res is not None:
                T, H, W, R, run = res
                for j, i in enumerate(remaining):
                    if not any(np.isnan(v[j]) for v in (T, H, W, R)):
                        wx[(i, day)] = (float(T[j]), float(H[j]), float(W[j]), float(R[j]), f'ARPEGE {run:%d/%H}h')
    LOG.info('météo calculée pour %d couples point-jour', len(wx))
    pidx = {(p[0], p[1]): i for i, p in enumerate(points)}

    # ---------------------------------------------------------- chaînes FWI
    def chain(state, last, start_rr_station, lat, i, tzname):
        """Prolonge un état FWI de la dernière observation jusqu'à J+2. Retourne les jours J, J+1, J+2."""
        today = local_today(tzname, now)
        d = dt.date.fromisoformat(last) + dt.timedelta(days=1)
        out = []
        held = 0
        while d <= today + dt.timedelta(days=2):
            day = d.isoformat()
            w = wx.get((i, day))
            if w is None:
                held += 1  # pas de prévision : l'état est conservé tel quel
                if d >= today:
                    out.append(None)
                d += dt.timedelta(days=1)
                continue
            T, H, W, R, src = w
            rsrc = src
            prev = start_rr_station['d'].get((d - dt.timedelta(days=1)).isoformat()) if start_rr_station else None
            if prev and prev.get('RR') is not None:
                R, rsrc = prev['RR'], 'pluie mesurée'
            state, c = fwi.step(state, T, H, W, R, d.month, lat)
            if d >= today:
                out.append({'date': day, 'T': round(T, 1), 'H': round(H), 'W': round(W), 'R': round(R, 1), 'src': src,
                            'rsrc': rsrc, **{k: round(v, 1) for k, v in c.items()}})
            d += dt.timedelta(days=1)
        return out, held

    for k, s in ST.items():
        s['res'], s['held'] = chain(s['state'], s['last'], s, s['lat'], pidx[('s', k)], s['tz'])
        for r in s['res']:
            if r:
                r['lvl'] = niveau(r['fwi'], s['fp'])

    units = {}
    for c in communes:
        best, be, bd = None, 1e9, 0.0
        for s in ST.values():
            if s['dep'] != c['dep']:
                continue
            dkm = hav(c['lat'], c['lon'], s['lat'], s['lon'])
            e = dkm + (abs(c['alt'] - s['alt']) / PENALITE_ALT_M_PAR_KM if c.get('alt') is not None else 0)
            if e < be:
                best, be, bd = s, e, dkm
        if best is None:
            continue
        cres, _ = chain(best['state'], best['last'], best, c['lat'], pidx[('c', c['insee'])], c['tz'])
        z = zones.get(c['insee'])
        inside = [s for s in ST.values() if s['dep'] == c['dep'] and z is not None and
                  (z.contains(Point(s['lon'], s['lat'])) or z.distance(Point(s['lon'], s['lat'])) < 0.014)]
        days = []
        for j in range(3):
            cand = []
            r = cres[j] if j < len(cres) else None
            if r:
                cand.append((niveau(r['fwi'], best['fp']), r['fwi'], 'c', best['key'], r))
            for s in inside:
                rs = s['res'][j] if j < len(s['res']) else None
                if rs:
                    cand.append((rs['lvl'], rs['fwi'], 's', s['key'], rs))
            if not cand:
                days.append(None)
                continue
            lv, f, by, sk, rr = max(cand, key=lambda x: (x[0], x[1]))
            days.append([lv, f, by, sk, rr['ffmc'], rr['dmc'], round(rr['dc']), rr['isi'], rr['bui'], rr['T'], rr['H'],
                         rr['W'], rr['R'], rr['src'], rr['rsrc'], r['fwi'] if r else None,
                         niveau(r['fwi'], best['fp']) if r else None, rr['date']])
        units[c['insee']] = {'n': c['nom'], 't': c['territoire'], 'p': c['pop'], 's': best['key'], 'sd': round(bd, 1),
                             'alt': c.get('alt'), 'si': [s['key'] for s in inside], 'd': days}

    # ---------------------------------------------------------- écriture
    gen = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    dates = {t: [(local_today(v['tz'], now) + dt.timedelta(days=k)).isoformat() for k in range(3)]
             for t, v in TERRITOIRES.items()}
    st_out = {k: {'n': s['nom'].title(), 'dep': s['dep'], 'alt': s['alt'], 'last': s['last'], 'dc8': round(s['state'][2]),
                  'fp': s['fp'], 'fp_src': s['fp_src'], 'd': [[r['lvl'], r['fwi']] if r else None for r in s['res']]}
              for k, s in ST.items()}
    meta = {'genere': gen, 'dates': dates, 'niveaux': NIVEAUX,
            'runs': {k: (v[0].strftime('%Y-%m-%dT%HZ') if v else None) for k, v in runs.items()},
            'sources': ['Météo-France, données climatologiques quotidiennes (Licence Ouverte 2.0)',
                        'Météo-France, modèles AROME Outre-mer et ARPEGE (Licence Ouverte 2.0)'],
            'avertissement': "Indice calculé par Météo des Forêts selon la méthode de l'Indice Forêt Météo ; ni produit ni validé par Météo-France."}
    os.makedirs(OUT, exist_ok=True)
    full = {'meta': meta, 'units': units, 'stations': st_out}
    with open(os.path.join(OUT, 'latest.json'), 'w') as f:
        json.dump(full, f, ensure_ascii=False, separators=(',', ':'))

    # fichier minimal : niveaux par commune et synthèse par territoire (source des images) : niveaux par commune et synthèse par territoire
    comm = {i: [u['n'], u['t'], [d[0] if d else None for d in u['d']], [d[1] if d else None for d in u['d']]]
            for i, u in units.items()}
    terr = {}
    for u in units.values():
        t = terr.setdefault(u['t'], {'max': [-1, -1, -1], 'n': [[0, 0, 0, 0] for _ in range(3)]})
        for j, d in enumerate(u['d']):
            if d:
                t['max'][j] = max(t['max'][j], d[0])
                t['n'][j][d[0]] += 1
    small = {'genere': gen, 'dates': dates, 'niveaux': NIVEAUX, 'territoires': terr, 'communes': comm}
    with open(os.path.join(OUT, 'resume.json'), 'w') as f:
        json.dump(small, f, ensure_ascii=False, separators=(',', ':'))
    arch = os.path.join(OUT, 'archives', now.strftime('%Y'), now.strftime('%m'))
    os.makedirs(arch, exist_ok=True)
    with open(os.path.join(arch, now.strftime('%d-%Hh') + '.json'), 'w') as f:
        json.dump(small, f, ensure_ascii=False, separators=(',', ':'))
    widgets.ecrire(full, small, os.path.dirname(OUT))
    LOG.info('terminé en %.0f s : %d communes, %d stations', time.time() - t0, len(units), len(ST))


if __name__ == '__main__':
    main()
