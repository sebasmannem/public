<?php

/*
 * Die Extensions senden verschiedene Abfrages an eine postgres Datenbank
 * und gibt das Ergebnis als kommaseparierte Liste zurück
 * Autor: Martina Mostert
 * Version 1.3
 */

// Funktion erlaubt im Editiermodus das Durchführen eines Updates
function wfOwlApAllowUpdate() {    
	global $egOwlApUpdateAllowed;
        
	// Update ermöglichen, da Speichernvorgang
	$egOwlApUpdateAllowed = true;
	return 1;
}

// Funktion verbietet nach dem Speichern erneutes Update z.B. beim einfachen Laden des Artikels   
function wfOwlApBlockUpdate() {    
	global $egOwlApUpdateAllowed;

	// Update nach Beendigung des Speichervorgangs wieder verbieten
	$egOwlApUpdateAllowed = false;
	return 1;
}

// Parserfunktion apGetValue
function owlApGetValue( &$parser, $table, $field, $idField, $id ) {
	
	//Tabellenname bereinigen
	$table = owlCleanParam( $table );

	//Feldname bereinigen
	$field = owlCleanParam( $field ); 

	//Feldname für id bereinigen
	$idField = owlCleanParam( $idField ); 

	//ID bereinigen
	$id = owlCleanParam( $id );

	// Abfragestring zusammenbauen
	$query = owlSimpleQuery ( $table, $field, $idField, $id );
    
	// Verbindungsdaten holen
	$owlConnectionstring = owlMakeConnectionstring();
	
	return owlSendQuery( $query, $owlConnectionstring, "wiki" );
}

// Parserfunktion apGetValues
function owlGetMValues( &$parser,$table, $idField, $idValue ) {

	// Prüfen, ob die Mindesanzahl benötigter Parameter vorhanden ist 
	if ( func_num_args() < 6)
		return wfMessage('missing-fields');

	//Tabellenname bereinigen
	$table = owlCleanParam( $table );

	//Feldname für id bereinigen
	$idField = owlCleanParam( $idField ); 

	//ID bereinigen
	$idValue = owlCleanParam( $idValue );

	// Felder aus Parameterliste auslesen
	for ( $i = 4; $i < func_num_args(); ++$i ){
		$field = func_get_arg( $i );
		$field = owlCleanParam( $field );
		$fields[] = $field;
	}

	// Anzahl Felder ermitteln
	$fieldsNum = count( $fields );

	// Abfragestring zusammenbauen
	$query = "";
	$query = "select distinct ";
	$query .= $fields[0];
		
	for ( $i = 1; $i < $fieldsNum; $i++ ){
		$query .= ", ";
		$query .= $fields[$i];
	}
		
	$query .= " from ";
	$query .= $table;
	$query .= " where ";
	$query .= $idField;
	$query .= " = '";
	$query .= $idValue;
	$query .= "';";

	// Verbindungsdaten holen
	$owlConnectionstring = owlMakeConnectionstring();

	return owlSendQuery( $query, $owlConnectionstring, "wiki" );
} 

// Parser-Funktion apGetLine
function owlGetTable(&$parser, $table) {

	if (func_num_args() < 3)
		return wfMessage('missing-fields');

	//Tabellenname bereinigen
	$table = owlCleanId($table);

	$query = "select ";

	// Felder gemäss Parameterliste anfügen
	$param = func_get_arg(2);
	$param = owlCleanId($param);
	$query .= $param;

	for ($i = 3; $i < func_num_args(); ++$i){
		$query .= ", ";
		$param = func_get_arg($i);
		$param = owlCleanId($param);
		$query .= $param;
	}
	
	$query .= " from ";
	$query .= $table;
	$query .= ";";
	
	// Verbindungsdaten holen
	$owlConnectionstring = owlMakeConnectionstring();
	
	return owlSendQuery($query, $owlConnectionstring, "html");
}

