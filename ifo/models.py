"""Lecture des prévisions AROME Outre-mer et ARPEGE de Météo-France (fichiers GRIB2 publics, Licence Ouverte 2.0).

Les valeurs sont prises au point de grille le plus proche de chaque lieu. La pluie sur une fenêtre est
reconstituée par différence des cumuls depuis le début du run, en enchaînant plusieurs runs si besoin.
"""
import datetime as dt
import logging
import os
import re

import numpy as np
from eccodes import (codes_get, codes_get_double_elements, codes_grib_new_from_file, codes_release, codes_get_double_array)

from .config import AROME_DOMAINES, AROME_HORIZON, AROME_MARGE, AROME_RUNS, DATAGOUV_API, PNT_BASE
from .datagouv import exists, get

LOG = logging.getLogger(__name__)
CACHE = os.environ.get('IFO_CACHE', '/tmp/ifo-cache')
ISO = '%Y-%m-%dT%H:%M:%SZ'

T_NAMES = ('2t', 't')
H_NAMES = ('2r', 'r')
WS_NAMES = ('10si', 'si', 'ws', 'wind')
U_NAMES = ('10u', 'u')
V_NAMES = ('10v', 'v')
P_NAMES = ('tp', 'tirf', 'rprate', 'tprate', 'prate')


def arome_domain(lat, lon):
    for code, b in AROME_DOMAINES.items():
        if b['lat'][0] + AROME_MARGE <= lat <= b['lat'][1] - AROME_MARGE and \
                b['lon'][0] + AROME_MARGE <= lon <= b['lon'][1] - AROME_MARGE:
            return code
    return None


class GribPoints:
    """Extrait, dans un fichier GRIB2, les champs utiles aux points demandés."""

    def __init__(self, points):
        self.points = points  # liste de (lat, lon)

    def _indices(self, gid):
        if codes_get(gid, 'gridType') != 'regular_ll':
            raise ValueError('grille non régulière : ' + codes_get(gid, 'gridType'))
        ni, nj = codes_get(gid, 'Ni'), codes_get(gid, 'Nj')
        lat1 = codes_get(gid, 'latitudeOfFirstGridPointInDegrees')
        lon1 = codes_get(gid, 'longitudeOfFirstGridPointInDegrees')
        di = codes_get(gid, 'iDirectionIncrementInDegrees')
        dj = codes_get(gid, 'jDirectionIncrementInDegrees')
        jpos = codes_get(gid, 'jScansPositively')
        idx, ok = [], []
        for lat, lon in self.points:
            x = (lon - lon1) % 360.0
            i = int(round(x / di))
            j = int(round(((lat - lat1) if jpos else (lat1 - lat)) / dj))
            inside = 0 <= i < ni and 0 <= j < nj
            ok.append(inside)
            idx.append(j * ni + i if inside else 0)
        return idx, ok

    def read(self, path):
        """Retourne {(shortName, typeOfLevel, level, startStep, endStep): np.array des valeurs aux points}."""
        out = {}
        inv = []
        cache_idx = None
        with open(path, 'rb') as f:
            while True:
                gid = codes_grib_new_from_file(f)
                if gid is None:
                    break
                try:
                    key = (codes_get(gid, 'shortName'), codes_get(gid, 'typeOfLevel'), codes_get(gid, 'level'),
                           codes_get(gid, 'startStep'), codes_get(gid, 'endStep'))
                    inv.append(key + (codes_get(gid, 'stepType'),))
                    if key[0] in T_NAMES + H_NAMES + WS_NAMES + U_NAMES + V_NAMES + P_NAMES:
                        if cache_idx is None:
                            cache_idx = self._indices(gid)
                        idx, ok = cache_idx
                        vals = np.array(codes_get_double_elements(gid, 'values', idx))
                        vals[~np.array(ok)] = np.nan
                        out[key] = vals
                finally:
                    codes_release(gid)
        return out, inv


def _pick(fields, names, level, step, tol=2):
    """Champ instantané à l'échéance step ; à défaut, échéance la plus proche à +-tol heures."""
    for dstep in sorted(range(-tol, tol + 1), key=abs):
        for n in names:
            for (sn, tl, lv, s0, s1), v in fields.items():
                if sn == n and lv == level and s1 == step + dstep and tl in ('heightAboveGround', 'surface'):
                    return v
    return None


