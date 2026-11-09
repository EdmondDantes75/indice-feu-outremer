"""Réglages : territoires, fuseaux, domaines des modèles, sources."""

# Territoire -> code département Météo-France des fichiers climatologiques et fuseau par défaut.
TERRITOIRES = {
    'Guadeloupe': {'dep': '971', 'tz': 'America/Guadeloupe'},
    'Martinique': {'dep': '972', 'tz': 'America/Martinique'},
    'Saint-Martin': {'dep': '971', 'tz': 'America/Marigot'},
    'Saint-Barthélemy': {'dep': '971', 'tz': 'America/St_Barthelemy'},
    'Guyane': {'dep': '973', 'tz': 'America/Cayenne'},
    'La Réunion': {'dep': '974', 'tz': 'Indian/Reunion'},
    'Mayotte': {'dep': '985', 'tz': 'Indian/Mayotte'},
    'Nouvelle-Calédonie': {'dep': '988', 'tz': 'Pacific/Noumea'},
    'Polynésie française': {'dep': '987', 'tz': 'Pacific/Tahiti'},
    'Wallis-et-Futuna': {'dep': '986', 'tz': 'Pacific/Wallis'},
    'Saint-Pierre-et-Miquelon': {'dep': '975', 'tz': 'America/Miquelon'},
}
# Fuseaux particuliers à l'intérieur d'un territoire (codes INSEE).
TZ_COMMUNE = {
    '98718': 'Pacific/Marquesas', '98723': 'Pacific/Marquesas', '98731': 'Pacific/Marquesas',
    '98746': 'Pacific/Marquesas', '98756': 'Pacific/Marquesas', '98757': 'Pacific/Marquesas',
    '98719': 'Pacific/Gambier',
}
DEPS = sorted({t['dep'] for t in TERRITOIRES.values()})

# Domaines AROME Outre-mer 0,025° (emprises du descriptif technique Météo-France, juin 2024).
AROME_DOMAINES = {
    'ANTIL': {'lat': (9.7, 22.9), 'lon': (-75.3, -51.7)},
    'GUYANE': {'lat': (1.05, 8.95), 'lon': (-56.75, -46.3)},
    'INDIEN': {'lat': (-25.9, -7.25), 'lon': (32.75, 67.6)},
    'NCALED': {'lat': (-30.0, -10.0), 'lon': (156.0, 174.0)},
    'POLYN': {'lat': (-25.25, -12.6), 'lon': (-157.5, -144.5)},
}
AROME_RUNS = (0, 6, 12, 18)
AROME_HORIZON = 48
# Marge intérieure (degrés) : un point trop près du bord du domaine passe sur ARPEGE.
AROME_MARGE = 0.05

PNT_BASE = 'https://meteofrance-pnt.s3.rbx.io.cloud.ovh.net/pnt'
DATAGOUV_API = 'https://www.data.gouv.fr/api/1'
DATASET_CLIMATO_QUOT = '6569b51ae64326786e4e8e1a'  # Données climatologiques de base - quotidiennes

USER_AGENT = 'indice-feu-outremer/1.0 (+https://github.com/EdmondDantes75/indice-feu-outremer)'

# Classes FWI harmonisées EFFIS / GWIS, regroupées en 4 niveaux.
SEUILS_ABS = (11.2, 21.3, 38.0)
NIVEAUX = ['Faible', 'Modéré', 'Élevé', 'Très élevé']

# Pénalité d'altitude pour le choix de la station de référence : 100 m d'écart = 5 km.
PENALITE_ALT_M_PAR_KM = 20.0

DEBUT_SERIE = '2025-01-01'  # début des séries stations utilisées pour l'état de sécheresse
