"""Observations quotidiennes des stations Météo-France et état de sécheresse (codes FFMC, DMC, DC)."""
import csv
import datetime as dt
import io
import logging

from . import fwi
from .config import DEBUT_SERIE
from .datagouv import climato_files, read_gz_text

LOG = logging.getLogger(__name__)


def _num(v):
    v = v.strip()
    if v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_files(rr_url, autres_url, since=DEBUT_SERIE):
    """Retourne {num_poste: {'nom','lat','lon','alt','d': {date: {'RR','TX','FFM','UN'}}}}."""
    since_k = since.replace('-', '')
    S = {}
    text = read_gz_text(rr_url)
    rd = csv.reader(io.StringIO(text), delimiter=';')
    head = next(rd)
    ix = {k: head.index(k) for k in ('NUM_POSTE', 'NOM_USUEL', 'LAT', 'LON', 'ALTI', 'AAAAMMJJ', 'RR', 'TX', 'FFM')}
    for row in rd:
        if len(row) < len(head) - 5:
            continue
        d = row[ix['AAAAMMJJ']]
        if d < since_k:
            continue
        sid = row[ix['NUM_POSTE']].strip()
        st = S.get(sid)
        if st is None:
            st = S[sid] = {'id': sid, 'nom': row[ix['NOM_USUEL']].strip(), 'lat': float(row[ix['LAT']]),
                           'lon': float(row[ix['LON']]), 'alt': _num(row[ix['ALTI']]) or 0.0, 'd': {}}
        st['d'][f'{d[:4]}-{d[4:6]}-{d[6:8]}'] = {'RR': _num(row[ix['RR']]), 'TX': _num(row[ix['TX']]),
                                                  'FFM': _num(row[ix['FFM']]), 'UN': None}
    del text
    text = read_gz_text(autres_url)
    rd = csv.reader(io.StringIO(text), delimiter=';')
    head = next(rd)
    i_id, i_d, i_un = head.index('NUM_POSTE'), head.index('AAAAMMJJ'), head.index('UN')
    for row in rd:
        if len(row) <= i_un:
            continue
        d = row[i_d]
        if d < since_k:
            continue
        st = S.get(row[i_id].strip())
        if st is None:
            continue
        k = f'{d[:4]}-{d[4:6]}-{d[6:8]}'
        if k in st['d']:
            st['d'][k]['UN'] = _num(row[i_un])
    return S


def complete(rec):
    return rec is not None and None not in (rec['TX'], rec['UN'], rec['FFM'])


def load_department(resources, dep, since=DEBUT_SERIE):
    files = climato_files(resources, dep, latest_only=True)
    if not files:
        LOG.warning('aucun fichier quotidien pour %s', dep)
        return {}
    (deb, fin), urls = next(iter(files.items()))
    LOG.info('département %s : période %s-%s', dep, deb, fin)
    S = parse_files(urls['RR-T-Vent'], urls['autres-parametres'], since=since)
    for st in S.values():
        st['dep'] = dep
        st['key'] = f'{dep}:{st["id"]}'
    return S


def day_iter(a, b):
    d = dt.date.fromisoformat(a)
    e = dt.date.fromisoformat(b)
    while d <= e:
        yield d.isoformat()
        d += dt.timedelta(days=1)


def run_series(st, start=DEBUT_SERIE):
    """Calcule la série FWI quotidienne d'une station à partir des observations.
    Midi du jour d : TX, UN, FFM du jour d et pluie RR du jour d-1 (06 h UTC d-1 -> 06 h UTC d).
    Les jours incomplets sont sautés (les codes restent inchangés)."""
    days = sorted(st['d'])
    if not days:
        return None
    state = fwi.START
    ser = []
    skipped = 0
    for d in day_iter(max(start, days[0]), days[-1]):
        r = st['d'].get(d)
        prev = st['d'].get((dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat())
        ro = prev['RR'] if prev else None
        if complete(r) and ro is not None:
            state, c = fwi.step(state, r['TX'], r['UN'], r['FFM'] * 3.6, ro, int(d[5:7]), st['lat'])
            ser.append((d, c))
        else:
            skipped += 1
    if not ser:
        return None
    return {'state': state, 'last': ser[-1][0], 'series': ser, 'skipped': skipped}


def completeness(st, end, days=120):
    e = dt.date.fromisoformat(end)
    full = 0
    for k in range(days):
        r = st['d'].get((e - dt.timedelta(days=k)).isoformat())
        if complete(r) and r['RR'] is not None:
            full += 1
    return full


def percentiles(values, qs=(0.5, 0.75, 0.9, 0.97)):
    s = sorted(values)
    out = []
    for q in qs:
        i = (len(s) - 1) * q
        lo, hi = int(i), min(int(i) + 1, len(s) - 1)
        out.append(round(s[lo] + (s[hi] - s[lo]) * (i - lo), 2))
    return out
