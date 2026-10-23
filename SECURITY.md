# App- und APK-Security

## Ziel

Diese Leitlinie gilt fuer dieses App-/APK-Projekt. Security-Pruefungen sollen Risiken in Netzwerkzugriffen, Authentifizierung, lokaler Datenspeicherung, externen Links, Dateiverarbeitung und Release-Artefakten reduzieren.

Der Cloudflare Security Audit Skill kann dafuer als agentische Review-Methode genutzt werden. Er ist ein Entwicklungs- und Audit-Werkzeug, keine Runtime-Abhaengigkeit der App.

## Wann ein Security-Review erforderlich ist

Ein Security-Review ist vor einer APK-Auslieferung erforderlich, wenn seit der letzten ausgelieferten Version mindestens einer dieser Bereiche geaendert wurde:

- Login, Authentifizierung oder Session-Handling
- Speicherung von Zugangsdaten, Tokens oder personenbezogenen Daten
- API-Aufrufe, Anbieter-Integrationen oder Request-Parameter
- Buchungs-, Kauf-, Mail-, Energie-, Schul-, Fahrzeug- oder sonstige produktbezogene Fremdsystem-Anbindungen
- externe Links, Deep Links, Intents oder URL-Oeffnung
- WebView, Browser-Integration oder HTML/JavaScript-Verarbeitung
- Dateiverarbeitung, Import, Export, Cache oder lokale Datenbanken
- Berechtigungen im Android Manifest
- Build-, Signing- oder Release-Prozess

Bei rein visuellen Aenderungen ohne Daten-, Netzwerk- oder Berechtigungsbezug reicht eine kurze Security-Checkliste.

## Allgemeine Pruefschwerpunkte

- Keine Secrets, API-Keys, Tokens oder Passwoerter im Repository
- Keine sensiblen Daten in Logs, Toasts, Fehlertexten oder Screenshots
- Zugangsdaten nur verschluesselt speichern
- Externe URLs nur aus vertrauenswuerdigen Quellen oeffnen
- API- und Anbieterantworten defensiv parsen
- Fehler bei API-Ausfaellen ohne Datenleck behandeln
- Android-Berechtigungen minimal halten
- Lokaler Cache darf keine unnoetigen personenbezogenen oder vertraulichen Daten enthalten
- Fremdsystem-Aktionen duerfen nicht durch manipulierte Parameter erzwungen werden

## Android- und APK-Release-Check

Vor einem sicherheitsrelevanten APK-Build pruefen:

- `AndroidManifest.xml` enthaelt nur benoetigte Berechtigungen
- keine Debug-Ausgaben mit vertraulichen Daten
- keine hart codierten privaten Tokens
- keine unsicheren Klartext-Endpunkte
- keine ungeprueften externen Intents
- keine unbeabsichtigten Test-, Mock- oder Demo-Zugaenge
- Versionierung erfolgt erst unmittelbar vor dem ausdruecklich angeforderten Build, sofern das Projekt APK-Versionierungsregeln besitzt
- versionierte APKs werden dauerhaft archiviert, sofern das Projekt APK-Archivierungsregeln besitzt

## Cloudflare Security Audit Skill

Empfehlung: fuer groessere oder sicherheitsrelevante Aenderungen verwenden.

Einsatzform:

```text
Code-Aenderung
-> normaler Funktionstest
-> Security-Review
-> Findings bewerten
-> notwendige Fixes
-> APK-Build nur auf ausdrueckliche Anforderung
```

Der Skill sollte lokal versioniert oder bewusst installiert werden. Keine automatische Internet-Abhaengigkeit und keine automatische Aktualisierung in Firmenumgebungen.

## Finding-Gates

- Critical: blockiert Release immer
- High: blockiert Release standardmaessig
- Medium: Review und Entscheidung erforderlich
- Low: dokumentieren oder bei Gelegenheit beheben

## Grenzen

Der Cloudflare Security Audit Skill ersetzt keine klassischen Scanner und keine manuelle fachliche Kontrolle. Fuer groessere Projekte kann er mit passenden Tools kombiniert werden, zum Beispiel Secret-Scanning, Dependency-Audit, Semgrep oder plattformspezifischen Android-Pruefungen.

## Nicht-Ziele

- Keine produktive App-Abhaengigkeit
- Keine automatische APK-Erstellung
- Keine PWA-Anforderung, sofern das Projekt dies nicht ausdruecklich verlangt
- Keine Live-Tests gegen fremde Produktionssysteme ohne ausdrueckliche Freigabe

## Yeal-spezifisch (Downloader)

Yeal laedt beliebige, vom Nutzer eingegebene URLs ueber yt-dlp herunter. Es gibt kein Login, keine Konten, keine eigenen Server und keine Zugangsdaten.

| Bereich | Regel / Stand |
|---|---|
| Eingaben | Nur `http(s)://`-Links werden angenommen (Regex in `ui/backend.py`). Keine Shell-Aufrufe mit Nutzereingaben; yt-dlp laeuft als Python-Bibliothek. |
| Eigene yt-dlp-Optionen (JSON) | Gefiltert durch `FORBIDDEN_KEYS` in `core/presets.py`: kein `exec_cmd`, keine eigenen Postprozessoren, keine externen Downloader, kein `paths`/`ffmpeg_location`, keine Browser-Cookies; `outtmpl` ohne `..` und ohne absolute Pfade. Getestet in `tests/test_core.py`. |
| Dateien | Schreibzugriff nur in Download-Ordner und App-Datenordner. Dateinamen kommen von yt-dlp (`%(title).150B`, unter Windows `windowsfilenames`). |
| Netzwerk | Nur ausgehend (yt-dlp). Android braucht `INTERNET` - Manifest nach erstem Build pruefen, keine weiteren Berechtigungen. |
| Android-Speicher | Scoped Storage; kein `MANAGE_EXTERNAL_STORAGE`. |
| Logs / Fehlertexte | Fehler werden auf eine Zeile gekuerzt (`clean_error`); keine Tokens oder Cookies werden gespeichert. |
| Lieferkette | yt-dlp wird bei jedem Build neu geladen (ungepinnt) - Version im Build-Log dokumentieren. ffmpeg stammt aus `Tools_Central\Video Tools`. |
| Offener Punkt | Der Cloud-Workflow wurde noch nicht real ausgefuehrt; das Manifest und die Berechtigungen der ersten APK sind ungeprueft. |
| yt-dlp-Selbstupdate | Yeal laedt yt-dlp und yt-dlp-ejs als Wheels von pypi.org (nur HTTPS, feste Hosts), prueft SHA-256 aus der PyPI-Metadaten-Antwort, blockt Pfade ausserhalb des Zielordners (zip-slip) und tauscht den Ordner atomar (Rollback bei Fehler). Das schuetzt vor defekten Downloads, nicht vor einem kompromittierten PyPI. Abschaltbar in den Einstellungen. Getestet in `tests/test_updater.py`. |
| JavaScript-Laufzeit | Node wird nur als Hilfsprozess von yt-dlp (YouTube-Signatur) mit festem Pfad aus Tools_Central/App-Ordner/`YEAL_NODE` benutzt, nie mit Nutzereingaben als Kommandozeile. |
