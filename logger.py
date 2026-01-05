# logger.py - CSV-Datenlogger (Version 1.0 - Robust)

import time
import os

LOGFILE = "log.csv"
MAX_LINES = 500 
HEADER_LINE = "Zeit,Sensor A,Sensor B,Sensor C\n" # ACHTUNG: Leerzeichen im Header!

def _now_string():
    """YYYY-MM-DD HH:MM:SS"""
    try:
        ts = time.localtime()
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            ts[0], ts[1], ts[2], ts[3], ts[4], ts[5])
    except:
        return "1970-01-01 00:00:00"

def _ensure_header():
    """Stellt sicher, dass das Logfile existiert und einen Header hat."""
    try:
        if LOGFILE not in os.listdir() or os.stat(LOGFILE)[6] < 10:
            with open(LOGFILE, "w") as f:
                f.write(HEADER_LINE)
    except Exception as e:
        print("Logger Header Check Error:", e)

def add_entry(t1, t2, t3):
    """Fügt einen Eintrag hinzu und trimmt das Log, falls es zu groß wird."""
    _ensure_header() 
    
    ts = _now_string()
    def _fmt(v):
        # None wird zu leerem String, den das JS dann als '--' oder leeren Wert liest
        return "" if v is None else "{:.3f}".format(v)
    
    line = "{},{},{},{}\n".format(ts, _fmt(t1), _fmt(t2), _fmt(t3))
    
    try:
        # Trim-Logik
        lines = []
        try:
            with open(LOGFILE, "r") as f:
                lines = f.readlines()
        except OSError:
            lines = [HEADER_LINE]

        if len(lines) > MAX_LINES + 1: # +1 für den Header
            lines = [lines[0]] + lines[-MAX_LINES:]  
            with open(LOGFILE, "w") as f:
                f.writelines(lines)
        
        # Neuen Eintrag anhängen
        with open(LOGFILE, "a") as f:
            f.write(line)
            try:
                f.flush() 
            except:
                pass
    except Exception as e:
        print("Logger add_entry error:", e)

def get_log():
    """Gesamte CSV (inkl. Header) für den Download"""
    try:
        with open(LOGFILE, "r") as f:
            return f.read()
    except OSError:
        return HEADER_LINE

def get_log_lines(limit=100):
    """LETZTE 'limit' DATENZEILEN (OHNE HEADER) - für Tabellenanzeige"""
    try:
        with open(LOGFILE, "r") as f:
            lines = f.readlines()
            
        if not lines:
            return []
            
        # Header entfernen (die erste Zeile)
        # Wir prüfen auf den Header, um robust zu sein, aber nehmen meistens lines[1:]
        data_lines = lines[1:] if lines[0].strip().startswith("Zeit") else lines
        
        # Leere Zeilen entfernen
        clean_lines = [l.strip() for l in data_lines if l.strip()]
        
        # Die letzten 'limit' Zeilen zurückgeben
        return clean_lines[-limit:]

    except OSError:
        return []

def clear_log():
    """Log leeren und Header neu schreiben"""
    try:
        with open(LOGFILE, "w") as f:
            f.write(HEADER_LINE)
        print("Log geleert")
    except Exception as e:
        print("Logger clear_log error:", e)

# Initialer Header-Check beim Modul-Import
_ensure_header()