// Parser-Funktion apGetLineWhere
function owlGetLine( &$parser, $table, $field, $value ) {

	if ( func_num_args() < 5 )
		return wfMessage('missing-fields');
	
	//Tabellenname bereinigen
	$table = owlCleanId( $table );
	
	// Vergleichsfeld und -wert erxtrahieren und bereinigen
	$field = owlCleanId( $field );
	$value = owlCleanParam( $value );

	$query = "select ";

	// Felder gemäss Parameterliste anfügen		
	$param = func_get_arg( 4 );
	$param = owlCleanId( $param );
	$query .= $param;

	for ( $i = 5; $i < func_num_args(); ++$i ){
		$query .= ", ";
		$param = func_get_arg( $i );
		$param = owlCleanId( $param );
		$query .= $param;
	}
	
	$query .= " from ";
	$query .= $table;
	$query .= " where ";
	$query .= $field;
	$query .= " = '";
	$query .= $value;
	$query .= "';";
	
	// Verbindungsdaten holen
	$owlConnectionstring = owlMakeConnectionstring();
	
	return owlSendQuery( $query, $owlConnectionstring, "html" );
}

// Paserfunktion apCreateEntry
function owlCreateEntry( &$parser, $table, $idField, $idValue ){

	global $egOwlApUpdateAllowed;
	$query = "";
	$fields = "";
	$values = "";

	// Überprüfen, ob Update gestattet ist
	if ( $egOwlApUpdateAllowed == true ){
		
		// Prüfen, ob die Mindesanzahl benötigter Parameter vorhanden ist 
		if ( func_num_args() < 4 ){
			return;
		}
		
		// Prüfen, ob zu jedem angegenbenen Feld auch ein Wert übergeben wurde
		if ( ( func_num_args() % 2 ) != 0 )	{
			return;
		}

		//Felder bereinigen und Vorhandensein prüfen
		if( owlIsGiven( $table ) )
			$table = owlCleanId( $table );
		else	
			return;
				
		if( owlIsGiven( $idField ) )
			$idField = owlCleanId( $idField );
		else
			return;
			
		if( owlIsGiven( $idValue ) )
			$idValue = owlCleanParam( $idValue );
		else
			return;
		
		if( strlen( $table ) == 0 || strlen( $idField ) == 0 || strlen( $idValue ) == 0 )
			return;
		
		// Felder und Werte aus Parameterliste auslesen
		for ( $i = 4; $i < func_num_args(); ++$i ){
			$field = func_get_arg( $i );
			
			++$i;
			$value = func_get_arg( $i );
			
			$field = owlCleanId( $field );
			$value = owlCleanParam( $value );
				
			// Prüfen, ob Wert und Feldname gesetzt wurde, andernfalls beides verwerfen
			if( owlIsGiven( $field ) && owlIsGiven( $value ) ){
				$fields[] = $field;
				$values[] = $value;
			}
		}

		// Anzahl Felder und Werte ermitteln
		$fieldsNum = count( $fields );
		$valuesNum = count( $values );

		// ... und überprüfen, ob noch welche übrig sind
		if( ( $fieldsNum != $valuesNum ) || $fieldsNum == 0 )
			return;
		
		// Prüfen, ob Index schon besteht
		$query = owlSimpleQuery ( $table, $idField, $idField, $idValue );
		$owlConnectionstring = owlMakeConnectionstring();
		$result = owlSendQuery( $query, $owlConnectionstring, "wiki" );
		
		// Verbindungsdaten holen für update/insert
		$owlConnectionstring = owlMakeWguserConnectionstring();
		
		if( $result == $idValue ){
			$query = owlUpdateQuery( $table, $idField, $idValue, $fields, $values );
			return owlSendUpdate( $query, $owlConnectionstring );
		}
			
		// Abfragestring zusammenbauen
		$query = "";
		$query = "insert into ";
		$query .= $table;
		$query .= " (";
		$query .= $idField;
		
		for ( $i = 0; $i < $fieldsNum; $i++ ){
			$query .= ", ";
			$query .= $fields[$i];
		}
		
		$query .= ") values ('";
		$query .= $idValue;
		
		for ( $i = 0; $i < $valuesNum; $i++ ){
			$query .= "', '";
			$query .= $values[$i];
		}
		
		$query .= "');";
		
		return owlSendUpdate( $query, $owlConnectionstring );
	}

	return $query;
}

