<?php
/**
 * Plugin Name: Indice feu Outre-mer
 * Description: Affiche l'indice feu Outre-mer de Météo des Forêts (calcul automatique deux fois par jour). Aucun JavaScript, aucune requête côté visiteur : les données sont récupérées en tâche de fond et mises en cache.
 * Version: 1.0.0
 * Author: Météo des Forêts
 * License: GPL-2.0-or-later
 * Text Domain: indice-feu-outremer
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'IFO_SOURCE', 'https://edmonddantes75.github.io/indice-feu-outremer/data/resume.json' );
define( 'IFO_SOURCE_SECOURS', 'https://raw.githubusercontent.com/EdmondDantes75/indice-feu-outremer/main/docs/data/resume.json' );
define( 'IFO_CARTE', 'https://edmonddantes75.github.io/indice-feu-outremer/' );
define( 'IFO_OPTION', 'ifo_resume' );

/* ------------------------------------------------------------------ récupération en tâche de fond */

add_filter( 'cron_schedules', function ( $s ) {
	$s['ifo_30min'] = array( 'interval' => 1800, 'display' => 'Toutes les 30 minutes (indice feu Outre-mer)' );
	return $s;
} );

register_activation_hook( __FILE__, function () {
	if ( ! wp_next_scheduled( 'ifo_rafraichir' ) ) {
		wp_schedule_event( time() + 60, 'ifo_30min', 'ifo_rafraichir' );
	}
	ifo_rafraichir();
} );

register_deactivation_hook( __FILE__, function () {
	wp_clear_scheduled_hook( 'ifo_rafraichir' );
} );

add_action( 'ifo_rafraichir', 'ifo_rafraichir' );

function ifo_rafraichir() {
	foreach ( array( IFO_SOURCE, IFO_SOURCE_SECOURS ) as $url ) {
		$r = wp_remote_get( $url, array( 'timeout' => 10 ) );
		if ( is_wp_error( $r ) || 200 !== wp_remote_retrieve_response_code( $r ) ) {
			continue;
		}
		$data = json_decode( wp_remote_retrieve_body( $r ), true );
		if ( is_array( $data ) && ! empty( $data['communes'] ) ) {
			// autoload désactivé : les données ne sont chargées que sur les pages qui les affichent
			update_option( IFO_OPTION, $data, false );
			return true;
		}
	}
	return false;
}

function ifo_donnees() {
	$d = get_option( IFO_OPTION );
	return is_array( $d ) ? $d : null;
}

/* ------------------------------------------------------------------ présentation */

function ifo_css() {
	static $fait = false;
	if ( $fait ) {
		return '';
	}
	$fait = true;
	return '<style>.ifo{font-size:.95em;line-height:1.45;margin:1em 0}.ifo table{border-collapse:collapse;width:100%}'
		. '.ifo th,.ifo td{padding:.35em .5em;border-bottom:1px solid rgba(127,127,127,.25);text-align:left}'
		. '.ifo th{font-weight:600;font-size:.85em}.ifo-n{display:inline-block;min-width:6.2em;text-align:center;'
		. 'border-radius:4px;padding:.1em .45em;font-size:.85em;font-weight:700}'
		. '.ifo-0{background:#5DB346;color:#0F2A12}.ifo-1{background:#FFE066;color:#3A2E00}'
		. '.ifo-2{background:#F59F00;color:#2E1A00}.ifo-3{background:#C92A2A;color:#fff}.ifo-x{background:#ddd;color:#333}'
		. '.ifo-c{display:flex;flex-wrap:wrap;gap:.35em .9em;list-style:none;padding:0;margin:.4em 0}'
		. '.ifo-c li{display:flex;align-items:center;gap:.4em;margin:0}.ifo small{display:block;opacity:.75;font-size:.8em;margin-top:.4em}</style>';
}

function ifo_pastille( $niveaux, $n ) {
	if ( null === $n || $n < 0 ) {
		return '<span class="ifo-n ifo-x">n.d.</span>';
	}
	return '<span class="ifo-n ifo-' . intval( $n ) . '">' . esc_html( $niveaux[ intval( $n ) ] ) . '</span>';
}

