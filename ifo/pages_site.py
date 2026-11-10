"""Pages publiées sur meteodesforets.fr, pour que le widget ne crée que des liens qui fonctionnent.

À chaque calcul : lecture du plan du site (page-sitemap.xml de Yoast, une seule requête).
- page de territoire : /incendie-departement-<territoire>/
- page de commune : /incendie-<commune>/ ou /incendie-<commune>-<département>/, retenue seulement si la page publiée cite bien le territoire
  (évite les homonymes de métropole : Saint-Denis, Saint-Pierre, Sainte-Anne…) ; vérifiée une seule fois
- page de méthode : /indice-feu-outre-mer-methode/
Le résultat est gardé dans docs/data/pages-site.json : si le site ne répond pas, on garde le dernier état connu.
"""
import json
import logging
import os
import re
import unicodedata

import requests

from .config import USER_AGENT

LOG = logging.getLogger(__name__)
SITE = 'https://www.meteodesforets.fr'
PLAN = SITE + '/page-sitemap.xml'
METHODE = '/indice-feu-outre-mer-methode/'
TERR_SLUG = {'Guadeloupe': 'guadeloupe', 'Martinique': 'martinique', 'Guyane': 'guyane', 'La Réunion': 'la-reunion',
             'Mayotte': 'mayotte', 'Saint-Martin': 'saint-martin', 'Saint-Barthélemy': 'saint-barthelemy',
             'Saint-Pierre-et-Miquelon': 'saint-pierre-et-miquelon', 'Nouvelle-Calédonie': 'nouvelle-caledonie',
             'Polynésie française': 'polynesie-francaise', 'Wallis-et-Futuna': 'wallis-et-futuna'}


def slug(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def _sans_accents(t):
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()


def charger(out_dir, units, en_ligne=True):
    chemin = os.path.join(out_dir, 'data', 'pages-site.json')
    try:
        with open(chemin, encoding='utf-8') as f:
            etat = json.load(f)
    except (OSError, ValueError):
        etat = {'chemins': [], 'communes': {}}
    if en_ligne:
        try:
            r = requests.get(PLAN, timeout=20, headers={'User-Agent': USER_AGENT})
            r.raise_for_status()
            chemins = sorted({re.sub(r'^https?://[^/]+', '', u) for u in re.findall(r'<loc>([^<]+)</loc>', r.text)})
            if chemins:
                etat['chemins'] = chemins
        except requests.RequestException as e:
            LOG.warning('plan du site illisible (%s) : liens du dernier état connu', e)
    publies = set(etat['chemins'])
    communes = etat.setdefault('communes', {})
    if en_ligne:
        for insee, u in units.items():
            if communes.get(insee):
                continue
            # forme simple, ou suffixée du département pour les homonymes (comme /incendie-la-trinite-06/)
            for c in (f'/incendie-{slug(u["n"])}-{insee[:3]}/', f'/incendie-{slug(u["n"])}/'):
                if c not in publies:
                    continue
                try:
                    page = requests.get(SITE + c, timeout=20, headers={'User-Agent': USER_AGENT}).text
                except requests.RequestException:
                    break
                if _sans_accents(u['t']) in _sans_accents(page):
                    communes[insee] = c
                    break
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'w', encoding='utf-8') as f:
        json.dump(etat, f, ensure_ascii=False, indent=0)
    terr = {t: f'/incendie-departement-{s}/' for t, s in TERR_SLUG.items() if f'/incendie-departement-{s}/' in publies}
    return {'terr': terr, 'communes': {i: c for i, c in communes.items() if c and c in publies},
            'methode': METHODE if METHODE in publies else ''}
