"""Images SVG statiques à intégrer par une simple balise <img> : aucun script, aucun plugin.

docs/widgets/accueil.svg          les 11 territoires, aujourd'hui et demain
docs/widgets/commune/<insee>.svg  une commune, trois jours
docs/widgets/communes.csv         correspondance code INSEE, commune, territoire, adresses de l'image
docs/widgets/.htaccess            réglages Apache du dossier déposé sur le site (cache court, pas d'exécution de script)
"""
import csv
import datetime as dt
import os
from xml.sax.saxutils import escape

FOND = ('#5DB346', '#FFE066', '#F59F00', '#C92A2A')
ENCRE = ('#0F2A12', '#3A2E00', '#2E1A00', '#FFFFFF')
LIB = ('Faible', 'Modéré', 'Élevé', 'Très élevé')
POLICE = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MOIS = ('janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.')
BASE_URL = 'https://edmonddantes75.github.io/indice-feu-outremer'
DOSSIER_SITE = '/indice-feu-outremer'  # dossier à la racine du site, rempli par le workflow

HTACCESS = '''# Dossier d'images de l'indice feu Outre-mer : fichiers statiques uniquement.
AddType image/svg+xml .svg
AddType text/csv .csv
<FilesMatch "\\.(php\\d?|phtml|phar|pl|py|cgi|sh)$">
  Require all denied
</FilesMatch>
<IfModule mod_headers.c>
  <FilesMatch "\\.svg$">
    Header set Cache-Control "public, max-age=1800"
    Header set X-Content-Type-Options "nosniff"
    Header set Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'"
  </FilesMatch>
</IfModule>
'''


def _quand(gen_iso):
    t = dt.datetime.fromisoformat(gen_iso.replace('Z', '+00:00'))
    # heure de Paris sans dépendance : UTC+1 l'hiver, UTC+2 du dernier dimanche de mars au dernier dimanche d'octobre
    def dernier_dimanche(an, mois):
        d = dt.date(an, mois + 1, 1) - dt.timedelta(days=1) if mois < 12 else dt.date(an, 12, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    ete = dernier_dimanche(t.year, 3) <= t.date() < dernier_dimanche(t.year, 10)
    p = t + dt.timedelta(hours=2 if ete else 1)
    return f'{p.day} {MOIS[p.month - 1]} {p.year}, {p.hour} h {p.minute:02d}'


def _pastille(x, y, w, lvl):
    if lvl is None or lvl < 0:
        return (f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="4" fill="#E2E6E1"/>'
                f'<text x="{x + w / 2}" y="{y + 14}" text-anchor="middle" fill="#4A554D" font-size="11.5" font-weight="700">n.d.</text>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="4" fill="{FOND[lvl]}"/>'
            f'<text x="{x + w / 2}" y="{y + 14}" text-anchor="middle" fill="{ENCRE[lvl]}" font-size="11.5" font-weight="700">{LIB[lvl]}</text>')


def _svg(w, h, titre, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'font-family="{POLICE}"><title>{escape(titre)}</title>'
            f'<rect width="{w}" height="{h}" rx="10" fill="#FFFFFF" stroke="#D8E0D6"/>{corps}</svg>')


def _pied(y, w, gen):
    return (f'<text x="14" y="{y}" font-size="9.5" fill="#58675D">Calcul Météo des Forêts (non Météo-France) · données Météo-France</text>'
            f'<text x="14" y="{y + 13}" font-size="9.5" fill="#58675D">Mis à jour le {escape(_quand(gen))} (heure de Paris)</text>')


def accueil(resume):
    terr = sorted(resume['territoires'].items())
    w, row = 380, 24
    h = 58 + row * len(terr) + 40
    c = [f'<text x="14" y="26" font-size="15" font-weight="700" fill="#0A2F19">Indice feu Outre-mer</text>',
         f'<text x="232" y="48" text-anchor="middle" font-size="10.5" font-weight="600" fill="#58675D">Aujourd\'hui</text>',
         f'<text x="320" y="48" text-anchor="middle" font-size="10.5" font-weight="600" fill="#58675D">Demain</text>']
    y = 56
    for nom, t in terr:
        c.append(f'<line x1="14" x2="{w - 14}" y1="{y + row - 1}" y2="{y + row - 1}" stroke="#EEF1EC"/>')
        c.append(f'<text x="14" y="{y + 15}" font-size="12.5" fill="#13241A">{escape(nom)}</text>')
        c.append(_pastille(190, y + 1, 84, t['max'][0]))
        c.append(_pastille(278, y + 1, 84, t['max'][1]))
        y += row
    c.append(_pied(y + 18, w, resume['genere']))
    return _svg(w, h, "Indice feu Outre-mer de Météo des Forêts : niveau le plus élevé de chaque territoire aujourd'hui et demain", ''.join(c))


def commune(insee, u, gen):
    nom, terr, niv, ifm = u
    w, h = 380, 132
    c = [f'<text x="14" y="25" font-size="15" font-weight="700" fill="#0A2F19">{escape(nom)}</text>',
         f'<text x="{w - 14}" y="25" text-anchor="end" font-size="10.5" fill="#58675D">{escape(terr)}</text>',
         '<text x="14" y="42" font-size="10.5" fill="#58675D">Indice feu Outre-mer (IFM)</text>']
    for k, lib in enumerate(("Aujourd'hui", 'Demain', 'Après-demain')):
        x = 14 + k * 120
        c.append(f'<text x="{x}" y="64" font-size="10.5" font-weight="600" fill="#58675D">{lib}</text>')
        c.append(_pastille(x, 70, 78, niv[k] if k < len(niv) else None))
        v = ifm[k] if k < len(ifm) else None
        c.append(f'<text x="{x + 84}" y="84" font-size="11" fill="#13241A">{"" if v is None else str(round(v, 1)).replace(".", ",")}</text>')
    c.append(_pied(110, w, gen))
    return _svg(w, h, f"Indice feu Outre-mer à {nom} ({terr}) : aujourd'hui, demain et après-demain, calcul Météo des Forêts", ''.join(c))


def ecrire(resume, out_dir):
    wd = os.path.join(out_dir, 'widgets')
    os.makedirs(os.path.join(wd, 'commune'), exist_ok=True)
    with open(os.path.join(wd, 'accueil.svg'), 'w', encoding='utf-8') as f:
        f.write(accueil(resume))
    rows = []
    for insee, u in sorted(resume['communes'].items()):
        with open(os.path.join(wd, 'commune', f'{insee}.svg'), 'w', encoding='utf-8') as f:
            f.write(commune(insee, u, resume['genere']))
        rows.append((insee, u[0], u[1], f'{DOSSIER_SITE}/commune/{insee}.svg', f'{BASE_URL}/widgets/commune/{insee}.svg'))
    with open(os.path.join(wd, 'communes.csv'), 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f, delimiter=';')
        wr.writerow(('code_insee', 'commune', 'territoire', 'image_sur_votre_site', 'image_github'))
        wr.writerows(rows)
    with open(os.path.join(wd, '.htaccess'), 'w', encoding='utf-8') as f:
        f.write(HTACCESS)
