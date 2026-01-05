# ESP32-C3-OLED_3DS18x20_Web

THERMO-Logger V1.4 – ESP32‑C3 OLED Temperatur- und Relaisregler

# Projektüberblick

THERMO-Logger V1.4 ist ein kompakter Temperatur-Logger und -Regler auf Basis eines ESP32‑C3 mit integriertem OLED-Display und drei DS18B20-Sensoren.
​
Das Projekt bietet ein Web-Dashboard, CSV-Logging, konfigurierbare Trigger-Grenzen und drei GPIO-Ausgänge zur Ansteuerung externer Aktoren (z.B. Relais für Heizung/Kühlung).
​
# Hardware
* Board: ESP32‑C3_OLED (ESP32‑C3 mit integriertem I2C-OLED 72x40)
​
* Sensoren: 3 × DS18B20 an GPIO 0 (A), 1 (B), 2 (C)​

* Anzeige: SSD1306 OLED via I2C (SDA=GPIO 5, SCL=GPIO 6)

# OLED -THERMO- Format

* -THERMO-    #
* A: 17.888   # Example "normal"
* B:_17.888   # Example "low"
* C:17.888_   # Example "high"

<img width="250" height="300" alt="image" src="https://github.com/user-attachments/assets/3a8572ae-de83-48c6-aabc-48421ecaf35a" /><img width="250" height="300" alt="image" src="https://github.com/user-attachments/assets/fe39c7ac-3afc-4f63-9f10-a10b8d16e8e4" />​

* Onboard-LED: GPIO 8, low-aktiv (0=AN, 1=AUS)​
* Wake-/Boot-Taster: GPIO 9, Pull‑Up, weckt Display und triggert Messungen

Trigger-Ausgänge:

* GPIO 3 → Sensor A Output
* GPIO 4 → Sensor B Output
* GPIO 7 → Sensor C Output
​
# Firmware-Funktionen
* Periodische Temperaturmessung aller drei DS18B20 mit einstellbarer Auflösung und Messintervall.​
* OLED-Anzeige im Format -THERMO- mit Markierung von Unter- und Überschreitung durch Unterstriche links/rechts der Temperatur.​
* Energiesparender Screensaver: Display geht nach konfigurierbarem Timeout aus, Wake über BOOT-Button.
​
# Web-Dashboard
* Eigenständiger Access Point (Standard: THERMO_192.168.4.1, Passwort password1234).
​
# Single-Page-Dashboard mit folgenden Bereichen:

<img width="328" height="576" alt="image" src="https://github.com/user-attachments/assets/af5a7e2e-170e-4271-b337-9c0a43e13786" />

* Live-Status der Sensoren (Temperatur, Status low/normal/high, ROM-ID mit DS18B20-Familie und vollständiger 64‑Bit‑Adresse).
​* Konfiguration (Auflösung, AP-SSID/Passwort, Display-Timeout, Messintervall).
​
Pro Sensor A/B/C:

* Aktiv-Checkbox
* Low- und High-Trigger
* Checkbox Invert logic zur Auswahl Heiz-/Kühlbetrieb​
* Trigger- und Reglerlogik

Je Sensor ein dedizierter GPIO-Ausgang (A → GPIO 3, B → GPIO 4, C → GPIO 7) zur Ansteuerung von Relais, SSR oder ähnlichen Lasten.
# Standardlogik (Invert logic = aus):
* Temperatur unterhalb low_trigger oder im Bereich low..high → Ausgang HIGH (typisch Heizung EIN).
* Temperatur oberhalb high_trigger → Ausgang LOW (Heizung AUS).

# Invertierte Logik (Invert logic = an): 
* Obiges Verhalten wird invertiert, geeignet für Kühlung oder Lüftersteuerung.
​
# Logging und CSV-Export
* Laufende Protokollierung jeder Messung (Zeitstempel, Sensor A/B/C) in log.csv im Flash.
* Web-Dashboard: Anzeige der letzten 20 Einträge und Buttons für „Log löschen“ und „CSV herunterladen“.
​
# Konfiguration und Persistenz
* Alle Einstellungen werden in config.json gespeichert (Auflösung, WLAN, Zeitouts, Sensor-Trigger, invert_logic je Sensor).
* Änderungen im Web-Dashboard werden per REST-API übernommen, im Flash gesichert und führen zu einem automatischen Neustart des ESP32‑C3-OLED.

# Typische Anwendungsfälle
* Mehrkanal-Heizungsregler (z.B. drei Räume/Zonen) mit frei wählbaren Temperaturfenstern.
* Kühl- oder Lüftersteuerung durch invertierte Logik pro Kanal.
* Langzeit-Logging von Temperaturverläufen mit CSV-Export zur Auswertung am PC.
