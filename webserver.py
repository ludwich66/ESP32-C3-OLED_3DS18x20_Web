# webserver.py - AP + Dashboard + CSV-Download (VERSION 1.5 - Trigger + ROM-ID + Offset)

import network
import socket
import json
import time
import logger
import sys  # Für machine.reset

# Globale Variablen für Webserver-Handler
cfg_global = {}
get_temps_global = None
save_cb_global = None
rom_info_global = []  # Sensor ROM Informationen (Familie + Serial)

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>THERMO-Logger V1.5</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #4CAF50; margin-bottom: 20px; }
        .status-box { background: #2a2a2a; border-left: 4px solid #4CAF50; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .sensor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-top: 10px; }
        .sensor-card { padding: 15px; border-radius: 5px; background: #333; border-left: 4px solid #555; }
        .sensor-title { font-weight: bold; margin-bottom: 5px; }
        .sensor-temp { font-size: 22px; font-weight: bold; margin-top: 5px; }
        .sensor-meta { font-size: 10px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #555; opacity: 0.75; font-family: monospace; line-height: 1.4; }

        /* Status-Farben */
        .state-low    { border-color: #2196F3; } .state-low .sensor-temp { color: #2196F3; }
        .state-normal { border-color: #4CAF50; } .state-normal .sensor-temp { color: #4CAF50; }
        .state-high   { border-color: #F44336; } .state-high .sensor-temp { color: #F44336; }
        .state-off    { border-color: #777; } .state-off .sensor-temp { color: #777; }

        .config-section { background: #2a2a2a; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .form-group { margin: 10px 0; }
        label { display: block; margin-bottom: 4px; color: #ccc; }
        input, select { width: 100%; padding: 8px; background: #333; color: #fff; border: 1px solid #444; border-radius: 3px; font-size: 14px; }
        .sensor-row { display: grid; grid-template-columns: 30px 70px 80px 80px 80px 90px; gap: 5px; align-items: center; margin-bottom: 8px; font-size: 13px; }

        button { background: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 3px; cursor: pointer; font-size: 14px; margin-right: 5px; }
        button:hover { background: #45a049; }

        .log-section { background: #2a2a2a; padding: 20px; border-radius: 5px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #444; font-size: 14px; }
        th { background: #333; color: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌡️ THERMO-Logger V1.5</h1>

        <div class="status-box">
            <h2>📊 Live Status</h2>
            <div id="sensor-grid" class="sensor-grid"></div>
        </div>

        <div class="config-section">
            <h2>⚙️ Konfiguration</h2>
            
            <div class="form-group">
                <label>Auflösung DS18B20:</label>
                <select id="resolution">
                    <option value="9">9-bit (0.5°C)</option>
                    <option value="10">10-bit (0.25°C)</option>
                    <option value="11">11-bit (0.125°C)</option>
                    <option value="12">12-bit (0.0625°C)</option>
                </select>
            </div>

            <div class="form-group">
                <label>WiFi AP SSID:</label>
                <input type="text" id="ap_ssid" placeholder="TEMPLOGGER_Setup">
            </div>

            <div class="form-group">
                <label>WiFi AP Passwort:</label>
                <input type="password" id="ap_password" placeholder="password1234">
            </div>

            <div class="form-group">
                <label>Display Timeout (Sekunden, 0 = aus):</label>
                <input type="number" id="display_timeout_s" min="0" value="60">
            </div>

            <div class="form-group">
                <label>Messintervall (Sekunden, 1–86400):</label>
                <input type="number" id="measure_interval_s" min="1" max="86400" value="2">
            </div>

            <h3>Sensor A/B/C Trigger & Kalibrierung</h3>
            <div id="sensor-config"></div>

            <button onclick="saveConfig()">💾 Speichern & Reboot</button>
        </div>

        <div class="log-section">
            <h2>📜 Temperatur Log (letzte 20 Einträge)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Zeit</th>
                        <th>Sensor A</th>
                        <th>Sensor B</th>
                        <th>Sensor C</th>
                    </tr>
                </thead>
                <tbody id="log-body">
                    <tr><td colspan="4">Laden...</td></tr>
                </tbody>
            </table>
            <button onclick="clearLog()">🗑️ Log löschen</button>
            <button onclick="downloadCsv()">⬇️ CSV herunterladen</button>
        </div>
    </div>

    <script>
        const CONFIG_URL = '/api/config';
        const TEMPS_URL  = '/api/temps';
        const LOG_URL    = '/api/log';
        const SAVE_URL   = '/api/save';
        const CLEAR_URL  = '/api/clear';

        let currentCfg = null;

        function buildSensorConfig(cfg) {
            const container = document.getElementById('sensor-config');
            container.innerHTML = '';
            const labels = ['A','B','C'];
            labels.forEach(label => {
                const sc = (cfg.sensors && cfg.sensors[label]) || {};
                const enabled = sc.enabled !== false;
                const low  = sc.low_trigger  != null ? sc.low_trigger  : 18.0;
                const high = sc.high_trigger != null ? sc.high_trigger : 25.0;
                const invert = sc.invert_logic === true;
                const offset = sc.offset != null ? sc.offset : 0.0;

                const row = document.createElement('div');
                row.className = 'sensor-row';
                row.innerHTML = `
                    <span>${label}</span>
                    <label><input type="checkbox" id="en_${label}" ${enabled ? 'checked' : ''}> Aktiv</label>
                    <input type="number" id="low_${label}" step="0.1" value="${low}" placeholder="Low">
                    <input type="number" id="high_${label}" step="0.1" value="${high}" placeholder="High">
                    <input type="number" id="offset_${label}" step="0.1" value="${offset}" placeholder="Offset">
                    <label><input type="checkbox" id="inv_${label}" ${invert ? 'checked' : ''}> Invert</label>
                `;
                container.appendChild(row);
            });
        }

        async function loadConfig() {
            try {
                const resp = await fetch(CONFIG_URL);
                const cfg = await resp.json();
                currentCfg = cfg;

                document.getElementById('resolution').value = cfg.resolution || 12;
                document.getElementById('ap_ssid').value = cfg.ap_ssid || '';
                document.getElementById('ap_password').value = cfg.ap_password || '';
                document.getElementById('display_timeout_s').value = cfg.display_timeout_s || 60;
                document.getElementById('measure_interval_s').value = cfg.measure_interval_s || 2;

                buildSensorConfig(cfg);
            } catch (e) {
                console.error('Load config error:', e);
            }
        }

        async function saveConfig() {
            const cfg = currentCfg || {};
            cfg.resolution = parseInt(document.getElementById('resolution').value);
            cfg.ap_ssid = document.getElementById('ap_ssid').value;
            cfg.ap_password = document.getElementById('ap_password').value;
            cfg.display_timeout_s = parseInt(document.getElementById('display_timeout_s').value) || 0;
            cfg.measure_interval_s = parseInt(document.getElementById('measure_interval_s').value) || 2;
            if (cfg.measure_interval_s < 1) cfg.measure_interval_s = 1;
            if (cfg.measure_interval_s > 86400) cfg.measure_interval_s = 86400;

            cfg.sensors = cfg.sensors || {};
            ['A','B','C'].forEach(label => {
                cfg.sensors[label] = {
                    enabled: document.getElementById('en_' + label).checked,
                    low_trigger: parseFloat(document.getElementById('low_' + label).value),
                    high_trigger: parseFloat(document.getElementById('high_' + label).value),
                    offset: parseFloat(document.getElementById('offset_' + label).value) || 0.0,
                    invert_logic: document.getElementById('inv_' + label).checked
                };
            });

            try {
                await fetch(SAVE_URL, {
                    method: 'POST',
                    body: JSON.stringify(cfg)
                });
                alert('Konfiguration gespeichert – THERMO startet neu... - WLAN verbinden');
                setTimeout(() => location.reload(), 2000);
            } catch (e) {
                alert('Fehler beim Speichern: ' + e);
            }
        }

        function getStatusClass(t, st) {
            if (st === 'off' || st === 'none' || t === null) {
                return 'sensor-card state-off';
            } else if (st === 'low') {
                return 'sensor-card state-low';
            } else if (st === 'high') {
                return 'sensor-card state-high';
            } else {
                return 'sensor-card state-normal';
            }
        }

        async function loadTemps() {
            try {
                const resp = await fetch(TEMPS_URL);
                const data = await resp.json();
                const grid = document.getElementById('sensor-grid');
                grid.innerHTML = '';
                data.labels.forEach((label, idx) => {
                    const t = data.temps[idx];
                    const st = data.status[idx];
                    const family = data.rom_family ? data.rom_family[idx] : '--';
                    const serial = data.rom_serial ? data.rom_serial[idx] : '--';

                    let text = '--';
                    if (t !== null) {
                        text = t.toFixed(3) + ' °C';
                    }

                    // Vollständige ROM-Adresse mit Trennzeichen: Family-Serial-CRC
                    let displayRom = serial;
                    if (serial.length === 16) {
                        displayRom = serial.slice(0,2) + '-' + serial.slice(2,14) + '-' + serial.slice(14,16);
                    } else if (serial !== '--') {
                        displayRom = serial;
                    }

                    const card = document.createElement('div');
                    card.className = getStatusClass(t, st);
                    card.innerHTML = `
                        <div class="sensor-title">Sensor ${label}</div>
                        <div class="sensor-temp">${text}</div>
                        <div style="font-size: 12px; margin-top: 4px;">Status: ${st}</div>
                        <div class="sensor-meta">Family: ${family}<br/>ROM: ${displayRom}</div>
                    `;
                    grid.appendChild(card);
                });
            } catch (e) {
                console.error('Load temps error:', e);
            }
        }

        async function loadLog() {
            try {
                const resp = await fetch(LOG_URL);
                const data = await resp.json();
                const body = document.getElementById('log-body');
                let html = '';
                data.log.slice(-20).forEach(line => {
                    const parts = line.split(',');
                    if (parts.length >= 4) {
                        html += `
                            <tr>
                                <td>${parts[0]}</td>
                                <td>${parts[1] || '--'}</td>
                                <td>${parts[2] || '--'}</td>
                                <td>${parts[3] || '--'}</td>
                            </tr>
                        `;
                    }
                });
                body.innerHTML = html || '<tr><td colspan="4">Keine Daten</td></tr>';
            } catch (e) {
                console.error('Load log error:', e);
            }
        }

        async function clearLog() {
            if (!confirm('Wirklich alle Log-Einträge löschen?')) return;
            try {
                await fetch(CLEAR_URL, {method: 'POST'});
                loadLog();
            } catch (e) {
                alert('Fehler: ' + e);
            }
        }

        async function downloadCsv() {
            try {
                const resp = await fetch('/api/log.csv');
                const text = await resp.text();
                const blob = new Blob([text], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'thermo-log.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (e) {
                alert('Fehler beim CSV-Download: ' + e);
            }
        }

        // Initial laden
        loadConfig();
        loadTemps();
        loadLog();
        
        // Alle 5 Sekunden aktualisieren
        setInterval(() => {
            loadTemps();
            loadLog();
        }, 5000);
    </script>
</body>
</html>
"""

def build_temps_payload():
    """Erstellt Temps + Status + ROM-Info für Dashboard - VERSION 1.5"""
    temps = get_temps_global()
    labels = ["A", "B", "C"]
    status = []
    rom_family = []
    rom_serial = []
    
    for i, t in enumerate(temps):
        label = labels[i]
        scfg = cfg_global.get("sensors", {}).get(label, {"enabled": True})
        
        if not scfg.get("enabled", True):
            st = "off"
        elif t is None:
            st = "none"
        else:
            low = scfg.get("low_trigger", 18.0)
            high = scfg.get("high_trigger", 25.0)
            if t < low:
                st = "low"
            elif t > high:
                st = "high"
            else:
                st = "normal"
        
        status.append(st)
        
        # ROM-Info hinzufügen
        if i < len(rom_info_global) and rom_info_global[i]:
            rom_family.append(rom_info_global[i].get("family", "--"))
            rom_serial.append(rom_info_global[i].get("serial", "--"))
        else:
            rom_family.append("--")
            rom_serial.append("--")
    
    return {
        "temps": temps,
        "status": status,
        "labels": labels,
        "rom_family": rom_family,
        "rom_serial": rom_serial,
    }

def handle_client(conn, addr):
    try:
        conn.settimeout(2)
        request = conn.recv(1024).decode() 
        if not request:
            conn.close()
            return

        lines = request.split("\r\n")
        first = lines[0].split()
        if len(first) < 2:
            conn.close()
            return
        method = first[0]
        path   = first[1]
        
        resp = None

        if method == "GET":
            if path == "/":
                resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n" + html_template
            elif path == "/api/config":
                resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json.dumps(cfg_global)
            elif path == "/api/temps":
                data = build_temps_payload()
                resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json.dumps(data)
            elif path == "/api/log":
                log_lines = logger.get_log_lines(100) 
                data = json.dumps({"log": log_lines})
                resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + data
            elif path == "/api/log.csv":
                csv_data = logger.get_log()
                resp = "HTTP/1.1 200 OK\r\n"
                resp += "Content-Type: text/csv\r\n"
                resp += "Content-Disposition: attachment; filename=\"THERMO-LOGGER-Log.csv\"\r\n"
                resp += "Connection: close\r\n"
                resp += "\r\n"
                resp += csv_data
            else:
                resp = "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n404"

        elif method == "POST":
            body = request.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in request else ""
            
            if path == "/api/save":
                try:
                    new_cfg = json.loads(body)
                    cfg_global.update(new_cfg)
                    save_cb_global(cfg_global)
                    resp = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"status":"ok"}'
                except Exception as e:
                    print("Config save error:", e)
                    resp = 'HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\n'
                conn.send(resp)
                conn.close()
                time.sleep(2)
                import machine
                machine.reset()
                return
            elif path == "/api/clear":
                logger.clear_log()
                resp = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"status":"cleared"}'
            else:
                resp = "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n404"
        else:
            resp = "HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n405"

        if resp:
            conn.sendall(resp)
            conn.close()
            
    except OSError:
        try:
            conn.close()
        except:
            pass
    except Exception as e:
        print("Webserver Error:", e)
        try:
            conn.close()
        except:
            pass

def start_webserver(roms, cfg, save_cb, get_temps, rom_info=None):
    """Startet Webserver - VERSION 1.5"""
    global cfg_global, get_temps_global, save_cb_global, rom_info_global
    import machine
    
    cfg_global = cfg
    get_temps_global = get_temps
    save_cb_global = save_cb
    rom_info_global = rom_info or []

    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    time.sleep(0.5)
    ap.active(True)

    ssid = cfg.get("ap_ssid", "TEMPLOGGER_Setup")
    pw   = cfg.get("ap_password", "password1234")

    ap.config(essid=ssid, password=pw)
    ap.active(True)

    print("WiFi AP started:", ssid)
    print("IP:", ap.ifconfig()[0])

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(1)
    sock.settimeout(10)

    print("Webserver ready! Navigate to http://192.168.4.1")
    while True:
        try:
            conn, addr = sock.accept()
            handle_client(conn, addr)
        except OSError:
            pass
        except Exception as e:
            print("Socket Accept Error:", e)
            time.sleep(1)
