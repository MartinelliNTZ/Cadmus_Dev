# Cadmus Einstellungen - Kurzanleitung

Dieses Werkzeug buendelt globale Einstellungen, die von Teilen des Cadmus-Plugins verwendet werden.

Im aktuellen Stand des Codes erlaubt es:

- die Standardmethode fuer Vektorberechnungen zu waehlen;
- die numerische Genauigkeit von Vektorfeldern festzulegen;
- den Feature-Grenzwert fuer asynchrone Verarbeitung festzulegen;
- den lokalen Cadmus-Einstellungsordner zu oeffnen.

## Verwendung

1. Oeffnen Sie `Cadmus > Cadmus Einstellungen`.
2. Waehlen Sie die Methode fuer Vektorberechnungen:
- `Ellipsoidal`
- `Cartesian`
- `Both`
3. Passen Sie die Genauigkeit der Vektorfelder an.
4. Passen Sie den asynchronen Grenzwert an.
5. Klicken Sie auf `Speichern`.

## Was das Plugin tatsaechlich macht

- Laedt gespeicherte Einstellungen mit `load_tool_prefs()`.
- Speichert die Konfiguration im Einstellungsbereich mit dem Schluessel `settings`.
- Zeigt nach dem Speichern eine Bestaetigungsmeldung an.
- Schliesst das Fenster kurz nach dem Anwenden der Einstellungen.
- Ermoeglicht das Oeffnen des lokalen Ordners, in dem die Einstellungsdateien gespeichert werden.

## Bedeutung jeder Option

- `Methode fuer Vektorberechnungen`: definiert den Textwert der Einstellung `calculation_method`.
- `Genauigkeit von Vektorfeldern`: speichert einen ganzzahligen Wert in `vector_field_precision`.
- `Asynchroner Grenzwert`: speichert einen ganzzahligen Wert in `async_threshold_features`.

## Methode fuer Vektorberechnungen (Ellipsoidisch vs Kartesisch)

### Ellipsoidisch (empfohlen fuer WGS84 / geografisches KBS)

Berechnet Flaechen und Laengen ueber die **gekruemmte Oberflaeche des Erdellipsoids** (z. B. WGS84).
- **Ideal fuer Ebenen in geografischem KBS (lat/lon)** wie WGS84 (EPSG:4326).
- Die Ergebnisse sind in **Metern / m²**, unabhaengig vom KBS der Ebene.
- Genauer fuer grosse Flaechen und hohe Breitengrade, da die Erdkruemmung beruecksichtigt wird.
- **Beispiel**: Eine in EPSG:4326 mit dieser Methode berechnete Flaeche liefert reale physikalische Werte in m².

### Kartesisch (empfohlen fuer UTM / projiziertes KBS)

Berechnet Flaechen und Laengen in der **kartesischen Ebene** des Ebenen-KBS.
- **Ideal fuer projizierte KBS wie UTM** (z. B. EPSG:31983 SIRGAS 2000 / UTM 23S), bei denen die Einheiten bereits Meter sind.
- Schnell und einfach, da nur planare Berechnungen verwendet werden (Satz des Pythagoras / Kreuzprodukt).
- **Vorsicht**: In geografischem KBS (Grad) wuerde die kartesische Berechnung Werte in **Grad / Grad²** ergeben, ohne physikalische Bedeutung.
- Wenn der kartesische Modus auf einer geografischen Ebene angefordert wird, wechselt das Plugin automatisch auf `Beides` und zeigt eine Warnung.

### Beides

Berechnet beide Methoden gleichzeitig.
- Erzeugt **zwei getrennte Felder** fuer jede Metrik (ein kartesisches und ein ellipsoidisches).
- Verwendet die unten konfigurierten Suffixe, um die Felder zu unterscheiden.
- Nuetzlich zum Vergleich der Ergebnisse und zur Validierung der Datenqualitaet.

## Tooltips (Widget-Beschreibungen)

Beim Ueberfahren eines beliebigen Einstellungsfelds wird eine detaillierte Beschreibung angezeigt:

- **Projektordner**: Stammordner, in dem Cadmus-Projekte erstellt und organisiert werden; dient als Standardort fuer neue Projekte und Ein-/Ausgabedateien.
- **Standard-KBS**: Referenzsystem, das verwendet wird, wenn kein KBS angegeben ist; WGS84 (EPSG:4326) ist der empfohlene Standard fuer globale Daten.
- **Sprache**: Definiert die Oberflaechensprache; `Automatisch erkennen` verwendet die QGIS-Sprache.
- **Genauigkeit von Vektorfeldern**: Anzahl der Dezimalstellen fuer Flaeche, Laenge und X/Y-Koordinaten; hoehere Werte erhoehen die Genauigkeit, erzeugen aber laengere Felder.
- **Asynchroner Grenzwert**: Mindestanzahl von Objekten, damit die Verarbeitung im Hintergrund laeuft; Ebenen kleiner als der Grenzwert laufen synchron (blockierend).
- **Werkzeugleiste - Sichtbare Kategorien**: Steuert, welche Werkzeugkategorien in der Werkzeugleiste erscheinen; deaktivieren zum Ausblenden.
- **Berechnungsmethode**: ellipsoidisch (ideal WGS84/geografisch), kartesisch (ideal UTM/projiziert) oder beides.
- **Kartesisches Suffix**: Text, der den im kartesischen Modus berechneten Feldern hinzugefuegt wird; leer = kein Suffix.
- **Ellipsoidisches Suffix**: Text, der den im ellipsoidischen Modus berechneten Feldern hinzugefuegt wird; Standard `_eli` zur Unterscheidung von kartesischen Feldern.

## Wichtiges Verhalten

- Der aktuelle asynchrone Grenzwert wird in Anzahl der Features gemessen, nicht in MB.
- Der Code akzeptiert Genauigkeitswerte zwischen 0 und 10.
- Der asynchrone Grenzwert akzeptiert Werte von 1 bis 100000000.
- Es gibt Rueckwaertskompatibilitaet beim Lesen des alten Schluessels `async_threshold_bytes`, aber nach dem Laden verwendet das Plugin den Grenzwert in Features.
- Dieses Werkzeug speichert nur Einstellungen; es fuehrt selbst keine Vektorberechnungen aus.

## Einstellungsordner

- Der Link in der Oberflaeche versucht, den Ordner `PREF_FOLDER` im Betriebssystem zu oeffnen.
- Wenn der Ordner nicht existiert, zeigt das Plugin eine Warnung anstatt den Explorer zu oeffnen.

## Wann man es verwenden sollte

Verwenden Sie dieses Werkzeug, wenn Sie das Standardverhalten anderer Cadmus-Werkzeuge anpassen moechten, die von diesen globalen Einstellungen abhaengen.

## Hinweise

- Aendern Sie die Berechnungsmethode nur, wenn sie zu Ihrem Arbeitsablauf passt.
- Wenn Sie den asynchronen Grenzwert zu stark senken, werden mehr Vorgaenge im Hintergrund ausgefuehrt.
- Wenn nach einer Einstellungsaenderung merkwuerdiges Verhalten auftritt, lohnt sich ein Blick in die gespeicherten Dateien im Einstellungsordner.
