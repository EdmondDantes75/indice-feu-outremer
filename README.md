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
| `docs/data/resume.json` | Fichier léger (≈ 20 Ko) lu par le plugin WordPress |
| `docs/data/latest.json` | Résultats détaillés (composantes, météo, stations) |
| `docs/data/archives/` | Historique des résumés |
| `wordpress/indice-feu-outremer/` | Plugin WordPress sans JavaScript |

Lancer à la main : onglet **Actions** du dépôt, « Calcul de l'indice », **Run workflow** (case « Sonde » pour seulement vérifier l'accès aux fichiers Météo-France).

## Plugin WordPress

Copier le dossier `wordpress/indice-feu-outremer` dans `wp-content/plugins/`, puis activer l'extension. Les données sont récupérées en tâche de fond toutes les 30 minutes et gardées dans la base : aucune requête externe ni aucun script n'est ajouté aux pages vues par les visiteurs.

- `[indice_feu_outremer]` : tableau des 11 territoires, aujourd'hui et demain.
- `[indice_feu_outremer format="compact"]` : liste courte pour la page d'accueil (`jour="1"` pour demain).
- `[indice_feu_commune insee="98811"]` ou `[indice_feu_commune nom="Koné"]` : trois jours pour une commune.

## Sources et licences

- Météo-France, *Données climatologiques de base quotidiennes* et paquets de prévision AROME Outre-mer et ARPEGE, Licence Ouverte / Open Licence 2.0. Source : Météo-France.
- Fonds de carte : IGN Admin Express via [france-geojson](https://github.com/gregoiredavid/france-geojson) (Licence Ouverte) et Natural Earth (domaine public). Contours approchés pour la Nouvelle-Calédonie, la Polynésie, Wallis-et-Futuna, Saint-Martin, Saint-Barthélemy et Saint-Pierre-et-Miquelon.
- Van Wagner C.E. (1987), *Development and structure of the Canadian Forest Fire Weather Index System*, Service canadien des forêts, rapport technique 35.