// Paserfunktion apUpdateValue
function owlUpdateMValues( &$parser, $table, $idField, $idValue ){
	global $egOwlApUpdateAllowed;
	$query = "";

	// Überprüfen, ob Update gestattet ist
	if ( $egOwlApUpdateAllowed == true ){
		// Prüfen, ob die Mindesanzahl benötigter Parameter vorhanden ist 
		if ( func_num_args() < 6 )
			return;
		
		// Prüfen, ob zu jedem angegenbenen Feld auch ein Wert übergeben wurde
		if ( ( func_num_args() % 2 ) != 0 )
			return;
		
		//Felder bereinigen und Vorhandensein prüfen
		if( owlIsGiven( $table ) )
			$table = owlCleanId( $table );
		else	
			return;
		
		if( owlIsGiven( $idField ) )
			$idField = owlCleanId( $idField );
		else	
			return;
		
		if( owlIsGiven( $idValue ) )
			$idValue = owlCleanParam( $idValue );
		else	
			return;
			
		if( strlen( $table ) == 0 || strlen( $idField ) == 0 || strlen( $idValue ) == 0 )
			return;

		// Felder und Werte aus Parameterliste auslesen
		for ( $i = 4; $i < func_num_args(); ++$i ){
			$field = func_get_arg( $i );
			
			++$i;
			$value = func_get_arg( $i );
			
			$field = owlCleanId( $field );
			$value = owlCleanParam( $value );
				
			// Prüfen, ob Wert und Feldname gesetzt wurde, andernfalls beides verwerfen
			if(owlIsGiven( $field ) && owlIsGiven( $value ) ){
				$fields[] = $field;
				$values[] = $value;
			}
		}

		// Anzahl Felder und Werte ermitteln
		$fieldsNum = count( $fields );
		$valuesNum = count( $values );
		
		// ... und überprüfen, ob noch welche übrig sind
		if( ( $fieldsNum != $valuesNum ) || $fieldsNum == 0 )
			return;
		
		$query = owlUpdateQuery( $table, $idField, $idValue, $fields, $values );
		
		// Verbindungsdaten holen
		$owlConnectionstring = owlMakeWguserConnectionstring();
		
		return owlSendUpdate( $query, $owlConnectionstring );
	}

	return $query;
}

// Paserfunktion apModifyValue
function owlUpdatePValue( &$parser, $table, $idField, $id, $refField, $refValue, $field, $value ){
	global $egOwlApUpdateAllowed;
	$query = "";

	// Überprüfen, ob Update gestattet ist
	if ( $egOwlApUpdateAllowed == true ){

		//Felder bereinigen und Vorhandensein prüfen
		if( owlIsGiven( $table ) )
			$table = owlCleanId( $table );
		else	
			return;
			
		if( owlIsGiven( $field ) )
			$field = owlCleanId( $field ); 
		else	
			return;
		
		if( owlIsGiven( $idField ) )
			$idField = owlCleanId( $idField );
		else	
			return;
		
		if( owlIsGiven( $value ) )
			$value = owlCleanParam( $value );
		else	
			return;
		
		if( owlIsGiven( $refField ) )
			$refField = owlCleanId( $refField );
		else	
			return;
		
		if( owlIsGiven( $refValue ) )
			$refValue = owlCleanParam( $refValue );
		else	
			return;

		if( owlIsGiven( $id ) )
			$id = owlCleanParam( $id );
		else	
			return;
		
		// Abfragestring zusammenbauen
		$query = "UPDATE ";
		$query .= $table;
		$query .= " SET ";
		$query .= $field;
		$query .= " = '";
		$query .= $value;
		$query .= "' WHERE ";
		$query .= $idField;
		$query .= " = '";
		$query .= $id;
		$query .= "' and ";
		$query .= $refField;
		$query .= " = '";
		$query .= $refValue;
		$query .= "';";
		
		// Verbindungsdaten holen
		$owlConnectionstring = owlMakeWguserConnectionstring();
		
		return owlSendUpdate( $query, $owlConnectionstring );
	}

	return $query;
}

