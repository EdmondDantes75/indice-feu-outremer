"""Seuils locaux de chaque station (centiles 50, 75, 90, 97 de l'IFM quotidien) sur une longue période.

Lit tous les fichiers quotidiens Météo-France (1950 à aujourd'hui) et écrit data/climatologie.json.
Usage : python -m ifo.climatologie [--debut 1995] [--fin 2024]
"""
import argparse
import json
import logging
import os

from .config import DATASET_CLIMATO_QUOT, DEPS
from .datagouv import climato_files, dataset_resources
from . import stations as stmod

LOG = logging.getLogger('ifo.climatologie')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_JOURS = 3 * 365  # au moins trois ans de jours complets


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--debut', type=int, default=1995)
    ap.add_argument('--fin', type=int, default=2024)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    resources = dataset_resources(DATASET_CLIMATO_QUOT)
    out = {}
    for dep in DEPS:
        merged = {}
        for (deb, fin), urls in sorted(climato_files(resources, dep, latest_only=False).items()):
            if fin < args.debut:
                continue
            LOG.info('%s : lecture de la période %s-%s', dep, deb, fin)
            S = stmod.parse_files(urls['RR-T-Vent'], urls['autres-parametres'], since=f'{args.debut - 1}-12-01')
            for sid, s in S.items():
                m = merged.setdefault(sid, {k: s[k] for k in ('id', 'nom', 'lat', 'lon', 'alt')} | {'d': {}})
                m['d'].update(s['d'])
        for sid, s in merged.items():
            res = stmod.run_series(s, start=f'{args.debut - 1}-12-01')
            if res is None:
                continue
            vals = [c['fwi'] for d, c in res['series'] if f'{args.debut}-01-01' <= d <= f'{args.fin}-12-31']
            if len(vals) < MIN_JOURS:
                continue
            years = sorted({d[:4] for d, c in res['series'] if f'{args.debut}-01-01' <= d <= f'{args.fin}-12-31'})
            out[f'{dep}:{sid}'] = {'nom': s['nom'], 'fp': stmod.percentiles(vals), 'jours': len(vals),
                                   'debut': years[0], 'fin': years[-1]}
        LOG.info('%s : %d stations avec seuils longs', dep, sum(1 for k in out if k.startswith(dep + ':')))
    path = os.path.join(ROOT, 'data', 'climatologie.json')
    with open(path, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
    LOG.info('écrit %s (%d stations)', path, len(out))


if __name__ == '__main__':
    main()