def _pick_precip(fields, step):
    """Cumul de pluie depuis le début du run à l'échéance step (mm)."""
    if step == 0:
        return 0.0
    for dstep in (0, -1, 1, -2, 2):
        for n in P_NAMES:
            for (sn, tl, lv, s0, s1), v in fields.items():
                if sn == n and s1 == step + dstep:
                    if s0 != 0:
                        LOG.warning('cumul de pluie %s sur %s-%s h : intervalle non attendu', sn, s0, s1)
                    return v
    return None


class Model:
    """Interface commune AROME-OM / ARPEGE : runs disponibles, fichier d'une échéance, champs aux points."""
    horizon = 48

    def __init__(self, points):
        self.gp = GribPoints(points)
        self._files = {}
        self._fields = {}
        self._avail = {}
        self.inventory_logged = False

    def runs_candidates(self, now, back_days=4):
        t = now.replace(minute=0, second=0, microsecond=0)
        out = []
        for h in range(0, 24 * back_days):
            r = t - dt.timedelta(hours=h)
            if r.hour in self.run_hours and r <= now:
                out.append(r)
        return out

    def fields(self, run, step):
        key = (run, step)
        if key in self._fields:
            return self._fields[key]
        path = self.file_for(run, step)
        if path is None:
            self._fields[key] = None
            return None
        if path not in self._files:
            f, inv = self.gp.read(path)
            self._files[path] = f
            if not self.inventory_logged:
                LOG.info('%s inventaire %s : %s', self.name, os.path.basename(path), sorted(set(inv))[:80])
                self.inventory_logged = True
        self._fields[key] = self._files[path]
        return self._files[path]

    def sample(self, run, step, kind):
        f = self.fields(run, step)
        if f is None:
            return None
        if kind == 'P':
            return _pick_precip(f, step)
        if kind == 'T':
            v = _pick(f, T_NAMES, 2, step)
            return None if v is None else np.where(v > 150, v - 273.15, v)
        if kind == 'H':
            v = _pick(f, H_NAMES, 2, step)
            return None if v is None else np.clip(v, 0, 100)
        if kind == 'W':
            v = _pick(f, WS_NAMES, 10, step)
            if v is None:
                u, w = _pick(f, U_NAMES, 10, step), _pick(f, V_NAMES, 10, step)
                if u is None or w is None:
                    return None
                v = np.hypot(u, w)
            return v * 3.6
        raise ValueError(kind)


class Arome(Model):
    name = 'AROME-OM'
    run_hours = AROME_RUNS
    horizon = AROME_HORIZON

    def __init__(self, domain, points):
        super().__init__(points)
        self.domain = domain

    def url(self, run, step, pkg='SP1'):
        r = run.strftime(ISO)
        return f'{PNT_BASE}/{r}/arome-om/{self.domain}/0025/{pkg}/arome-om-{self.domain}__0025__{pkg}__{step:03d}H__{r}.grib2'

    def available(self, run):
        if run not in self._avail:
            self._avail[run] = exists(self.url(run, self.horizon))
        return self._avail[run]

    def steps(self, run):
        return range(0, self.horizon + 1)

    def file_for(self, run, step):
        url = self.url(run, step)
        path = os.path.join(CACHE, 'arome', self.domain, run.strftime('%Y%m%d%H'), f'{step:03d}.grib2')
        if not os.path.exists(path):
            r = get(url, timeout=300)
            if r.status_code != 200:
                LOG.warning('%s absent (%s)', url, r.status_code)
                return None
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as fh:
                fh.write(r.content)
        return path