// Paserfunktion apAddValue
function owlAddValue( &$parser, $table, $idField, $idValue, $field, $value ){
	global $egOwlApUpdateAllowed;
	$query = "";
	
	// Überprüfen, ob Update gestattet ist
	if ( $egOwlApUpdateAllowed == true ){
	
		//Übergabewerte bereinigen, falls vorhanden
		if( owlIsGiven( $table ) )
			$table = owlCleanId( $table );
		else
			return;
			
		if( owlIsGiven( $field ) )
			$field = owlCleanId( $field ); 
		else
			return;
		
		if( owlIsGiven( $idField ) )
			$idField = owlCleanId( $idField );
		else
			return;
		
		if( owlIsGiven( $value ) )
			$value = owlCleanParam( $value );
		else
			return;
		
		if( owlIsGiven( $idValue ) )
			$idValue = owlCleanId( $idValue ); 
		else
			return;
		
		// Prüfen, ob alle Daten vorliegen
		if( strlen( $table ) == 0 || strlen( $field ) == 0 || strlen( $idField ) == 0 || strlen( $value ) == 0 || strlen( $idValue ) == 0 )
			return;
		
		// Abfragestring zusammenbauen
		$query = "INSERT INTO ";
		$query .= $table;
		$query .= " (";
		$query .= $idField;
		$query .= ", ";
		$query .= $field;
		$query .= ") VALUES ('";
		$query .= $idValue;
		$query .= "', '";
		$query .= $value;
		$query .= "');";
		
		// Verbindungsdaten holen
		$owlConnectionstring = owlMakeWguserConnectionstring();
		
		return owlSendUpdate( $query, $owlConnectionstring );
    }
	
    return $query;
}

// Paserfunktion apDeleteValue
function owlDeletePEntry( &$parser, $table, $idField, $id, $field, $value ){
	global $egOwlApUpdateAllowed;
	$query = "";
	
	// Überprüfen, ob Update gestattet ist
	if ( $egOwlApUpdateAllowed == true ){
	
		//Übergabewerte bereinigen, falls vorhanden
		if( owlIsGiven( $table ) )
			$table = owlCleanId( $table );
		else
			return;
			
		if( owlIsGiven( $field ) )	
			$field = owlCleanId( $field ); 
		else
			return;
		
		if( owlIsGiven( $idField ) )
			$idField = owlCleanId( $idField );
		else
			return;
		
		if( owlIsGiven( $value ) )
			$value = owlCleanParam( $value );
		else
			return;
	
		if( owlIsGiven( $id ) )
			$id = owlCleanId( $id ); 
		else
			return;
		
		// Abfragestring zusammenbauen
		$query = "DELETE FROM ";
		$query .= $table;
		$query .= " WHERE ";
		$query .= $idField;
		$query .= " = '";
		$query .= $id;
		$query .= "' AND ";
		$query .= $field;
		$query .= " = '";
		$query .= $value;
		$query .= "';";
		
		// Verbindungsdaten holen
		$owlConnectionstring = owlMakeWguserConnectionstring();
		
		return owlSendUpdate( $query, $owlConnectionstring );
    }
	
    return $query;
}

// Abschnitt allgemeiner Funktionen, die von den Parser-Funktionen verwendet werden

