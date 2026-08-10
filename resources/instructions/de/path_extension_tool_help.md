<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Pfad-Erweiterung - Kurzanleitung

Werkzeug zum Entfernen/Wiederherstellen der Dateierweiterung oder zum Zip-/Unzip von Fotos in den Pfaden, die in den Features einer Vektor-Ebene gespeichert sind.

Die Dateipfade werden aus einem Feld der Ebene gelesen und das Ergebnis jeder Operation wird in das Feld `NewPath` geschrieben (automatisch erstellt).

## Betriebsmodi

- `Erweiterung entfernen` - entfernt den Punkt und die Erweiterung aus dem physischen Pfad. Beispiel: `C:/fotos/foto.jpg` wird zu `C:/fotos/fotojpg`. Die Datei auf der Platte wird umbenannt.
- `Erweiterung wiederherstellen` - stellt den Punkt und die Erweiterung wieder her. Beispiel: die Datei `C:/fotos/fotojpg` auf der Platte wird wieder zu `C:/fotos/foto.jpg`.
- `Zip` - gruppiert die Features desselben Ordners und erstellt EINE ZIP-Datei pro Ordner mit den von den Features referenzierten Dateien. Entfernt die Originaldateien nach der Komprimierung.
- `Unzip` - gruppiert die Features desselben Ordners, extrahiert das ZIP des Ordners und entfernt das ZIP nach der Extraktion.

## Verwendung

1. Oeffnen Sie `Cadmus > Pfad-Erweiterung`.
2. Waehlen Sie die Eingabe-Vektor-Ebene (oder eine Vektordatei, wenn Sie moechten).
3. Optional: Aktivieren Sie `Nur ausgewaehlte Features`, um nur die aktuelle Auswahl zu verarbeiten.
4. Waehlen Sie das Feld, das die Dateipfade enthaelt. Wenn die Ebene ein Feld namens `path` hat, wird es automatisch ausgewaehlt.
5. Waehlen Sie den Betriebsmodus: Entfernen, Wiederherstellen, Zip oder Unzip.
6. Klicken Sie auf `Ausfuehren`.
7. Am Ende wird eine Erfolgsmeldung in der Nachrichtenleiste mit der Anzahl der geaenderten Features angezeigt.

## Was das Plugin tatsaechlich macht

- Liest die Ebene aus der Oberflaeche und das gewaehlte Pfad-Feld.
- Prueft, dass die Ebene eine Vektor-Ebene ist, ein Attribut ausgewaehlt wurde und ein Modus gewaehlt wurde.
- Fuehrt eine asynchrone Pipeline aus (`AsyncPipelineEngine` mit `PathExtensionStep`).
- Die Task verarbeitet die physischen Dateien auf der Platte, ohne die Ebene zu beruehren:
  - `remove` und `restore` verarbeiten Feature fuer Feature ueber `ExplorerUtils`.
  - `zip` und `unzip` gruppieren die Features nach Ordner und delegieren an `FileCompressUtils`.
- Der Step fuegt das Feld `NewPath` (Text) zur Ebene hinzu, falls es noch nicht existiert.
- Beim Abschluss schreibt der Step den neuen resultierenden Pfad in das Feld `NewPath` jedes Features (Haupt-Thread) und zeichnet die Ebene neu.
- Zeigt in der Nachrichtenleiste: `Verarbeitung abgeschlossen: N Features geaendert`.
- Speichert den zuletzt verwendeten Modus in den Werkzeugeinstellungen.

## Wichtiges Verhalten

- `NewPath` wird in der Ebene erstellt und erhaelt den neuen Pfad jedes verarbeiteten Features; uebersprungene oder fehlerhafte Features werden nicht geaendert.
- Modus `Zip`: Das ZIP wird mit dem Ordnernamen erstellt (z.B. `C:/fotos/fotos.zip`) und enthaelt nur die von den Features referenzierten Dateien - nicht alle Dateien im Ordner.
- Modus `Unzip`: Das ZIP des Ordners wird in das Verzeichnis selbst extrahiert und die ZIP-Datei anschliessend entfernt.
- Wenn ein Pfad leer oder ungueltig ist, wird das Feature als Fehler gezaehlt.
- Fehlende Datei oder verweigerte Berechtigung erzeugen einen gezaehlten Fehler, aber die Verarbeitung laeuft mit den uebrigen Features weiter.
- Die Verarbeitung ist asynchron und die Oberflaeche friert nicht ein; die Task kann waehrend der Ausfuehrung abgebrochen werden.

## Wann man es verwenden sollte

Verwenden Sie dieses Werkzeug, wenn Sie:

- Fotopfade normalisieren moechten, indem Sie die Erweiterung in Stapeln entfernen oder wiederherstellen;
- die von den Features einer Ebene referenzierten Dateien in ZIP komprimieren moechten;
- von den Features referenzierte ZIPs extrahieren moechten, um die Originaldateien wiederherzustellen.

## Hinweise

- Der Modus `Zip` entfernt die Originaldateien nach dem Erstellen des ZIP - erstellen Sie bei Bedarf ein Backup.
- Der Modus `Unzip` entfernt das ZIP nach der Extraktion.
- Pruefen Sie, ob das ausgewaehlte Feld wirklich gueltige absolute Pfade enthaelt.
- Verwenden Sie `Nur ausgewaehlte Features`, um auf einer kleinen Menge zu testen, bevor Sie die gesamte Ebene verarbeiten.
- Die Verarbeitung aendert Dateien auf der Platte; pruefen Sie den Ordner vor der Ausfuehrung.