class Arpege(Model):
    """ARPEGE 0,25° global. Les fichiers regroupent plusieurs échéances ; on les découvre via data.gouv.fr."""
    name = 'ARPEGE'
    run_hours = (0, 6, 12, 18)
    horizon = 102

    def __init__(self, points):
        super().__init__(points)
        self._catalog = None  # {run: [(s0, s1, url)]}

    def catalog(self):
        if self._catalog is not None:
            return self._catalog
        cat = {}
        try:
            r = get(f'{DATAGOUV_API}/datasets/?q=paquets%20arpege&page_size=50')
            sets = r.json().get('data', [])
            cand = [d for d in sets if 'arpege' in d['slug'] and ('0-25' in d['slug'] or '025' in d['slug'])
                    and 'europe' not in d['slug']]
            LOG.info('ARPEGE : jeux trouvés %s', [d['slug'] for d in cand])
            for d in cand:
                rr = get(f'{DATAGOUV_API}/datasets/{d["id"]}/').json()
                for res in rr['resources']:
                    t = res.get('title', '')
                    if '__SP1__' not in t:
                        continue
                    m = re.search(r'__(\d{3})H(?:(\d{3})H)?__(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', t)
                    if not m:
                        continue
                    s0 = int(m.group(1))
                    s1 = int(m.group(2)) if m.group(2) else s0
                    run = dt.datetime.strptime(m.group(3), ISO).replace(tzinfo=dt.timezone.utc)
                    cat.setdefault(run, []).append((s0, s1, res['url']))
                if cat:
                    LOG.info('ARPEGE : exemple de ressource %s', next(iter(cat.values()))[0])
                    break
        except Exception as e:  # noqa: BLE001
            LOG.warning('catalogue ARPEGE indisponible : %s', e)
        self._catalog = cat
        return cat

    def available(self, run):
        files = self.catalog().get(run)
        return bool(files) and max(f[1] for f in files) >= 60

    def file_for(self, run, step):
        for s0, s1, url in sorted(self.catalog().get(run, [])):
            if s0 <= step <= s1:
                path = os.path.join(CACHE, 'arpege', run.strftime('%Y%m%d%H'), f'{s0:03d}-{s1:03d}.grib2')
                if not os.path.exists(path):
                    r = get(url, timeout=900)
                    if r.status_code != 200:
                        return None
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'wb') as fh:
                        fh.write(r.content)
                return path
        return None

    def fields(self, run, step):
        # un même fichier contient plusieurs échéances : on lit tout et on filtre à la demande
        path = self.file_for(run, step)
        if path is None:
            return None
        if path not in self._files:
            f, inv = self.gp.read(path)
            self._files[path] = f
            self.steps_seen = sorted({k[4] for k in f})
            if not self.inventory_logged:
                LOG.info('ARPEGE inventaire %s : %s', os.path.basename(path), sorted(set(inv))[:60])
                self.inventory_logged = True
        return self._files[path]


def hours(a, b):
    return int(round((a - b).total_seconds() / 3600))


def weather_at_noon(model, runs, noon, point_ix):
    """Température, humidité, vent à midi et pluie des 24 h précédentes pour les points point_ix.
    runs : runs disponibles du modèle, du plus récent au plus ancien.
    Retourne (T, H, W, R, run_utilisé) ou None si le modèle ne couvre pas."""
    best = None
    for r in runs:
        s = hours(noon, r)
        if 0 <= s <= model.horizon:
            best = r
            break
    if best is None:
        return None
    s = hours(noon, best)
    T, H, W = (model.sample(best, s, k) for k in 'THW')
    if T is None or H is None or W is None:
        return None
    rain = np.zeros(len(point_ix))
    end = noon
    start = noon - dt.timedelta(hours=24)
    while end > start:
        seg_run = None
        for r in runs:
            if r < end and hours(end, r) <= model.horizon:
                seg_run = r
                break
        if seg_run is None:
            return None
        seg_start = max(seg_run, start)
        a = model.sample(seg_run, hours(end, seg_run), 'P')
        b = model.sample(seg_run, hours(seg_start, seg_run), 'P')
        if a is None or b is None:
            return None
        rain = rain + (np.asarray(a)[point_ix] if np.ndim(a) else a) - (np.asarray(b)[point_ix] if np.ndim(b) else b)
        end = seg_start
    return (np.asarray(T)[point_ix], np.asarray(H)[point_ix], np.asarray(W)[point_ix], np.clip(rain, 0, None), best)
