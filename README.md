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
| `ifo/widgets.py` | Fabrication des images SVG déposées sur le site |

Lancer à la main : onglet **Actions** du dépôt, « Calcul de l'indice », **Run workflow** (case « Sonde » pour seulement vérifier l'accès aux fichiers Météo-France).

## Affichage sur le site, sans plugin

Un petit script (`w.js`, 2,7 Ko compressé, sans dépendance) construit le widget en HTML dans la page à partir d'un fichier de données. Le texte prend la police du thème et se réorganise selon la largeur de l'emplacement (grilles CSS auto-adaptatives) : quatre colonnes de cartes sur ordinateur, une seule sur téléphone, et le widget commune tient aussi dans une barre latérale. Les cartes sont des images sans texte.

Code à coller dans un bloc « HTML personnalisé » :

```html
<div data-ifo="accueil" style="min-height:900px"></div><script src="/indice-feu-outremer/w.js" defer></script>
```

```html
<div data-ifo="97209" style="min-height:520px"></div><script src="/indice-feu-outremer/w.js" defer></script>
```

Le code INSEE de chaque commune et son code prêt à coller sont dans `communes.csv`. La hauteur minimale réserve la place du widget avant son affichage (pas de décalage de la page).

| Fichier déposé | Rôle | Poids transféré |
|---|---|---|
| `w.js` | script du widget | 2,7 Ko |
| `accueil.json` | îles, niveaux, dates | 0,5 Ko |
| `c/<insee>.json` | trois jours, conditions, sources, tracé de la commune | 0,5 à 1 Ko |
| `iles/<id>.svg` | carte colorée de l'île (accueil) | 0,3 à 5 Ko |
| `iles/fond-<id>.svg` | carte grise de l'île (pages communes, mise en cache 7 jours) | 0,3 à 5 Ko |

Les fichiers sont fabriqués à chaque calcul et déposés dans le dossier `indice-feu-outremer` à la racine du site, en FTPS ; ils ne sont pas conservés dans ce dépôt. Secrets du dépôt (Settings > Secrets and variables > Actions) : `SITE_HOTE` (nom couvert par le certificat du serveur FTP, chez o2switch le nom du serveur, par exemple `sophus.o2switch.net`), `SITE_PROTOCOLE` (`ftps`), `SITE_UTILISATEUR`, `SITE_MOT_DE_PASSE` (compte FTP limité à ce dossier), `SITE_DOSSIER` (`.`).

Le serveur FTP d'o2switch ne transmet pas le certificat intermédiaire Let's Encrypt : le workflow le récupère à l'adresse inscrite dans le certificat et ajoute la racine YR contre-signée par ISRG Root X1 ; la chaîne complète est vérifiée avant tout envoi. Seuls les `.json` et `.svg` du sous-dossier `c` peuvent être supprimés (communes retirées de la liste). Le `.htaccess` du dossier fixe les types, la compression, le cache et interdit l'exécution de scripts serveur.

Pour refaire et déposer les fichiers sans relancer le calcul : onglet Actions, « Calcul de l'indice », Run workflow, case « Envoi seul ».

## Sources et licences

- Météo-France, *Données climatologiques de base quotidiennes* et paquets de prévision AROME Outre-mer et ARPEGE, Licence Ouverte / Open Licence 2.0. Source : Météo-France.
- Fonds de carte : IGN Admin Express via [france-geojson](https://github.com/gregoiredavid/france-geojson) (Licence Ouverte) et Natural Earth (domaine public). Contours approchés pour la Nouvelle-Calédonie, la Polynésie, Wallis-et-Futuna, Saint-Martin, Saint-Barthélemy et Saint-Pierre-et-Miquelon.
- Van Wagner C.E. (1987), *Development and structure of the Canadian Forest Fire Weather Index System*, Service canadien des forêts, rapport technique 35.