// Sucht die Verbindungsdaten für den Verbindungsaufbau zusammen mit den default-Werten
function owlMakeConnectionstring(){
	global $egOwlApHost;
	global $egOwlApDBName;
	global $egOwlApUser;
	global $egOwlApPassword;

	return owlConnectionstring( $egOwlApHost, $egOwlApDBName, $egOwlApUser, $egOwlApPassword );
}

// Sucht die Verbindungsdaten für den Verbindungsaufbau zusammen, mit dem aktuellen Wiki-Benutzer
function owlMakeWguserConnectionstring(){
	global $egOwlApHost;
	global $egOwlApDBName;
	global $wgUser;
	global $egOwlApPasswordGet;

	// Wiki-Benutzer muss schreibberechtigter DB-Benutzer sein
	// andernfalls wird das spätere update zurückgewiesen von der Datenbank
	$egOwlApUser = strtolower( $wgUser->getName() );

	return owlConnectionstring( $egOwlApHost, $egOwlApDBName, $egOwlApUser, $egOwlApPasswordGet );
}

// Baut die Verbindungsdaten für den Verbindungsaufbau zusammen
function owlConnectionstring( $host, $dbname, $user, $password ){

	if( strlen( $host ) != 0 ){
		$connectionstring = "host=";
		$connectionstring .= $host;
	}
	
	if( strlen( $dbname ) != 0 ){
		$connectionstring .= " dbname=";
		$connectionstring .= $dbname;
	}
	else
		die(  wfMessage( 'missing-db') );
	
	if( strlen( $user ) != 0 ){
		$connectionstring .= " user=";
		$connectionstring .= $user;
	}
	else
		die(  wfMessage( 'missing-user') );
	
	if( strlen( $password ) != 0 ){
		$connectionstring .= " password=";
		$connectionstring .= $password;
	}

	return $connectionstring;
}


// Funktion, die überflüssige und ggf. "gefährliche" Zeichen aus dem String fischt
function owlCleanId( $id ){
	$id = strtolower( $id ); // alles in Kleinbuchstaben umwandeln, da Datenbankeinträge der ID's klein sind
	$id = strip_tags( $id ); // mögliche Html- und php-Tags entfernen
	$id = stripslashes( $id ); // mögliche Escape-Sequenzen entfernen

	return $id;
}

// Funktion, die überflüssige und ggf. "gefährliche" Zeichen aus dem String fischt
function owlCleanParam( $id ){
	$id = strip_tags( $id ); // mögliche Html- und php-Tags entfernen
    $id = stripslashes( $id ); // mögliche Escape-Sequenzen entfernen

	return $id;
}

// Funktion, die überprüft, ob ein Wert gesetzt wurde
function owlIsGiven( $value ){
	if( strlen( $value ) == 0 )
		return false;
	else
		$pos = strpos( $value, "{{{" );

	if ( $pos === false )
		return true;
	else
		return false;
}

// Funktion, die ein Update mit mehreren Feldern und einem Indexfeld zusammenbaut
function owlUpdateQuery( $table, $idField, $idValue, $fields, $values ){		
	$fieldsNum = count( $fields );

	// Abfragestring zusammenbauen
	$query = "UPDATE ";
	$query .= $table;
	$query .= " SET ";
	$query .= $fields[0];
	$query .= " = '";
	$query .= $values[0];
	$query .= "' ";

	for ( $i = 1; $i < $fieldsNum; $i++ ){
		$query .= ", ";
		$query .= $fields[$i];
		$query .= " = '";
		$query .= $values[$i];
		$query .= "' ";
	}

	$query .= " WHERE ";
	$query .= $idField;
	$query .= " = '";
	$query .= $idValue;
	$query .= "';";

	return $query;
}

// Funktion, die eine einfache Abfragen zusammenbaut
function owlSimpleQuery( $table, $field, $idField, $id ){
	$query = "SELECT distinct ";
	$query .= $field;
	$query .= " FROM ";
	$query .= $table;
	$query .= " WHERE ";
	$query .= $table;
	$query .= ".";
	$query .= $idField;
	$query .= " = '";
	$query .= $id;
	$query .= "';";

	return $query;
}

