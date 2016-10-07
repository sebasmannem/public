<?php
/**
 * AccessPostgres extension
 *
 * @file
 * @ingroup Extensions
 *
 * This file contains the main include file for the AccessPostgres extension of
 * MediaWiki.
 *
 * Copyright (C) [2008-2011] [Martina Mostert]
 *
 * This program is free software; you can redistribute it and/or modify it under
 *  the terms of the GNU General Public License as published by the 
 * Free Software Foundation; either version 3 of the License, or (at your 
 * option) any later version.
 * 
 * This program is distributed in the hope that it will be useful, but WITHOUT 
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along with 
 * this program; if not, see <http://www.gnu.org/licenses/>.
 * 
 * 
 *
 * Usage: Add the following line in LocalSettings.php:
 * require_once( "$IP/extensions/AccessPostgres/AccessPostgres.php" );
 * and fill in the above globals with the values needed:
 * $egOwlApHost: name of the host on which Postgres is running - if left empty, a unix socket is used (localhost)
 * $egOwlApDBName: name of the postgres database to connect to
 * $egOwlApUser: user for select queries
 * $egOwlApPassword: password for queries except select
 * $egOwlApPasswordGet;	password of $egOwlApUser
 * $egOwlApSearchPath: search path for the database
 *
 * @author Martina Mostert <>
 * @license GPL 3.0
 * @version 1.3
 */

// Check environment
if ( !defined( 'MEDIAWIKI' ) ) {
    echo( "This extension can be run only on MediaWiki.\n" );
    die( -1 );
}

// Credits
$wgExtensionCredits['parserhook'][] = array(
	'name' => 'AccessPostgres',
	'author' =>'Martina Mostert', 
	'url' => 'http://www/owl-s/wiki/index.php/Hilfe:Datenbank_Abfragen', 
	'description' => 'Collection of functions to perform select, insert or update on a PostgreSQL database.',
	'descriptionmsg' => 'accesspostgres-desc',
        'version' => '1.3',
        'license-name'   => 'GPL-3.0+'
);

// Internationalization
$wgMessagesDirs['AccessPostgres'] = __DIR__ . '/i18n';

// Global Veraiables
global $egOwlApHost;		// Servername, auf dem die Datenbank läuft
global $egOwlApDBName;		// Datenbankname
global $egOwlApUser;		// Name des Users, der mit der Datenbank verbindet
global $egOwlApPassword;	// Passwort für Änderungen
global $egOwlApPasswordGet;	// Passwort für einfaches Auslesen
global $egOwlApSearchPath;	// Suchpfad der Datenbankschemata

global $egOwlApUpdateAllowed;
$egOwlApUpdateAllowed = false;

global $egOwlMessagesLoaded;
$egOwlMessagesLoaded = false;

require_once('AccessPostgresDBConfig.php');

// parser hooks registration
$wgHooks['EditPage::attemptSave'][] = 'wfOwlApAllowUpdate' ;
$wgHooks['ArticleSaveComplete'][] = 'wfOwlApBlockUpdate' ;
$wgHooks['LanguageGetMagic'][] = 'efOwlApGetValue_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApGetMValues_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApGetTable_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApGetLine_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApCreateEntry_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApUpdateMValues_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApUpdatePValue_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApAddValue_Magic';
$wgHooks['LanguageGetMagic'][] = 'efOwlApDeletePEntry_Magic';

function efOwlApGetValue_Magic( &$magicWords, $langCode ) {
	$magicWords['apGetValue'] = array( 0, 'apGetValue' );
	return true;
}

function efOwlApGetMValues_Magic( &$magicWords, $langCode ) {
	$magicWords['apGetMValues'] = array( 0, 'apGetMValues' );
	return true;
}

function efOwlApGetTable_Magic( &$magicWords, $langCode ) {
	$magicWords['apGetTable'] = array( 0, 'apGetTable' );
	return true;
}

function efOwlApGetLine_Magic( &$magicWords, $langCode ) {
	$magicWords['apGetLine'] = array( 0, 'apGetLine' );
	return true;
}

function efOwlApCreateEntry_Magic( &$magicWords, $langCode ) {
	$magicWords['apCreateEntry'] = array( 0, 'apCreateEntry' );
	return true;
}

function efOwlApUpdateMValues_Magic( &$magicWords, $langCode ) {
	$magicWords['apUpdateMValues'] = array( 0, 'apUpdateMValues' );
	return true;
}

function efOwlApUpdatePValue_Magic( &$magicWords, $langCode ) {
	$magicWords['apUpdatePValue'] = array( 0, 'apUpdatePValue' );
	return true;
}

function efOwlApAddValue_Magic( &$magicWords, $langCode ) {
	$magicWords['apAddValue'] = array( 0, 'apAddValue' );
	return true;
}

function efOwlApDeletePEntry_Magic( &$magicWords, $langCode ) {
	$magicWords['apDeletePEntry'] = array( 0, 'apDeletePEntry' );
	return true;
}

// extension functions registration
$wgExtensionFunctions[] = "efOwlApGetValue";
$wgExtensionFunctions[] = "efOwlApGetMValues";
$wgExtensionFunctions[] = "efOwlApGetTable";
$wgExtensionFunctions[] = "efOwlApGetLine";
$wgExtensionFunctions[] = "efOwlApCreateEntry";
$wgExtensionFunctions[] = "efOwlApUpdateMValues";
$wgExtensionFunctions[] = "efOwlApUpdatePValue";
$wgExtensionFunctions[] = "efOwlApAddValue";
$wgExtensionFunctions[] = "efOwlApDeletePEntry";

function efOwlApGetValue() {
	global $wgParser;
	$wgParser->setFunctionHook( "apGetValue", "owlApGetValue" );
}

function efOwlApGetMValues() {
	global $wgParser;
	$wgParser->setFunctionHook( "apGetMValues", "owlGetMValues" );
}

function efOwlApGetTable() {
	global $wgParser;
	$wgParser->setFunctionHook( "apGetTable", "owlGetTable" );
}

function efOwlApGetLine() {
    global $wgParser;
    $wgParser->setFunctionHook( "apGetLine", "owlGetLine" );
}

function efOwlApCreateEntry() {
	global $wgParser;
	$wgParser->setFunctionHook( "apCreateEntry", "owlCreateEntry" );

}

function efOwlApUpdateMValues() {
	global $wgParser;
	$wgParser->setFunctionHook( "apUpdateMValues", "owlUpdateMValues" );
  
}

function efOwlApUpdatePValue() {
	global $wgParser;
	$wgParser->setFunctionHook( "apUpdatePValue", "owlUpdatePValue" );
}

function efOwlApAddValue() {
	global $wgParser;
	$wgParser->setFunctionHook( "apAddValue", "owlAddValue" );
}

function efOwlApDeletePEntry() {
	global $wgParser;
	$wgParser->setFunctionHook( "apDeletePEntry", "owlDeletePEntry" );
}

require_once(dirname( __FILE__ ) ."/AccessPostgres.body.php" );
?>
