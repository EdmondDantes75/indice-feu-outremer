# Indice feu Outre-mer

Calcul automatique, deux fois par jour, d'un indice de danger météorologique de feu pour les territoires ultramarins français : Guadeloupe, Martinique, Saint-Martin, Saint-Barthélemy, Guyane, La Réunion, Mayotte, Nouvelle-Calédonie, Polynésie française, Wallis-et-Futuna et Saint-Pierre-et-Miquelon.

**Cet indice est calculé par Météo des Forêts. Il n'est ni produit ni validé par Météo-France, les préfectures ou les services de secours.** Il évalue des conditions météorologiques favorables au départ et à la propagation d'un feu ; il ne signale pas les feux en cours. Les consignes officielles priment toujours : la carte Prévifeu de Météo-France Nouvelle-Calédonie, les arrêtés préfectoraux et les consignes des sapeurs-pompiers.

## Méthode

- **Indice** : Indice Forêt Météo (IFM, *Fire Weather Index* du système canadien), équations de Van Wagner (1987) telles que publiées dans le paquet de référence `cffdrs`. C'est la méthode utilisée par Météo-France pour la Météo des forêts et Prévifeu, et par le système européen EFFIS.
- **Sécheresse accumulée** : codes FFMC, DMC et DC calculés jour après jour à partir des observations quotidiennes des stations Météo-France (pluie, température maximale, humidité minimale, vent moyen), depuis le 1er janvier 2025.
- **Prévision** : conditions de midi (heure locale standard) et pluie des 24 heures précédentes, prises au point de grille de chaque commune et de chaque station : AROME Outre-mer 0,025° jusqu'à 48 h dans ses cinq domaines, ARPEGE 0,25° au-delà et hors domaine (Marquises, est des Tuamotu, Gambier, Wallis-et-Futuna, Saint-Pierre-et-Miquelon). La pluie de la veille mesurée à la station remplace la prévision quand elle est publiée.
- **Niveaux** (Faible, Modéré, Élevé, Très élevé) : rang de l'IFM du jour parmi les valeurs habituelles de la station de référence (centiles 75, 90 et 97, comme Prévifeu), sans s'écarter de plus d'une classe des seuils européens EFFIS (11,2 ; 21,3 ; 38). Chaque commune prend le niveau le plus sévère entre son point de grille et les stations situées sur son territoire.
- **Seuils locaux** : centiles 1995-2024 calculés chaque mois (`data/climatologie.json`) ; à défaut, centiles de la série récente.

## Fonctionnement

| Élément | Rôle |
|---|---|
| `.github/workflows/indice.yml` | Calcul vers 6 h 45 et 16 h 45 (heure de Paris en hiver), publication dans `docs/data/` |
| `.github/workflows/climatologie.yml` | Seuils locaux recalculés le 2 de chaque mois |
| `ifo/` | Code Python : stations, lecture GRIB2, calcul FWI, niveaux |
| `docs/` | Page de carte publiée par GitHub Pages |
| `docs/data/resume.json` | Synthèse légère (≈ 15 Ko) : niveaux par commune et par territoire |
| `docs/data/latest.json` | Résultats détaillés (composantes, météo, stations) |
| `docs/data/archives/` | Historique des résumés |
| `docs/widgets/` | Images SVG à afficher sur le site (accueil, une par commune), liste `communes.csv` |

Lancer à la main : onglet **Actions** du dépôt, « Calcul de l'indice », **Run workflow** (case « Sonde » pour seulement vérifier l'accès aux fichiers Météo-France).

## Affichage sur le site, sans plugin

Chaque calcul produit des images SVG statiques (2 à 6 Ko, aucun script) : `widgets/accueil.svg` pour les 11 territoires et `widgets/commune/<code INSEE>.svg` pour chaque commune. Sur WordPress, un bloc « HTML personnalisé » suffit :

```html
<img src="/indice-feu-outremer/accueil.svg" width="380" height="362" loading="lazy" decoding="async"
     alt="Indice feu Outre-mer de Météo des Forêts : niveau de chaque territoire aujourd'hui et demain" style="max-width:100%;height:auto">
```

```html
<img src="/indice-feu-outremer/commune/98811.svg" width="380" height="132" loading="lazy" decoding="async"
     alt="Indice feu Outre-mer à Koné : aujourd'hui, demain et après-demain" style="max-width:100%;height:auto">
```

`widgets/communes.csv` donne pour chaque commune son code INSEE et l'adresse de son image.

**Dossier à la racine du site** (adresses ci-dessus) : le workflow dépose le contenu de `docs/widgets/` dans le dossier `indice-feu-outremer` du site, en SFTP ou FTPS, si ces secrets du dépôt sont renseignés (Settings > Secrets and variables > Actions) :

| Secret | Exemple |
|---|---|
| `SITE_HOTE` | `ftp.exemple-hebergeur.net` |
| `SITE_PROTOCOLE` | `sftp` ou `ftps` |
| `SITE_UTILISATEUR` | compte FTP limité à ce dossier |
| `SITE_MOT_DE_PASSE` | mot de passe de ce compte |
| `SITE_DOSSIER` | chemin du dossier vu par ce compte, par exemple `www/indice-feu-outremer` ou `.` |

Le dossier reçoit aussi un `.htaccess` (Apache) : type `image/svg+xml`, cache de 30 minutes, exécution de scripts refusée.

**Sans dépôt sur le site** : remplacer `/indice-feu-outremer/` par `https://edmonddantes75.github.io/indice-feu-outremer/widgets/` (GitHub Pages activé sur `main` / `docs`).

## Sources et licences

- Météo-France, *Données climatologiques de base quotidiennes* et paquets de prévision AROME Outre-mer et ARPEGE, Licence Ouverte / Open Licence 2.0. Source : Météo-France.
- Fonds de carte : IGN Admin Express via [france-geojson](https://github.com/gregoiredavid/france-geojson) (Licence Ouverte) et Natural Earth (domaine public). Contours approchés pour la Nouvelle-Calédonie, la Polynésie, Wallis-et-Futuna, Saint-Martin, Saint-Barthélemy et Saint-Pierre-et-Miquelon.
- Van Wagner C.E. (1987), *Development and structure of the Canadian Forest Fire Weather Index System*, Service canadien des forêts, rapport technique 35.
