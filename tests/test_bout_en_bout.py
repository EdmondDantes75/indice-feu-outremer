"""Exécution complète avec données simulées (aucun accès réseau) : vérifie que run.py produit ses fichiers."""
import datetime as dt
import json
import os
import random

import ifo.run as run
import ifo.stations as stmod
from tests.test_calcul import FakeModel


def _csv(today):
    rr = ['NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJ;RR;QRR;TX;QTX;FFM;QFFM']
    au = ['NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJ;UN;QUN']
    rnd = random.Random(1)
    d = dt.date(2025, 1, 1)
    while d < today:
        k = d.strftime('%Y%m%d')
        for sid, lat, lon in (('97213004', 14.5953, -60.9957), ('97232003', 14.5518, -60.8367)):
            rain = 0.0 if rnd.random() < 0.7 else round(rnd.random() * 15, 1)
            rr.append(f'{sid};STATION {sid[-3:]};{lat};{lon};10;{k};{rain};1;{30 + rnd.random() * 3:.1f};1;{4 + rnd.random() * 3:.1f};1')
            au.append(f'{sid};STATION {sid[-3:]};{lat};{lon};10;{k};{45 + rnd.random() * 20:.0f};1')
        d += dt.timedelta(days=1)
    return '\n'.join(rr) + '\n', '\n'.join(au) + '\n'


def test_execution_complete(tmp_path, monkeypatch):
    today = dt.datetime.now(dt.timezone.utc).date()
    rr, au = _csv(today - dt.timedelta(days=1))
    res = [{'title': 'QUOT_departement_972_periode_2025-2026_RR-T-Vent', 'url': 'rr'},
           {'title': 'QUOT_departement_972_periode_2025-2026_autres-parametres', 'url': 'au'}]
    monkeypatch.setattr(run, 'dataset_resources', lambda ds: res)
    monkeypatch.setattr(stmod, 'read_gz_text', lambda url: rr if url == 'rr' else au)

    class A(FakeModel):
        name = 'AROME-OM'

        def __init__(self, dom, pts):
            super().__init__(pts, str(tmp_path))

        def available(self, r):
            return True

    class P(A):
        def __init__(self, pts):
            super().__init__('ARP', pts)

    monkeypatch.setattr(run, 'Arome', A)
    monkeypatch.setattr(run, 'Arpege', P)
    monkeypatch.setattr(run, 'OUT', str(tmp_path / 'out'))
    run.main([])
    full = json.load(open(tmp_path / 'out' / 'latest.json'))
    small = json.load(open(tmp_path / 'out' / 'resume.json'))
    mq = {k: v for k, v in full['units'].items() if v['t'] == 'Martinique'}
    assert len(mq) == 34
    assert all(v['d'][0] is not None for v in mq.values())
    assert small['territoires']['Martinique']['max'][0] in (0, 1, 2, 3)
    assert os.path.getsize(tmp_path / 'out' / 'resume.json') < 30000
