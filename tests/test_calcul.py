"""Tests hors réseau : équations FWI, lecture GRIB2 aux points, reconstitution de la pluie, niveaux."""
import datetime as dt
import os
import tempfile

import numpy as np
from eccodes import codes_grib_new_from_samples, codes_release, codes_set, codes_set_values, codes_write

from ifo import fwi
from ifo.models import GribPoints, Model, weather_at_noon
from ifo.run import niveau, std_noon_utc


def test_reference_van_wagner_pickett():
    s, r = fwi.step(fwi.START, 17, 42, 25, 0, 4, 46)
    assert [round(r[k], 1) for k in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')] == [87.7, 8.5, 19.0, 10.9, 8.5, 10.1]
    s, r = fwi.step(s, 20, 21, 25, 2.4, 4, 46)
    assert [round(r[k], 1) for k in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')] == [86.2, 10.4, 23.6, 8.8, 10.4, 9.3]
    s, r = fwi.step(s, 8.5, 40, 17, 0, 4, 46)
    assert [round(r[k], 1) for k in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')] == [87.0, 11.8, 26.1, 6.5, 11.7, 7.6]


def _write(path, step, fields):
    """Écrit un GRIB2 0,025° sur [14,15]N x [-62,-60] avec un champ par (shortName, niveau, valeur(lat,lon))."""
    with open(path, 'wb') as f:
        for sn, typ, lev, fn, accum in fields:
            g = codes_grib_new_from_samples('regular_ll_sfc_grib2')
            for k, v in [('Ni', 81), ('Nj', 41), ('latitudeOfFirstGridPointInDegrees', 15.0),
                         ('longitudeOfFirstGridPointInDegrees', 298.0), ('latitudeOfLastGridPointInDegrees', 14.0),
                         ('longitudeOfLastGridPointInDegrees', 300.0), ('iDirectionIncrementInDegrees', 0.025),
                         ('jDirectionIncrementInDegrees', 0.025), ('jScansPositively', 0)]:
                codes_set(g, k, v)
            codes_set(g, 'shortName', sn)
            codes_set(g, 'typeOfLevel', typ)
            codes_set(g, 'level', lev)
            if accum:
                codes_set(g, 'stepType', 'accum')
                codes_set(g, 'startStep', 0)
                codes_set(g, 'endStep', step)
            else:
                codes_set(g, 'step', step)
            lats = 15.0 - 0.025 * np.arange(41)
            lons = -62.0 + 0.025 * np.arange(81)
            vals = np.array([[fn(la, lo) for lo in lons] for la in lats]).ravel()
            codes_set_values(g, vals)
            codes_write(g, f)
            codes_release(g)


class FakeModel(Model):
    name = 'TEST'
    run_hours = (0, 12)
    horizon = 48

    def __init__(self, points, folder):
        super().__init__(points)
        self.folder = folder

    def file_for(self, run, step):
        p = os.path.join(self.folder, f'{run:%d%H}_{step:03d}.grib2')
        if not os.path.exists(p):
            # cumul de pluie = 0,5 mm/h depuis le début du run, sauf 2 mm/h pour le run de 12 h
            rate = 2.0 if run.hour == 12 else 0.5
            _write(p, step, [('2t', 'heightAboveGround', 2, lambda la, lo: 300.15, False),
                             ('2r', 'heightAboveGround', 2, lambda la, lo: 40.0 + (15 - la) * 10, False),
                             ('10u', 'heightAboveGround', 10, lambda la, lo: 3.0, False),
                             ('10v', 'heightAboveGround', 10, lambda la, lo: 4.0, False),
                             ('tp', 'surface', 0, lambda la, lo: rate * step, True)])
        return p


def test_grib_points_et_pluie():
    pts = [(14.6, -61.05), (14.95, -61.95), (20.0, -61.0)]  # le dernier est hors grille
    with tempfile.TemporaryDirectory() as d:
        m = FakeModel(pts, d)
        r12 = dt.datetime(2026, 11, 9, 12, tzinfo=dt.timezone.utc)
        r00 = dt.datetime(2026, 11, 9, 0, tzinfo=dt.timezone.utc)
        noon = dt.datetime(2026, 11, 10, 16, tzinfo=dt.timezone.utc)  # midi à la Martinique
        T, H, W, R, run = weather_at_noon(m, [r12, r00], noon, [0, 1, 2])
        assert run == r12
        assert abs(T[0] - 27.0) < 0.01 and abs(W[0] - 18.0) < 0.01
        assert abs(H[0] - 44.0) < 0.3 and abs(H[1] - 40.5) < 0.3
        # fenêtre 16 h le 9 -> 16 h le 10 entièrement couverte par le run de 12 h : 24 h x 2 mm
        assert abs(R[0] - 48.0) < 0.01
        assert np.isnan(T[2])
        # midi plus tôt : fenêtre 06 h le 9 -> 06 h le 10, 6 h du run de 00 h (0,5 mm/h) + 18 h du run de 12 h
        noon2 = dt.datetime(2026, 11, 10, 6, tzinfo=dt.timezone.utc)
        T, H, W, R, run = weather_at_noon(m, [r12, r00], noon2, [0])
        assert abs(R[0] - (6 * 0.5 + 18 * 2.0)) < 0.01


def test_niveaux_et_midi():
    p = [5, 10, 20, 30]
    assert niveau(5, p) == 0 and niveau(25, p) == 2 and niveau(45, p) == 3
    assert niveau(9, [1, 2, 3, 4]) == 1  # un IFM < 11,2 ne dépasse jamais « modéré »
    assert std_noon_utc('2026-11-10', 'Pacific/Noumea') == dt.datetime(2026, 11, 10, 1, tzinfo=dt.timezone.utc)
    assert std_noon_utc('2026-07-10', 'America/Miquelon') == dt.datetime(2026, 7, 10, 15, tzinfo=dt.timezone.utc)
