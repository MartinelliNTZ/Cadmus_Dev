<!--
Versao: 1.0.0
Data de criacao: 2026-08-07
Data da ultima modificacao: 2026-08-10
-->

# Alle Layouts Exportieren - Kurzanleitung

Exportiert alle Layouts des aktuellen Projekts als PDF, PNG und/oder SVG, mit Georeferenzierung, Ausgabe-DPI, Zusammenfuehrung der Enddateien und individueller Layout-Auswahl.

## Ausgabeformate

Waehlen Sie mindestens ein Format:

- `Export PDF` - erzeugt ein PDF pro Layout. Mit aktivierter Option `Georeference PDF` erhaelt das PDF eine Georeferenzierung.
- `Export PNG` - erzeugt ein PNG-Bild pro Layout.
- `Export SVG` - erzeugt ein Vektor-SVG pro Layout.

Der Export wird blockiert, wenn kein Format markiert ist.

## Allgemeine Optionen

- `Ausgabe-DPI` - definiert die Aufloesung der exportierten Dateien. Der Wert `0` (Standard) verwendet das im Layout konfigurierte DPI. Hoehere Werte wenden ein festes DPI auf PDFs, PNGs und SVGs an.
- `Max Width` - maximale Breite in Pixeln, die beim Zusammenfuehren von PNGs in ein endgueltiges PDF verwendet wird.
- `Ausgabeordner` - Zielordner fuer die Dateien. Der Standard ist `exports` im Projektverzeichnis und wird automatisch erstellt, falls er nicht existiert.

## Layout-Auswahl

- Klicken Sie auf `Layouts`, um auszuwaehlen, welche Layouts exportiert werden sollen.
- Die Auswahl wird fuer die naechsten Ausfuehrungen des Werkzeugs gespeichert.
- Wenn kein Layout ausgewaehlt ist, werden alle Layouts des Projekts exportiert.
- Wenn das Projekt keine Layouts hat, zeigt das Werkzeug einen Hinweis an.

## Dateizusammenfuehrung

- `Merge PDF` - fuegt alle exportierten PDFs in eine einzige `_PDF_UNICO_FINAL.pdf` zusammen.
- `Merge PNG` - wandelt alle exportierten PNGs in eine einzige `_PNG_MERGED_FINAL.pdf` um, unter Beruecksichtigung von `Max Width`.

Die Zusammenfuehrung haengt von optionalen Bibliotheken ab: `PyPDF2` (PDFs) und `Pillow` (PNGs). Wenn die Bibliothek fehlt, fragt das Werkzeug, ob sie installiert werden soll; bei Ablehnung wird die Zusammenfuehrung uebersprungen und der Export laeuft normal weiter.

## Dateinamen

- Ungueltige Dateisystemzeichen (`< > : " / \ | ? *`) werden aus jedem Layoutnamen entfernt.
- Bei deaktivierter Option `Replace Existing` (Standard) erhalten Dateien mit vorhandenem Namen eine numerische Erweiterung (`Layout_1`, `Layout_2`...).
- Bei aktivierter Option `Replace Existing` werden vorhandene Dateien ohne numerische Kopien ueberschrieben.

## Verwendung

1. Oeffnen Sie `Cadmus > Export All Layouts`.
2. Markieren Sie mindestens ein Format: PDF, PNG und/oder SVG.
3. Passen Sie `DPI`, `Georeference PDF`, `Max Width` und die Zusammenfuehrungen nach Bedarf an.
4. Waehlen Sie den Ausgabeordner (Standard `.../exports`).
5. Optional: Klicken Sie auf `Layouts` und waehlen Sie die gewuenschten Layouts aus.
6. Klicken Sie auf `Export` und verfolgen Sie die Fortschrittsleiste (Abbruch ist moeglich).
7. Am Ende zeigt eine Zusammenfassung Erfolge, Fehler und Zielordner; zusammengefuehrte Dateien werden angegeben.

## Was das Plugin tatsaechlich macht

- Liest die Projekt-Layouts ueber `layoutManager().layouts()` und filtert nach der in `Layouts` getroffenen Auswahl.
- Prueft, dass vor dem Start mindestens ein Format markiert ist.
- Erstellt den Ausgabeordner automatisch, falls er nicht existiert.
- Exportiert jedes Layout mit `QgsLayoutExporter` in den markierten Formaten und wendet `dpi` an, wenn es groesser als null ist.
- Wendet die Georeferenzierung nur auf das PDF an, wenn `Georeference PDF` markiert ist.
- Erzeugt eindeutige Namen mit numerischer Erweiterung, wenn `Replace Existing` deaktiviert ist.
- Zaehlt ein Layout als Erfolg, wenn mindestens ein Format erfolgreich exportiert wurde.
- Zeigt einen `ProgressDialog`, unterstuetzt den Abbruch und stoppt die Schleife an der aktuellen Stelle.
- Fuehrt am Ende die angeforderten Zusammenfuehrungen aus (`_PDF_UNICO_FINAL.pdf` und/oder `_PNG_MERGED_FINAL.pdf`).
- Speichert die Einstellungen automatisch (Formate, DPI, Max Width, Ordner, ausgewaehlte Layouts) beim Schliessen des Fensters.

## Wichtiges Verhalten

- Es muss mindestens ein Format (PDF, PNG oder SVG) markiert sein.
- Wenn ein Layout in einem Format fehlschlaegt, aber in einem anderen gelingt, wird es als Erfolg gezaehlt und der Fehler erscheint in der Zusammenfassung.
- Ein Abbruch des Exports behaelt die bereits exportierten Dateien im Ordner.
- Ein `DPI`-Wert von 0 delegiert an das Layout; positive Werte ueberschreiben das DPI der erzeugten Dateien.

## Wann man es verwenden sollte

Verwenden Sie dieses Werkzeug, wenn Sie schnell alle Layouts eines Projekts exportieren muessen, ohne jedes einzeln zu oeffnen und zu speichern.

Es ist besonders nuetzlich, um:

- einen vollstaendigen Satz Plaene zu liefern;
- Serienexports fuer Revisionen zu erzeugen;
- PDF- oder PNG-Ausgaben in einer einzigen Enddatei zu konsolidieren;
- Vektorversionen (SVG) der Layouts zu erzeugen.

## Hinweise

- Pruefen Sie vor der Ausfuehrung den Ausgabeordner, besonders wenn `Replace Existing` aktiviert ist.
- Kontrollieren Sie die erzeugten Dateien, wenn Layouts aehnliche Namen haben.
- Bei grossen Projekten exportieren Sie zuerst ohne Zusammenfuehrung, um das Ergebnis zu validieren.
- `Merge PNG` kann je nach Anzahl der Bilder und dem eingestellten `Max Width` grosse PDFs erzeugen.