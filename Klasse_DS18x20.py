"""
Klasse_DS18x20_FIXED.py - KORRIGIERT
DS18B20/DS18S20/DS1822 Temperatur Sensor (One-Wire)
Kompatibel mit: DS18B20 (0x28), DS18S20 (0x10), DS1822 (0x22)

FIX: Dezimalstellen-Auflösung korrekt einstellen
  + Serielle Nummer und Family ID in Ausgabe
"""

import machine
import time
import onewire
import ds18x20


class DS18x20:
    """DS18x20 Familie - Temperatur Sensoren - KORRIGIERT"""
    
    RESOLUTION_MAP = {
        9: (b'\x00\x00\x1f', 94),
        10: (b'\x00\x00\x3f', 188),
        11: (b'\x00\x00\x5f', 375),
        12: (b'\x00\x00\x7f', 750)
    }
    
    RESOLUTION_DECIMALS = {
        9: 1,    # 0.5°C   → 1 Dezimal
        10: 2,   # 0.25°C  → 2 Dezimal
        11: 3,   # 0.125°C → 3 Dezimal
        12: 4    # 0.0625°C → 4 Dezimal
    }
    
    SENSOR_TYPES = {
        0x28: "DS18B20",
        0x10: "DS18S20",
        0x22: "DS1822"
    }
    
    def __init__(self, pin=2, resolution=12, name="DS18x20"):
        self.pin = machine.Pin(pin)
        self.ow = onewire.OneWire(self.pin)
        self.ds = ds18x20.DS18X20(self.ow)
        self.roms = []
        self.resolution = resolution if resolution in [9, 10, 11, 12] else 12
        self.conversion_time_ms = self.RESOLUTION_MAP[self.resolution][1]
        self.name = name
        self.initialized = False
        self.last_read = None
    
    def init(self):
        """Scannt Bus und initialisiert Sensoren"""
        try:
            self.roms = self.ds.scan()
            
            if not self.roms:
                print(f"✗ {self.name}: Keine Sensoren gefunden")
                return False
            
            print(f"✓ {self.name} initialisiert - {len(self.roms)} Sensor(e) gefunden")
            
            for i, rom in enumerate(self.roms):
                family_code = rom[0]
                sensor_type = self.SENSOR_TYPES.get(family_code, f"Unknown(0x{family_code:02x})")
                serial_hex = ''.join(f'{b:02x}' for b in rom)
                print(f"  [{i}] {sensor_type} - Serial: {serial_hex} - Family ID: 0x{family_code:02x}")
            
            decimals = self.RESOLUTION_DECIMALS[self.resolution]
            print(f"  Auflösung: {self.resolution}-bit ({self.conversion_time_ms}ms, {decimals} Dezimalstellen)")
            
            if self.resolution != 12:
                scratch_data = self.RESOLUTION_MAP[self.resolution][0]
                for rom in self.roms:
                    try:
                        self.ds.write_scratch(rom, scratch_data)
                    except:
                        pass
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"✗ {self.name} Init-Fehler: {e}")
            return False
    
    def read(self):
        """Liest alle Sensoren mit KORREKTER Dezimalstellen-Auflösung"""
        if not self.initialized or not self.roms:
            return None
        
        try:
            self.ds.convert_temp()
            time.sleep_ms(self.conversion_time_ms)
            
            temps = []
            decimals = self.RESOLUTION_DECIMALS.get(self.resolution, 2)
            
            for rom in self.roms:
                temp = self.ds.read_temp(rom)
                temps.append(round(temp, decimals))
            
            self.last_read = temps
            return temps
        except Exception as e:
            print(f"{self.name} Lesefehler: {e}")
            return None
    
    def get_data(self):
        """Gibt letzte Messung zurück"""
        return self.last_read
    
    def to_dict(self):
        """Konvertiert zu Dictionary für Ausgabe"""
        temps = self.read()
        if temps:
            if len(temps) == 1:
                rom = self.roms[0]
                family_code = rom[0]
                serial_hex = ''.join(f'{b:02x}' for b in rom)
                return {
                    "sensor": self.name,
                    "type": "DS18x20",
                    "temperature_C": temps[0],
                    "resolution_bits": self.resolution,
                    "resolution_decimals": self.RESOLUTION_DECIMALS[self.resolution],
                    "serial": serial_hex,
                    "family_id": f"0x{family_code:02x}"
                }
            else:
                sensors = []
                for i, rom in enumerate(self.roms):
                    family_code = rom[0]
                    serial_hex = ''.join(f'{b:02x}' for b in rom)
                    sensors.append({
                        "index": i,
                        "temperature_C": temps[i],
                        "serial": serial_hex,
                        "family_id": f"0x{family_code:02x}"
                    })
                return {
                    "sensor": self.name,
                    "type": "DS18x20",
                    "resolution_bits": self.resolution,
                    "resolution_decimals": self.RESOLUTION_DECIMALS[self.resolution],
                    "sensors": sensors
                }
        return None