// Funktion, die den Abfragetext an die Datenbank schickt und die Ergebnisse entgegennimmt
function owlSendQuery( $query, $owlConnectionstring, $how ) {
	
	global $egOwlApSearchPath;

	if( stripos( $query, "select" ) != 0 )
		return wfMessage( 'no-select' );

	// Verbindungsaufbau und Auswahl der Datenbank
	$dbconn = pg_connect( $owlConnectionstring )
		or die( wfMessage( 'connection-failure' ));
		
	// Kodierung auf UTF-8 setzen	
	pg_set_client_encoding( UNICODE );

	// Suchpfad setzen
	$search_path = "set search_path = ".$egOwlApSearchPath;
	pg_query( $search_path );

	$output = "";

	// Abfrage durchführen
	$result = pg_query( $query ) or die(  wfMessage( 'query-aborted' ). pg_last_error() );

	$first_row = true;

	// Abfrageergebnis auslesen und aufbereiten abhängig von der gewünschten Rückgabeart
	switch( $how ){
		case "wiki":
			while ( $line = pg_fetch_array( $result, null, PGSQL_ASSOC ) ){
		
				if ( !first_row )
					$output .= "\n";
		
				$first_field = true;

				foreach ( $line as $col_value )	{			
					# Komma darf nur gesetzt werden, wenn es nicht das erste Feld der Zeile ist
					# Verhindert, dass ein Komma am Ende der Zeile steht
					if ( !$first_field )
						$output .= ", ";
			
					$output .= "$col_value";
			
					$first_field = false;
				}
		
					$first_row = false;
			}
			break;
		case "single":
			while ( $line = pg_fetch_array( $result, null, PGSQL_ASSOC ) ){
				foreach ( $line as $col_value )
					$output_line[] = $col_value;

				$output[] = $output_line;				
			}
			break;
		case "html":
			while ( $line = pg_fetch_array( $result, null, PGSQL_ASSOC ) ){
				$output .= "<tr>";
				foreach ( $line as $col_value ){
					$output .= "<td>";
					$output .= "$col_value";
					$output .= "</td>";
				}
				$output .= "</tr>";
			}
			break;
		default:
			$output = wfMessage( 'format-missing' );
	}

	// Aufraeumen
	pg_free_result( $result );
	pg_close( $dbconn );

	// entsprechend Wert in $how die Rückgabe durchführen	
	if( $how == "html" ){
	   return array( $output, 'noparse' => true, 'isHTML' => true );	
	}
	
	return $output;
}

// Funktion, die die eigentliche Insert-Anweisung an die Datenbank schickt   
function owlSendUpdate( $string, $owlConnectionstring ) {

	global $egOwlApUpdateAllowed;

	// Überprüfen, ob insert gestattet ist
	if ( $egOwlApUpdateAllowed == true ){

		// Verbindungsaufbau und Auswahl der Datenbank
		$dbconn = pg_connect( $owlConnectionstring )
			or die( wfMessage( 'connection-failure' ));
		
		// Kodierung auf UTF-8 setzen	
		pg_set_client_encoding( UNICODE );

		$output = "";

		// Suchpfad setzen
		$search_path = "set search_path = public, management_s";
		pg_query( $search_path );

		// Update durchführen
		$update = $string;
		$result = pg_query( $update ) or die( wfMessage( 'query-aborted' ). pg_last_error() );
		$output = $result;
		
		// Rückgabe löschen sofern es sich nur um die Transaktionsid handelt
		if ( $output != "false" )
			$output = "";

		// Aufraeumen
		pg_free_result( $result );
		pg_close( $dbconn );

	   //Rückgabe als Wiki-Text
	   return $output;
	}
	else
	{
		return wfMessage( 'error' );
	}
}
?>
