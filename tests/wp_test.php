<?php
/**
 * Essai réel du plugin hors WordPress : fonctions WordPress minimales simulées, téléchargement réel
 * du fichier publié sur GitHub, rendu des shortcodes. Usage : php tests/wp_test.php
 */
define( 'ABSPATH', __DIR__ );
$GLOBALS['ifo_opts'] = array();
$GLOBALS['ifo_sc']   = array();
$GLOBALS['ifo_http'] = array();
function add_filter( $h, $f ) {}
function add_action( $h, $f ) {}
function register_activation_hook( $f, $c ) {}
function register_deactivation_hook( $f, $c ) {}
function wp_next_scheduled( $h ) { return false; }
function wp_schedule_event( $t, $r, $h ) {}
function wp_clear_scheduled_hook( $h ) {}
function add_shortcode( $n, $c ) { $GLOBALS['ifo_sc'][ $n ] = $c; }
function shortcode_atts( $d, $a ) { return array_merge( $d, (array) $a ); }
function update_option( $k, $v, $auto = null ) { $GLOBALS['ifo_opts'][ $k ] = $v; return true; }
function get_option( $k ) { return $GLOBALS['ifo_opts'][ $k ] ?? false; }
function esc_html( $s ) { return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ); }
function esc_url( $s ) { return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ); }
function number_format_i18n( $n, $d ) { return number_format( $n, $d, ',', ' ' ); }
function remove_accents( $s ) { return iconv( 'UTF-8', 'ASCII//TRANSLIT', $s ); }
function wp_date( $f, $t ) { return date( 'd/m/Y H:i', $t ) . ' UTC'; }
function is_wp_error( $r ) { return is_array( $r ) && isset( $r['erreur'] ); }
function wp_remote_retrieve_response_code( $r ) { return $r['code']; }
function wp_remote_retrieve_body( $r ) { return $r['body']; }
function wp_remote_get( $url, $args ) {
	$t0 = microtime( true );
	$c  = curl_init( $url );
	curl_setopt_array( $c, array( CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => $args['timeout'], CURLOPT_FOLLOWLOCATION => true,
		CURLOPT_CAINFO => '/root/.ccr/ca-bundle.crt' ) );
	$body = curl_exec( $c );
	$code = curl_getinfo( $c, CURLINFO_HTTP_CODE );
	$GLOBALS['ifo_http'][] = sprintf( '%s -> HTTP %s, %d octets, %.2f s', $url, $code ?: 'erreur', strlen( (string) $body ), microtime( true ) - $t0 );
	return false === $body ? array( 'erreur' => curl_error( $c ) ) : array( 'code' => $code, 'body' => $body );
}

require dirname( __DIR__ ) . '/wordpress/indice-feu-outremer/indice-feu-outremer.php';

$ok = ifo_rafraichir();
echo "== Téléchargements réels\n" . implode( "\n", $GLOBALS['ifo_http'] ) . "\nrécupération : " . ( $ok ? 'OK' : 'ÉCHEC' ) . "\n";
$d = get_option( IFO_OPTION );
echo 'données : généré ' . $d['genere'] . ', ' . count( $d['communes'] ) . " communes\n\n";
foreach ( array(
	'accueil compact' => array( 'indice_feu_outremer', array( 'format' => 'compact' ) ),
	'tableau'         => array( 'indice_feu_outremer', array() ),
	'commune INSEE'   => array( 'indice_feu_commune', array( 'insee' => '98811' ) ),
	'commune nom'     => array( 'indice_feu_commune', array( 'nom' => 'Saint-Pierre', 'territoire' => 'Saint-Pierre-et-Miquelon' ) ),
) as $lib => $sc ) {
	$t0   = microtime( true );
	$html = call_user_func( $GLOBALS['ifo_sc'][ $sc[0] ], $sc[1] );
	printf( "== %s : %d octets de HTML, %.1f ms, %d balise(s) script\n%s\n\n", $lib, strlen( $html ), ( microtime( true ) - $t0 ) * 1000,
		substr_count( $html, '<script' ), $html );
}
