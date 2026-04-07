# PDF_TO_EPUB_EXPORTER

Modularer PDF-to-EPUB Exporter mit aktivierbaren Pipeline-Schritten.

## Ziele

- Zwei unabhaengige Scan-Schritte (Scan A und Scan B)
- Abgleich beider Scan-Ergebnisse
- Woerterbuch-Pruefung fuer moegliche OCR-Fehler
- EPUB-Export
- Einfache Erweiterbarkeit: neue Schritte hinzufuegen, deaktivieren oder entfernen

## Projektstruktur

```
src/pdf_to_epub_exporter/
	cli.py
	config.py
	context.py
	dictionary.py
	epub.py
	pipeline.py
	registry.py
	scanners.py
	step.py
	steps/
		scan_a.py
		scan_b.py
		reconcile.py
		dictionary_check.py
		export_epub.py
pipeline.example.json
run.py
```

## Schneller Start

1. Python 3.10+ nutzen.
2. Abhaengigkeiten installieren:

```bash
pip install -e .
```

3. Fuer OCR Tesseract lokal installieren und im PATH verfuegbar machen.
4. Beispielkonfiguration anpassen: `pipeline.example.json`
5. Pipeline ausfuehren:

```bash
python run.py run --pdf ./input/mein_dokument.pdf --output ./output --config ./pipeline.example.json
```

## Wie die Scans funktionieren

- `scan_a`: OCR-Methode. Das PDF wird als Bild gerendert und mit Tesseract gelesen.
- `scan_b`: Schnelle Methode. Direkte Textextraktion aus dem PDF-Textlayer.

Damit bekommst du zwei unterschiedliche Quellen fuer den spaeteren Abgleich.

Falls ein Scan leer ist, kann optional auf Sidecar-Dateien zurueckgefallen werden:

- `mein_dokument.scan_a.txt`
- `mein_dokument.scan_b.txt`

## Pipeline-Konfiguration

Beispiel (gekuerzt):

```json
{
	"steps": [
		{
			"id": "scan_a",
			"enabled": true,
			"params": {
				"ocr_language": "deu+eng",
				"ocr_dpi": 300,
				"use_sidecar_fallback": true
			}
		},
		{
			"id": "scan_b",
			"enabled": true,
			"params": {
				"use_sidecar_fallback": true
			}
		},
		{ "id": "reconcile_scans", "enabled": true, "params": {} },
		{
			"id": "dictionary_check",
			"enabled": true,
			"params": {
				"dictionary_file": "resources/de_dictionary_sample.txt",
				"cutoff": 0.85
			}
		},
		{
			"id": "export_epub",
			"enabled": true,
			"params": {
				"title": "Mein Buch",
				"author": "Unbekannt",
				"output_file": "mein_buch.epub"
			}
		}
	]
}
```

## Neue Methoden hinzufuegen

1. Neue Step-Klasse in `src/pdf_to_epub_exporter/steps/` erstellen.
2. In `src/pdf_to_epub_exporter/steps/__init__.py` in der Registry registrieren.
3. Step-ID in der Config hinzufuegen und `enabled` setzen.

## Deaktivieren oder Entfernen

- Deaktivieren: in der Config `"enabled": false`
- Entfernen: Step-Eintrag aus `steps` loeschen