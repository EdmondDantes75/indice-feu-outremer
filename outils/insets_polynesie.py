"""Remplace l'encart « Polynésie · ensemble des archipels » (points seuls) par trois cartes à contours réels :
Tuamotu ouest, Tuamotu est et Gambier, Australes. Les îlots d'un même atoll sont réunis en une forme pleine (lagon compris).
À l'échelle d'un archipel (1 000 à 1 500 km), un atoll ou une île des Australes
ne ferait qu'un ou deux pixels : chaque île trop petite est agrandie autour de sa position réelle
(facteur limité), pratique cartographique courante. Les communes sans contour connu restent un point.

Usage : python -m outils.insets_polynesie   (réécrit docs/data/geometry.json)
"""
import json
import math
import os

from shapely.geometry import shape, MultiPolygon, Polygon
from shapely import affinity
from shapely.ops import unary_union

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
H, MARGE = 230, 12
ENCARTS = [
    {'id': 'pfo', 'title': 'Polynésie · Tuamotu ouest',
     'insee': ['98740', '98713', '98727', '98749', '98716', '98711', '98726', '98721'],
     'taille_min': 14.0, 'facteur_max': 4.0, 'epaisseur': 2.5},
    {'id': 'pfe', 'title': 'Polynésie · Tuamotu est et Gambier',
     'insee': ['98730', '98717', '98737', '98720', '98732', '98751', '98755', '98742', '98719'],
     'taille_min': 14.0, 'facteur_max': 4.0, 'epaisseur': 3.0},
    {'id': 'pfu', 'title': 'Polynésie · Australes', 'insee': ['98743', '98744', '98753', '98739', '98741'],
     'taille_min': 24.0, 'facteur_max': 10.0},
]


def parties(geom):
    return list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]


def amas(geom, rayon=0.25):
    """Regroupe les îlots d'un même atoll (îlots à moins de 2 × `rayon` degrés les uns des autres, de proche
    en proche) et rend la forme pleine de chaque groupe : l'enveloppe convexe, c'est-à-dire l'atoll avec
    son lagon, lisible à petite échelle."""
    morceaux = parties(geom)
    zones = unary_union([m.buffer(rayon) for m in morceaux])
    out = []
    for z in (zones.geoms if hasattr(zones, 'geoms') else [zones]):
        g = [m for m in morceaux if m.intersects(z)]
        out.append(MultiPolygon(g).convex_hull if len(g) > 1 else g[0].convex_hull)
    return out


def construit(spec, zones, communes):
    pts = []
    for i in spec['insee']:
        if i in zones:
            for p in parties(shape(zones[i])):
                pts.extend(p.exterior.coords)
        else:
            pts.append((communes[i]['lon'], communes[i]['lat']))
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
    cosl = math.cos(math.radians((lat0 + lat1) / 2))
    k = (H - 2 * MARGE) / (lat1 - lat0)
    W = round((lon1 - lon0) * cosl * k + 2 * MARGE)

    def xy(lon, lat):
        return MARGE + (lon - lon0) * cosl * k, MARGE + (lat1 - lat) * k

    shapes, dots = [], []
    for i in spec['insee']:
        if i not in zones:
            x, y = xy(communes[i]['lon'], communes[i]['lat'])
            dots.append({'i': i, 'x': round(x, 1), 'y': round(y, 1)})
            continue
        d = []
        for p in amas(shape(zones[i])):
            if p.geom_type != 'Polygon':
                continue
            q = Polygon([xy(*c) for c in p.exterior.coords])
            b = q.bounds
            taille = max(b[2] - b[0], b[3] - b[1])
            f = min(max(1.0, spec['taille_min'] / max(taille, 1e-6)), spec['facteur_max'])
            if f > 1:
                q = affinity.scale(q, f, f, origin=q.centroid)
            if spec.get('epaisseur'):  # un atoll en lanière devient une petite île arrondie
                q = q.buffer(spec['epaisseur'], resolution=3).simplify(0.4)
            c = list(q.exterior.coords)
            d.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in c[:-1]) + 'Z')
        shapes.append({'i': i, 'd': ''.join(d)})
    return {'id': spec['id'], 'title': spec['title'], 'sub': '987', 'terr': 'Polynésie française',
            'w': W, 'h': H, 'shapes': shapes, 'dots': dots, 'base': ''}


def main():
    zones = json.load(open(os.path.join(RACINE, 'data', 'zones.json'), encoding='utf-8'))
    communes = {c['insee']: c for c in json.load(open(os.path.join(RACINE, 'data', 'communes.json'), encoding='utf-8'))}
    chemin = os.path.join(RACINE, 'docs', 'data', 'geometry.json')
    g = json.load(open(chemin, encoding='utf-8'))
    garde = [i for i in g['insets'] if i['id'] not in ('pfa', 'pft', 'pfo', 'pfe', 'pfu')]
    pos = next(k for k, i in enumerate(garde) if i['id'] == 'pfm') + 1
    nouveaux = [construit(s, zones, communes) for s in ENCARTS]
    g['insets'] = garde[:pos] + nouveaux + garde[pos:]
    with open(chemin, 'w', encoding='utf-8') as f:
        json.dump(g, f, ensure_ascii=False, separators=(',', ':'))
    for n in nouveaux:
        print(n['id'], n['w'], 'x', n['h'], len(n['shapes']), 'contours', len(n['dots']), 'points')


if __name__ == '__main__':
    main()
