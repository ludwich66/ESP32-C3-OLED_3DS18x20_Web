# main.py - AP + Webserver + Logger, OLED-Screensaver mit Boot-Button - VERSION 1.4

''' PERPLEXITY

ESP32-C3_OLED
GPIO 0 = Sensor A Input
GPIO 1 = Sensor B Input
GPIO 2 = Sensor C Input
GPIO 3 = Sensor A Output
GPIO 4 = Sensor B Output
GPIO 5 = I2C SDA=5
GPIO 6 = I2C SCL=6
GPIO 7 = Sensor C Output
GPIO 8 = ONBOARD LED (Low-active: 0=ON, 1=OFF), 
GPIO 9 = BOOT Button (Pull-up, aktiv LOW)

OLED -THERMO- Format

# -THERMO-    #
# A: 17.888   # Example "normal"
# B:_17.888   # Example "low"
# C:17.888_   # Example "high"

'''

import time
from machine import Pin, I2C, unique_id
import ubinascii
import json
import _thread

# Import der Hilfsmodule (müssen auf dem Gerät vorhanden sein)
try:
    import webserver
    import logger
    from ssd1306 import SSD1306
    from Klasse_DS18x20 import DS18x20
except ImportError as e:
    print("Kritischer Fehler: Modul fehlt!", e)

# -------------------------------------------------------
# Konfiguration laden / speichern
# -------------------------------------------------------

DEFAULT_CFG = {
    "resolution": 12,
    "ap_ssid": "THERMO_192.168.4.1",
    "ap_password": "password1234",
    "display_timeout_s": 60,
    "measure_interval_s": 2,
    "sensors": {
        "A": {"enabled": True, "low_trigger": 18.0, "high_trigger": 25.0, "invert_logic": False},
        "B": {"enabled": True, "low_trigger": 18.0, "high_trigger": 25.0, "invert_logic": False},
        "C": {"enabled": True, "low_trigger": 18.0, "high_trigger": 25.0, "invert_logic": False},
    },
}

def load_config():
    try:
        with open("config.json") as f:
            cfg = json.load(f)
    except:
        print("Keine config.json gefunden, lade Defaults.")
        cfg = {}

    # Defaults auffüllen
    for k, v in DEFAULT_CFG.items():
        if k not in cfg:
            cfg[k] = v

    # Sensor-Defaults
    if "sensors" not in cfg:
        cfg["sensors"] = DEFAULT_CFG["sensors"]
    else:
        for lbl, sv in DEFAULT_CFG["sensors"].items():
            if lbl not in cfg["sensors"]:
                cfg["sensors"][lbl] = sv
            else:
                for sk, svv in sv.items():
                    if sk not in cfg["sensors"][lbl]:
                        cfg["sensors"][lbl][sk] = svv

    return cfg

def save_config(new_cfg):
    try:
        with open("config.json", "w") as f:
            json.dump(new_cfg, f)
        print("✓ Konfiguration gespeichert.")
    except Exception as e:
        print("✗ Fehler beim Speichern:", e)

cfg = load_config()

# -------------------------------------------------------
# Globale Variablen für Screensaver
# -------------------------------------------------------

display_on = True
last_activity_ms = time.ticks_ms()

# -------------------------------------------------------
# Hardware: LED & I2C
# -------------------------------------------------------

# Onboard-LED (GPIO 8, Low-active)
led = Pin(8, Pin.OUT)

def set_led(on):
    led.value(0 if on else 1)  # 0 = an, 1 = aus

# GPIO-Ausgänge für Trigger (A/B/C)
GPIO_PINS = {
    "A": Pin(3, Pin.OUT),
    "B": Pin(4, Pin.OUT),
    "C": Pin(7, Pin.OUT),
}

# Startzustand: alles aus
for p in GPIO_PINS.values():
    p.value(0)

# OLED an I2C
try:
    i2c = I2C(0, scl=Pin(6), sda=Pin(5), freq=400000)
    oled = SSD1306(i2c)
    oled.flip()  # Falls Display über Kopf steht
    oled.fill(0)
    oled.text("Booting...", 0, 0)
    oled.show()
