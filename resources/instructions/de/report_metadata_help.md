<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Metadata-Bericht - Kurzanleitung

Werkzeug zum erneuten Erzeugen von HTML-Berichten und zum Vektorisieren von Fluegen aus temporaeren JSONs, die von der Metadaten-Pipeline erzeugt wurden.

Die Liste der verfuegbaren JSONs wird automatisch aus dem temporaeren Berichtsordner geladen, sortiert vom neuesten zum aeltesten.

## Was das Werkzeug tut

- **Bericht erzeugen** - erzeugt einen HTML-Bericht aus dem ausgewaehlten JSON und oeffnet die Datei automatisch.
- **Flug vektorisieren** - erstellt eine Punkt-Ebene (`Flight_...`) aus dem JSON und erzeugt die entsprechende Spur-Ebene (Linie).
- **Aktualisieren-Schaltflaeche** - aktualisiert die Liste der verfuegbaren temporaeren JSONs.
- **Ordner oeffnen** - oeffnet den Ordner der temporaeren JSONs oder den Ordner der HTML-Berichte.

## Verwendung

1. Oeffnen Sie `Cadmus > Metadata-Bericht`.
2. Waehlen Sie eine temporaere JSON-Datei aus der Liste (vom neuesten zum aeltesten).
3. Waehlen Sie eine Aktion:
   - Klicken Sie auf `Bericht erzeugen`, um den HTML-Bericht zu erzeugen und zu oeffnen.
   - Klicken Sie auf `Flug vektorisieren`, um die Punkt- und Spur-Ebenen im Projekt zu erstellen.
4. Verwenden Sie bei Bedarf die Hilfsschaltflaechen:
   - `Liste aktualisieren` - laedt die verfuegbaren JSONs neu.
   - `JSON-Ordner oeffnen` - oeffnet den Ordner, in dem die temporaeren JSON-Dateien gespeichert sind.
   - `Berichtsordner oeffnen` - oeffnet den Ordner, in dem die erzeugten HTML-Berichte gespeichert sind.

## Was das Plugin tatsaechlich macht

- Liest die `.json`-Dateien aus dem temporaeren Berichtsordner (`REPORTS_TEMP_FOLDER` + `REPORTS_JSON_FOLDER`), sortiert nach Aenderungsdatum (neueste zuerst).
- Das Kombinationsfeld zeigt den Namen jeder JSON-Datei; die Auswahl wird in den Werkzeugeinstellungen gespeichert.
- **Bericht erzeugen**:
  - Prueft, dass ein JSON ausgewaehlt wurde und die Datei existiert.
  - Prueft, dass die Lizenz mindestens Stufe 3 hat (`RegistryManager.has_minimum_level`).
  - Verwendet `ReportGenerationService.generate_from_json()`, um das HTML zu erzeugen, und erhaelt den Pfad aus dem Payload.
  - Oeffnet das HTML automatisch mit `ExplorerUtils.open_file()`.
- **Flug vektorisieren**:
  - Verwendet `JsonToVectorTranslator.translate()`, um die Punkt-Ebene zu erstellen.
  - Der Ebenenname ist `Flight_<Titel>` (Feld `titulo` des JSON) oder `Flight_<Dateiname>` als Fallback.
  - Die Koordinatenquelle wird aus dem Feld `source` des JSON gelesen (Standard `mrk+photo`).
  - Die Felder der Ebene werden alphabetisch neu sortiert.
  - Die Punkt-Ebene wird zum Projekt hinzugefuegt.
  - Erzeugt die Spur-Ebene (Linie) aus den Punkten, sortiert nach Fotofeld (Foto/PhotoNum/id) und gruppiert nach `MrkPath` + `MrkFile`.
  - Zeigt in der Leiste: `Flug vektorisiert: N Punkte und Spur erzeugt.`

## Wichtiges Verhalten

- Das Erzeugen eines Berichts erfordert Lizenzstufe 3 oder hoeher; ohne diese zeigt das Werkzeug einen Hinweis.
- Wenn kein JSON ausgewaehlt ist oder die Datei nicht existiert, zeigt das Werkzeug einen Hinweis (`Datei auswaehlen` / `Datei nicht gefunden`).
- Die JSON-Liste kann leer sein - verwenden Sie `Liste aktualisieren`, nachdem Sie neue JSONs in der Pipeline erzeugt haben.
- Der erzeugte HTML-Bericht wird automatisch geoeffnet; wenn das Oeffnen fehlschlaegt, wird eine Warnleiste angezeigt.
- Das temporaere JSON enthaelt die Flug-Metadaten (Titel, Koordinatenquelle, Fotos und Markierungen), die sowohl vom Bericht als auch von der Vektorisierung verwendet werden.

## Wann man es verwenden sollte

Verwenden Sie dieses Werkzeug, wenn Sie:

- einen HTML-Bericht eines Flugs erneut erzeugen moechten, ohne die gesamte Pipeline erneut zu verarbeiten;
- einen bereits verarbeiteten Flug vektorisieren moechten, um die Punkt- und Spur-Ebenen neu zu erstellen;
- schnell auf die Ordner der temporaeren JSONs und HTML-Berichte zugreifen moechten.

## Hinweise

- Die Vektorisierung fuegt Ebenen zum Projekt hinzu - pruefen Sie, ob bereits Ebenen mit demselben Namen existieren.
- Das Erzeugen eines Berichts oeffnet das HTML im Browser; pruefen Sie, ob der Berichtsordner existiert.
- Die JSON-Liste wird nur manuell aktualisiert (Schaltflaeche `Liste aktualisieren`) oder beim Oeffnen des Werkzeugs.
- Lizenzierung: Das Erzeugen von Berichten erfordert Stufe 3; die Vektorisierung erfordert diese Stufe nicht.