function ifo_mention( $d ) {
	$genere = isset( $d['genere'] ) ? strtotime( $d['genere'] ) : 0;
	$age    = $genere ? ( time() - $genere ) / 3600 : 999;
	$quand  = $genere ? wp_date( 'j F Y à H\hi', $genere ) : '';
	$alerte = $age > 36 ? ' Données non mises à jour depuis plus de 36 heures.' : '';
	return '<small>Indice calculé par Météo des Forêts (mise à jour du ' . esc_html( $quand ) . '), méthode de l\'Indice Forêt Météo, '
		. 'à partir des données publiques de Météo-France. Ni produit ni validé par Météo-France ; les consignes officielles priment.'
		. esc_html( $alerte ) . ' <a href="' . esc_url( IFO_CARTE ) . '" rel="noopener">Voir la carte</a></small>';
}

/* [indice_feu_outremer] ou [indice_feu_outremer format="compact"] */
add_shortcode( 'indice_feu_outremer', function ( $atts ) {
	$a = shortcode_atts( array( 'format' => 'tableau', 'jour' => '0' ), $atts );
	$d = ifo_donnees();
	if ( ! $d ) {
		return '';
	}
	$niv  = $d['niveaux'];
	$jour = max( 0, min( 2, intval( $a['jour'] ) ) );
	$terr = $d['territoires'];
	ksort( $terr );
	$h = ifo_css() . '<div class="ifo">';
	if ( 'compact' === $a['format'] ) {
		$h .= '<ul class="ifo-c">';
		foreach ( $terr as $nom => $t ) {
			$h .= '<li>' . esc_html( $nom ) . ' ' . ifo_pastille( $niv, $t['max'][ $jour ] ) . '</li>';
		}
		$h .= '</ul>';
	} else {
		$h .= '<table><thead><tr><th>Territoire</th><th>Aujourd\'hui</th><th>Demain</th></tr></thead><tbody>';
		foreach ( $terr as $nom => $t ) {
			$h .= '<tr><td>' . esc_html( $nom ) . '</td><td>' . ifo_pastille( $niv, $t['max'][0] ) . '</td><td>'
				. ifo_pastille( $niv, $t['max'][1] ) . '</td></tr>';
		}
		$h .= '</tbody></table>';
	}
	return $h . ifo_mention( $d ) . '</div>';
} );

/* [indice_feu_commune insee="98811"] ou [indice_feu_commune nom="Koné"]
   Noms en double (Saint-Pierre, Sainte-Anne, Saint-Louis…) : préciser territoire="Martinique" ou utiliser le code INSEE. */
add_shortcode( 'indice_feu_commune', function ( $atts ) {
	$a = shortcode_atts( array( 'insee' => '', 'nom' => '', 'territoire' => '' ), $atts );
	$d = ifo_donnees();
	if ( ! $d ) {
		return '';
	}
	$c = null;
	if ( $a['insee'] && isset( $d['communes'][ $a['insee'] ] ) ) {
		$c = $d['communes'][ $a['insee'] ];
	} elseif ( $a['nom'] ) {
		$cle  = remove_accents( mb_strtolower( $a['nom'] ) );
		$terr = remove_accents( mb_strtolower( $a['territoire'] ) );
		foreach ( $d['communes'] as $v ) {
			if ( remove_accents( mb_strtolower( $v[0] ) ) === $cle
				&& ( '' === $terr || remove_accents( mb_strtolower( $v[1] ) ) === $terr ) ) {
				$c = $v;
				break;
			}
		}
	}
	if ( ! $c ) {
		return '';
	}
	list( $nom, $terr, $niveaux_c, $ifm ) = $c;
	$niv = $d['niveaux'];
	$h   = ifo_css() . '<div class="ifo"><table><thead><tr><th>' . esc_html( $nom ) . '</th><th>Niveau</th><th>IFM</th></tr></thead><tbody>';
	foreach ( array( 'Aujourd\'hui', 'Demain', 'Après-demain' ) as $j => $lib ) {
		$f  = isset( $ifm[ $j ] ) && null !== $ifm[ $j ] ? number_format_i18n( $ifm[ $j ], 1 ) : 'n.d.';
		$h .= '<tr><td>' . esc_html( $lib ) . '</td><td>' . ifo_pastille( $niv, $niveaux_c[ $j ] ) . '</td><td>' . esc_html( $f ) . '</td></tr>';
	}
	return $h . '</tbody></table>' . ifo_mention( $d ) . '</div>';
} );