except Exception as e:
    print("✗ I2C/OLED Init Error:", e)
    oled = None

# -------------------------------------------------------
# Interrupt Handler für BOOT-Button (Wake)
# -------------------------------------------------------

def handle_wake_irq(pin):
    global display_on, last_activity_ms

    last_activity_ms = time.ticks_ms()

    if not display_on:
        display_on = True
        set_led(True)
        print("🔔 Wake: Display EIN")

        # Display sofort aktualisieren (Platzhalter)
        if oled:
            try:
                oled.fill(0)
                oled.text("-THERMO-", 0, 0)
                oled.text("A: --", 0, 12)
                oled.text("B: --", 0, 22)
                oled.text("C: --", 0, 32)
                oled.show()
            except Exception as e:
                print("⚠️ Display IRQ Error:", e)

try:
    wake_button = Pin(9, Pin.IN, Pin.PULL_UP)
    wake_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_wake_irq)
except Exception as e:
    print("✗ Button Init Error:", e)
    wake_button = None

# -------------------------------------------------------
# DS18B20 Initialisierung
# -------------------------------------------------------

print("\n--- Initialisiere Sensoren ---")

sensor1 = DS18x20(pin=0, resolution=cfg["resolution"], name="Sensor_A")
sensor2 = DS18x20(pin=1, resolution=cfg["resolution"], name="Sensor_B")
sensor3 = DS18x20(pin=2, resolution=cfg["resolution"], name="Sensor_C")

sensors = [sensor1, sensor2, sensor3]
SENSOR_LABELS = ["A", "B", "C"]

# ROM-Adressen sammeln
roms = []
for sensor in sensors:
    try:
        rom = sensor.roms[0] if sensor.init() and sensor.roms else None
        roms.append(rom)
    except Exception as e:
        print(f"✗ Fehler bei Sensor Init {sensor.name}: {e}")
        roms.append(None)

# ROM-Infos für Webserver (Familie + Serial)
rom_info = []
for rom in roms:
    if rom:
        family = rom[0]
        serial_hex = "".join("{:02X}".format(b) for b in rom)
        rom_info.append({
            "family": f"0x{family:02X}",
            "serial": serial_hex,
        })
    else:
        rom_info.append(None)

print("--- Sensoren initialisiert ---\n")

if oled:
    oled.fill(0)
    oled.text("-SENSORS-", 0, 0)
    y = 12
    for i, rom in enumerate(roms):
        label = SENSOR_LABELS[i]
        if rom:
            ser = "".join("{:02X}".format(b) for b in rom)
            oled.text(f"{label}:{ser[-6:]}", 0, y)
        else:
            oled.text(f"{label}: --", 0, y)
        y += 10
    oled.show()
    time.sleep(3)

# -------------------------------------------------------
# Temperatur lesen (Helper)
# -------------------------------------------------------

def read_temps():
    """Liest aktuelle Temperaturen von allen Sensoren"""
    temps = []
    for sensor in sensors:
        val = None
        try:
            res = sensor.read()
            if isinstance(res, list) and res:
                val = res[0]
            elif isinstance(res, (float, int)):
                val = res
        except:
            pass
        temps.append(val)
    return temps

def get_sensor_cfg(idx):
    """Holt Konfiguration für einen Sensor"""
    label = SENSOR_LABELS[idx]
    return cfg["sensors"].get(label, {"enabled": True})

# -------------------------------------------------------
# Trigger-Logik für GPIO-Ausgänge
# -------------------------------------------------------

def update_trigger_outputs(temps):
    """
    Setzt GPIO 3 (A), 4 (B), 7 (C) abhängig von Temperatur und invert_logic.
    """
    for i, t in enumerate(temps):
        label = SENSOR_LABELS[i]
        scfg = get_sensor_cfg(i)
        pin = GPIO_PINS[label]

        if not scfg.get("enabled", True) or t is None:
            # Sensor aus oder keine Messung -> Ausgang LOW
            pin.value(0)
            continue

        low = scfg.get("low_trigger", 18.0)
        high = scfg.get("high_trigger", 25.0)
        invert = scfg.get("invert_logic", False)

        # Grundlogik (nicht invertiert):
        # t < low       -> HIGH
        # low <= t <= high -> HIGH
        # t > high      -> LOW
        if t > high:
            out = 0
        else:
            out = 1

        # Invertieren falls gewünscht
        if invert:
            out = 1 - out

        pin.value(out)

