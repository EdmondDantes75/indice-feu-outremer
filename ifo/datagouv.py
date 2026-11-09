"""Accès aux fichiers publics de Météo-France publiés sur data.gouv.fr et au stockage PNT."""
import gzip
import io
import logging
import re
import time

import requests

from .config import DATAGOUV_API, USER_AGENT

LOG = logging.getLogger(__name__)
SESSION = requests.Session()
SESSION.headers['User-Agent'] = USER_AGENT


def get(url, stream=False, timeout=120, tries=4):
    for k in range(tries):
        try:
            r = SESSION.get(url, stream=stream, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 404):
                return r
            LOG.warning('HTTP %s sur %s', r.status_code, url)
        except requests.RequestException as e:
            LOG.warning('erreur réseau %s sur %s', e, url)
        time.sleep(5 * (k + 1))
    raise RuntimeError(f'échec du téléchargement : {url}')


def exists(url):
    for k in range(3):
        try:
            r = SESSION.head(url, timeout=30, allow_redirects=True)
            return r.status_code == 200
        except requests.RequestException:
            time.sleep(3)
    return False


def dataset_resources(dataset):
    r = get(f'{DATAGOUV_API}/datasets/{dataset}/')
    r.raise_for_status()
    return r.json()['resources']


def read_gz_text(url):
    r = get(url, timeout=600)
    r.raise_for_status()
    return gzip.decompress(r.content).decode('utf-8', errors='replace')


def climato_files(resources, dep, latest_only=True):
    """Fichiers quotidiens d'un département : {(debut, fin): {'RR-T-Vent': url, 'autres-parametres': url}}."""
    pat = re.compile(rf'QUOT_departement_{dep}_periode_(\d{{4}})-(\d{{4}})_(RR-T-Vent|autres-parametres)')
    per = {}
    for res in resources:
        m = pat.search(res.get('title', ''))
        if m:
            per.setdefault((int(m.group(1)), int(m.group(2))), {})[m.group(3)] = res['url']
    per = {k: v for k, v in per.items() if len(v) == 2}
    if latest_only and per:
        k = max(per, key=lambda x: (x[1], x[0]))
        return {k: per[k]}
    return per