# -------------------------------------------------------
# Webserver Thread
# -------------------------------------------------------

def webserver_thread():
    try:
        webserver.start_webserver(
            roms=roms, cfg=cfg, save_cb=save_config, get_temps=read_temps, rom_info=rom_info
        )
    except Exception as e:
        print("✗ Webserver Crash:", e)

try:
    _thread.start_new_thread(webserver_thread, ())
    print("✓ Webserver Thread gestartet.")
except Exception as e:
    print("✗ Thread konnte nicht starten:", e)

# -------------------------------------------------------
# Screensaver Check
# -------------------------------------------------------

def check_screensaver():
    global display_on

    if not display_on:
        return

    timeout_ms = cfg.get("display_timeout_s", 60) * 1000

    if timeout_ms <= 0:
        return

    if time.ticks_diff(time.ticks_ms(), last_activity_ms) > timeout_ms:
        display_on = False
        if oled:
            oled.fill(0)
            oled.show()
        set_led(False)
        print("📴 Screensaver: Display OFF")

# -------------------------------------------------------
# HAUPTSCHLEIFE
# -------------------------------------------------------

update_count = 0
last_read_ms = time.ticks_ms()
temps = [None, None, None]

print("🚀 Starte Hauptschleife...\n")

while True:
    try:
        # 1. Screensaver
        check_screensaver()

        # 2. Temps messen (Intervall-Check)
        current_ms = time.ticks_ms()
        measure_interval_ms = cfg.get("measure_interval_s", 2) * 1000
        
        if time.ticks_diff(current_ms, last_read_ms) >= measure_interval_ms:
            temps = read_temps()
            last_read_ms = current_ms
            
            # 3. Trigger-GPIOs aktualisieren
            update_trigger_outputs(temps)
            
            # 4. Logger
            v1 = temps[0] if temps[0] is not None else None
            v2 = temps[1] if temps[1] is not None else None
            v3 = temps[2] if temps[2] is not None else None
            logger.add_entry(v1, v2, v3)
            update_count += 1
            
            # 5. Print
            a_str = f"{v1:.3f}" if v1 is not None else "None"
            b_str = f"{v2:.3f}" if v2 is not None else "None"
            c_str = f"{v3:.3f}" if v3 is not None else "None"
            print(f"[{update_count}] A:{a_str}° B:{b_str}° C:{c_str}°")

        # 6. OLED Anzeige (unabhängig vom Messintervall)
        if display_on and oled:
            oled.fill(0)
            oled.text("-THERMO-", 0, 0)
            y_pos = 12
            for i, t in enumerate(temps):
                lbl = SENSOR_LABELS[i]
                scfg = get_sensor_cfg(i)

                if not scfg.get("enabled", True) or t is None:
                    oled.text(f"{lbl}: --", 0, y_pos)
                    y_pos += 10
                else:
                    low = scfg.get("low_trigger", 18.0)
                    high = scfg.get("high_trigger", 25.0)

                    temp_str = "{:6.3f}".format(t)
                    status_str = ""

                    if t < low:
                        status_str = "_" + temp_str  # LOW
                    elif t > high:
                        status_str = temp_str + "_"  # HIGH
                    else:
                        status_str = temp_str       # Normal

                    oled.text(f"{lbl}:{status_str}", 0, y_pos)
                    y_pos += 10

            oled.show()
            set_led(True)

        # 7. Kurzer Sleep für Responsiveness
        time.sleep_ms(100)

    except KeyboardInterrupt:
        print("\n⏹️ Benutzer-Stopp")
        break
    except Exception as e:
        print(f"❌ Main Loop Error: {e}")
        time.sleep(5)
