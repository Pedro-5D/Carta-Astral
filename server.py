import json
import sys
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_compress import Compress
from flask_caching import Cache
from datetime import datetime, timezone, timedelta
from skyfield.api import load, wgs84
from math import sin, cos, tan, atan, atan2, radians, degrees
import xml.etree.ElementTree as ET
import numpy as np
import os
from pathlib import Path
from functools import lru_cache
import requests
import urllib.request
import ssl
import csv

app = Flask(__name__)
# Configurar CORS correctamente
CORS(app, resources={r"/*": {"origins": "*"}})
# Comprimir respuestas
Compress(app)
# Configurar caché
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Variables globales para recursos precargados
eph = None
ts = None
interpreter = None
time_zone_df = None
common_cities = {}

API_KEY = "e19afa2a9d6643ea9550aab89eefce0b"

# Precarga de recursos al inicio
def preload_resources():
    global eph, ts, interpreter, time_zone_df, common_cities
    
    print("Precargando recursos...")
    
    # Cargar efemérides desde GitHub
    try:
        # Cargar desde archivo local
        eph_path = Path('de421.bsp')
        if not eph_path.exists():
            # Intentar cargar desde la carpeta docs
            eph_path = Path('docs') / 'de421.bsp'
        
        print(f"Cargando efemérides desde: {eph_path}")
        eph = load(str(eph_path))
    except Exception as e:
        print(f"Error cargando efemérides: {e}")
        # Intento alternativo
        try:
            print("Intentando cargar efemérides alternativas...")
            eph = load('de440s.bsp')
        except Exception as e2:
            print(f"Error en carga alternativa: {e2}")
            sys.exit(1)  # Salir si no se pueden cargar las efemérides
    
    ts = load.timescale()
    
    # Cargar zona horaria desde CSV
    try:
        time_zone_df = []
        with open('time_zone.csv', 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if len(row) >= 6:  # asegurarse de que hay suficientes columnas
                    time_zone_df.append({
                        'timezone': row[0],
                        'country_code': row[1],
                        'abbreviation': row[2],
                        'timestamp': int(row[3]) if row[3].isdigit() else 0,
                        'utc_offset': float(row[4]) if row[4].replace('.', '', 1).isdigit() else 0,
                        'dst': int(row[5]) if row[5].isdigit() else 0
                    })
        print(f"Cargado archivo de zonas horarias: {len(time_zone_df)} entradas")
    except Exception as e:
        print(f"Error cargando zonas horarias: {e}")
        time_zone_df = []
    
    # Cargar intérprete con XML
    try:
        interpreter = AstrologicalInterpreter()
        print("Intérprete astrológico cargado")
    except Exception as e:
        print(f"Error cargando intérprete: {e}")
        interpreter = None
    
    # Cargar datos de ciudades comunes
    try:
        # Precargar algunas ciudades populares
        cities = ["Madrid", "Barcelona", "Buenos Aires", "Mexico City", "New York", "Paris", "London"]
        for city in cities:
            result = obtener_datos_ciudad(city, "", "")
            if isinstance(result, list) and len(result) > 0:
                common_cities[city.lower()] = result[0]
    except Exception as e:
        print(f"Error precargando ciudades: {e}")
    
    print("Recursos precargados correctamente")

class AstrologicalInterpreter:
    def __init__(self, xml_path='interpretations.xml'):
        try:
            self.tree = ET.parse(xml_path)
            self.root = self.tree.getroot()
            print("XML de interpretaciones cargado correctamente")
        except Exception as e:
            print(f"Error al cargar el archivo XML: {e}")
            # No lanzar excepción, solo reportar el error
            self.root = None

    def get_planet_in_sign(self, planet, sign):
        try:
            if not self.root:
                return None
                
            xpath = f".//PLANET_IN_SIGN14/{planet}/{sign}"
            planet_element = self.root.find(xpath)
            
            if planet_element is not None:
                full_text = planet_element.text.strip() if planet_element.text else ""
                physical_desc = ""
                astral_desc = ""
                
                split_text = full_text.split("En el plano Astral", 1)
                
                if len(split_text) > 0:
                    physical_desc = split_text[0].strip()
                if len(split_text) > 1:
                    astral_desc = "En el plano Astral" + split_text[1].strip()
                
                return {
                    "physical": physical_desc,
                    "astral": astral_desc
                }
            return None
        except Exception as e:
            print(f"Error en get_planet_in_sign: {e}")
            return None

    def get_planet_in_house(self, planet, house):
        try:
            if not self.root:
                return None
                
            house_str = f"HS{house}"
            xpath = f".//PLANET_IN_12HOUSE/{planet}/{house_str}"
            house_element = self.root.find(xpath)
            
            if house_element is not None and house_element.text:
                return house_element.text.strip()
            return None
        except Exception as e:
            print(f"Error en get_planet_in_house: {e}")
            return None

    def get_aspect_interpretation(self, planet1, planet2, aspect_type):
        try:
            if not self.root:
                return None
                
            aspect_angles = {
                "Armónico Relevante": ["0", "60", "120", "180"],
                "Inarmónico Relevante": ["90", "150"],
                "Armónico": ["12", "24", "36", "48", "72", "84", "96", "108", "132", "144", "156", "168"],
                "Inarmónico": ["6", "18", "42", "54", "66", "78", "102", "114", "126", "138", "162", "174"]
            }
            
            for angles in aspect_angles[aspect_type]:
                xpath = f".//PLANET_IN_ASPECT/{planet1}/{planet2}/ASP_{angles}"
                aspect_element = self.root.find(xpath)
                
                if aspect_element is not None and aspect_element.text:
                    return aspect_element.text.strip()
                
                xpath = f".//PLANET_IN_ASPECT/{planet2}/{planet1}/ASP_{angles}"
                aspect_element = self.root.find(xpath)
                
                if aspect_element is not None and aspect_element.text:
                    return aspect_element.text.strip()
            
            return None
        except Exception as e:
            print(f"Error en get_aspect_interpretation: {e}")
            return None

    def get_house_ruler_interpretation(self, ruler_house, house_position):
        try:
            if not self.root:
                return None
                
            xpath = f".//HRULER_IN_HOUSE/RH{ruler_house}/HS{house_position}"
            ruler_element = self.root.find(xpath)
            
            if ruler_element is not None and ruler_element.text:
                return ruler_element.text.strip()
            return None
        except Exception as e:
            print(f"Error en get_house_ruler_interpretation: {e}")
            return None

# Cachear obtención de datos de ciudad
@lru_cache(maxsize=100)
def obtener_datos_ciudad(ciudad, fecha, hora):
    # Verificar si está en ciudades comunes
    if ciudad.lower() in common_cities:
        return common_cities[ciudad.lower()]
        
    url = f"https://api.geoapify.com/v1/geocode/search?text={ciudad}&apiKey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)  # Timeout para evitar demoras
        if response.status_code == 200:
            datos = response.json()
            if datos.get("features"):
                opciones = [{
                    "nombre": resultado["properties"]["formatted"],
                    "lat": resultado["properties"]["lat"],
                    "lon": resultado["properties"]["lon"],
                    "pais": resultado["properties"].get("country", "")
                }
                for resultado in datos["features"]]
                return opciones
            return {"error": "Ciudad no encontrada"}
        return {"error": f"Error en la consulta: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "Timeout en la consulta"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def obtener_zona_horaria(coordenadas, fecha):
    """
    Obtiene la zona horaria usando el archivo time_zone.csv y ajusta para horario de verano/invierno
    basado en las coordenadas y la fecha, considerando hemisferio norte/sur
    """
    try:
        lat = coordenadas["lat"]
        lon = coordenadas["lon"]
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        
        # Determinar hemisferio (norte o sur)
        hemisferio = "norte" if lat >= 0 else "sur"
        
        # Verificar si la fecha está en horario de verano
        # Hemisferio Norte: DST generalmente entre marzo y octubre
        # Hemisferio Sur: DST generalmente entre octubre y marzo
        mes = fecha_obj.month
        is_dst = False
        
        if hemisferio == "norte" and 3 <= mes <= 10:
            is_dst = True
        elif hemisferio == "sur" and (mes >= 10 or mes <= 3):
            is_dst = True
            
        # Buscar en el CSV por aproximación de longitud
        # Un grado de longitud es aproximadamente 4 minutos de tiempo (15 grados = 1 hora)
        estimated_offset = round(lon / 15)
        
        # Ajustar para países específicos con información conocida
        pais = coordenadas.get("pais", "").lower()
        abbr = "UTC"
        tz_name = "UTC"
        
        if "spain" in pais or "españa" in pais:
            tz_name = "Europe/Madrid"
            abbr = "CET"
            abbr_dst = "CEST"
            offset = 1
            if is_dst:
                offset = 2
                abbr = abbr_dst
        elif "argentina" in pais:
            tz_name = "America/Argentina/Buenos_Aires"
            abbr = "ART"
            offset = -3
            # Argentina no usa DST actualmente
        elif "mexico" in pais or "méxico" in pais:
            tz_name = "America/Mexico_City"
            abbr = "CST"
            abbr_dst = "CDT"
            offset = -6
            if is_dst:
                offset = -5
                abbr = abbr_dst
        else:
            # Buscar en el CSV la zona más cercana a la longitud estimada
            closest_zone = None
            min_diff = float('inf')
            
            if time_zone_df:
                for zone in time_zone_df:
                    # Los offsets en el CSV están en segundos, convertir a horas
                    csv_offset = zone['utc_offset'] / 3600
                    diff = abs(csv_offset - estimated_offset)
                    
                    if diff < min_diff:
                        min_diff = diff
                        closest_zone = zone
                
                if closest_zone:
                    offset = closest_zone['utc_offset'] / 3600
                    abbr = closest_zone['abbreviation']
                    tz_name = closest_zone['timezone']
                    
                    # Ajustar por DST si corresponde
                    if is_dst and closest_zone['dst'] == 1:
                        offset += 1
            else:
                # Si no hay datos en el CSV, usar la estimación por longitud
                offset = estimated_offset
                abbr = f"GMT{offset:+d}"
                tz_name = f"Estimated/GMT{offset:+d}"
        
        print(f"Zona horaria determinada: {tz_name}, offset: {offset}, DST: {is_dst}")
        
        return {
            "name": tz_name,
            "offset": offset,
            "abbreviation_STD": abbr,
            "abbreviation_DST": abbr,
            "is_dst": is_dst,
            "hemisphere": hemisferio
        }
    
    except Exception as e:
        print(f"Error obteniendo zona horaria: {str(e)}")
        # Si hay un error, devolver un mensaje claro
        print("Error en obtención de zona horaria, usando estimación basada en longitud")
        
        try:
            # Estimar zona horaria basada en longitud
            lon = coordenadas["lon"]
            estimated_offset = round(lon / 15)  # 15 grados = 1 hora
            
            # Para ciudades conocidas, usar valores predeterminados
            pais = coordenadas.get("pais", "").lower()
            
            if "spain" in pais or "españa" in pais:
                estimated_offset = 1
            elif "argentina" in pais:
                estimated_offset = -3
            elif "mexico" in pais or "méxico" in pais:
                estimated_offset = -6
            elif "united states" in pais or "estados unidos" in pais:
                # Aproximación basada en longitud para EEUU
                if lon < -100:
                    estimated_offset = -8  # Pacífico
                elif lon < -90:
                    estimated_offset = -7  # Montaña
                elif lon < -75:
                    estimated_offset = -6  # Central
                else:
                    estimated_offset = -5  # Este
            
            return {
                "name": f"GMT{estimated_offset:+d}",
                "offset": estimated_offset,
                "abbreviation_STD": f"GMT{estimated_offset:+d}",
                "abbreviation_DST": f"GMT{estimated_offset:+d}",
                "is_dst": False,
                "hemisphere": "norte" if coordenadas["lat"] >= 0 else "sur",
                "lon": lon  # Añadir longitud para referencia
            }
        except Exception as inner_e:
            print(f"Error en estimación de zona horaria: {str(inner_e)}")
            # Valor por defecto UTC si todo falla
            return {
                "name": "UTC",
                "offset": 0,
                "abbreviation_STD": "UTC",
                "abbreviation_DST": "UTC",
                "is_dst": False,
                "hemisphere": "norte",
                "estimated": True
            }

def convertir_a_utc(fecha, hora, timezone_info):
    """
    Convierte fecha y hora local a UTC considerando zona horaria y DST
    Para cálculos astrológicos correctos, debemos asegurarnos de que la hora UTC sea precisa
    """
    try:
        # Combinar fecha y hora en un objeto datetime
        fecha_hora_str = f"{fecha} {hora}"
        dt_local = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
        
        # Obtener offset en horas desde la API de zona horaria
        # Si estamos en DST, la API ya incluye ese offset
        offset_hours = timezone_info["offset"]
        
        print(f"Offset de zona horaria: {offset_hours} horas")
        print(f"Hora local ingresada: {dt_local}")
        
        # Crear un timezone con el offset
        tz = timezone(timedelta(hours=offset_hours))
        
        # Aplicar timezone al datetime
        dt_local_with_tz = dt_local.replace(tzinfo=tz)
        
        # Convertir a UTC
        dt_utc = dt_local_with_tz.astimezone(timezone.utc)
        
        print(f"Hora convertida a UTC: {dt_utc}")
        return dt_utc
    except Exception as e:
        print(f"Error en conversión a UTC: {str(e)}")
        # Si falla, usar la hora proporcionada con offset manual aproximado
        dt_local = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        
        # Intentar estimar offset basado en longitud si no tenemos zona horaria
        if "lon" in timezone_info:
            lon = timezone_info["lon"]
            est_offset = round(lon / 15)  # 15 grados = 1 hora
            est_tz = timezone(timedelta(hours=est_offset))
            dt_with_tz = dt_local.replace(tzinfo=est_tz)
            return dt_with_tz.astimezone(timezone.utc)
        
        # Fallback: asumir UTC
        return dt_local.replace(tzinfo=timezone.utc)

def calculate_positions_with_utc(utc_datetime, lat=None, lon=None):
    """
    Calcula posiciones planetarias con un datetime UTC
    Asegura que el tiempo se ajusta correctamente según la zona horaria
    """
    try:
        # Usar el datetime UTC directamente
        print(f"Calculando posiciones para UTC: {utc_datetime}")
        t = ts.from_datetime(utc_datetime)
        earth = eph['earth']
        
        positions = []
        bodies = {
            'SOL': eph['sun'],
            'LUNA': eph['moon'],
            'MERCURIO': eph['mercury'],
            'VENUS': eph['venus'],
            'MARTE': eph['mars'],
            'JÚPITER': eph['jupiter barycenter'],
            'SATURNO': eph['saturn barycenter'],
            'URANO': eph['uranus barycenter'],
            'NEPTUNO': eph['neptune barycenter'],
            'PLUTÓN': eph['pluto barycenter']
        }
        
        for body_name, body in bodies.items():
            pos = earth.at(t).observe(body).apparent()
            lat_ecl, lon_ecl, dist = pos.ecliptic_latlon(epoch='date')
            
            longitude = float(lon_ecl.degrees) % 360
            positions.append({
                "name": body_name,
                "longitude": longitude,
                "sign": get_sign(longitude)
            })
        
        if lat is not None and lon is not None:
            asc, mc = calculate_asc_mc(t, lat, lon)
            
            positions.append({
                "name": "ASC",
                "longitude": float(asc),
                "sign": get_sign(asc)
            })
            
            positions.append({
                "name": "MC",
                "longitude": float(mc),
                "sign": get_sign(mc)
            })
        
        return positions
    except Exception as e:
        print(f"Error calculando posiciones: {str(e)}")
        # No lanzar excepción, simplemente retornar un error formateado
        print("Usando método alternativo de cálculo")
        try:
            return calculate_positions(
                utc_datetime.strftime("%d/%m/%Y"),
                utc_datetime.strftime("%H:%M"),
                lat,
                lon
            )
        except Exception as inner_e:
            print(f"Error en método alternativo: {str(inner_e)}")
            return []

def calculate_positions(date_str, time_str, lat=None, lon=None):
    try:
        if '-' in date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_str = date_obj.strftime("%d/%m/%Y")
            
        local_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
        spain_tz = timezone(timedelta(hours=1))
        local_dt = local_dt.replace(tzinfo=spain_tz)
        utc_dt = local_dt.astimezone(timezone.utc)
        
        t = ts.from_datetime(utc_dt)
        earth = eph['earth']
        
        positions = []
        bodies = {
            'SOL': eph['sun'],
            'LUNA': eph['moon'],
            'MERCURIO': eph['mercury'],
            'VENUS': eph['venus'],
            'MARTE': eph['mars'],
            'JÚPITER': eph['jupiter barycenter'],
            'SATURNO': eph['saturn barycenter'],
            'URANO': eph['uranus barycenter'],
            'NEPTUNO': eph['neptune barycenter'],
            'PLUTÓN': eph['pluto barycenter']
        }
        
        for body_name, body in bodies.items():
            pos = earth.at(t).observe(body).apparent()
            lat_ecl, lon_ecl, dist = pos.ecliptic_latlon(epoch='date')
            
            longitude = float(lon_ecl.degrees) % 360
            positions.append({
                "name": body_name,
                "longitude": longitude,
                "sign": get_sign(longitude)
            })
        
        if lat is not None and lon is not None:
            asc, mc = calculate_asc_mc(t, lat, lon)
            
            positions.append({
                "name": "ASC",
                "longitude": float(asc),
                "sign": get_sign(asc)
            })
            
            positions.append({
                "name": "MC",
                "longitude": float(mc),
                "sign": get_sign(mc)
            })
        
        return positions
    except Exception as e:
        print(f"Error calculando posiciones: {str(e)}")
        return []

def calculate_asc_mc(t, lat, lon):
    try:
        gst = t.gast
        lst = (gst * 15 + lon) % 360
        mc = lst % 360
        
        lat_rad = np.radians(lat)
        ra_rad = np.radians(lst)
        eps_rad = np.radians(23.4367)
        
        tan_asc = np.cos(ra_rad) / (np.sin(ra_rad) * np.cos(eps_rad) + np.tan(lat_rad) * np.sin(eps_rad))
        asc = np.degrees(np.arctan(-tan_asc))
        
        if 0 <= lst <= 180:
            if np.cos(ra_rad) > 0:
                asc = (asc + 180) % 360
        else:
            if np.cos(ra_rad) < 0:
                asc = (asc + 180) % 360
                
        asc = asc % 360
        
        dist_mc_asc = (asc - mc) % 360
        if dist_mc_asc > 180:
            asc = (asc + 180) % 360
        
        return asc, mc
    except Exception as e:
        print(f"Error en calculate_asc_mc: {str(e)}")
        # Valores por defecto en caso de error
        return 0, 0

def get_sign(longitude):
    longitude = float(longitude) % 360
    signs = [
        ("ARIES", 354.00, 36.00),
        ("TAURO", 30.00, 30.00),
        ("GÉMINIS", 60.00, 30.00),
        ("CÁNCER", 90.00, 30.00),
        ("LEO", 120.00, 30.00),
        ("VIRGO", 150.00, 36.00),
        ("LIBRA", 186.00, 24.00),
        ("ESCORPIO", 210.00, 30.00),
        ("OFIUCO", 240.00, 12.00),
        ("SAGITARIO", 252.00, 18.00),
        ("CAPRICORNIO", 270.00, 36.00),
        ("ACUARIO", 306.00, 18.00),
        ("PEGASO", 324.00, 6.00),
        ("PISCIS", 330.00, 24.00)
    ]
    
    for name, start, length in signs:
        end = start + length
        if start <= longitude < end:
            return name
        elif start > 354.00 and (longitude >= start or longitude < (end % 360)):
            # Caso especial para Aries que cruza 0°
            return name
    
    return "ARIES"  # Valor por defecto

def calculate_positions_aspects(positions):
    aspects = []
    traditional_planets = ["SOL", "LUNA", "MERCURIO", "VENUS", "MARTE", "JÚPITER", "SATURNO"]
    
    def calculate_angle(pos1, pos2):
        diff = abs(pos1 - pos2) % 360
        if diff > 180:
            diff = 360 - diff
        return diff
    
    def determine_aspect_type(angle):
        orb = 2
        
        if (abs(angle) <= orb or 
            abs(angle - 60) <= orb or 
            abs(angle - 120) <= orb or
            abs(angle - 180) <= orb):
            return "Armónico Relevante"
        elif (abs(angle - 30) <= orb or
              abs(angle - 90) <= orb or
              abs(angle - 150) <= orb):
            return "Inarmónico Relevante"
        elif any(abs(angle - a) <= orb for a in [12, 24, 36, 48, 72, 84, 96, 108, 132, 144, 156, 168]):
            return "Armónico"
        elif any(abs(angle - a) <= orb for a in [6, 18, 42, 54, 66, 78, 102, 114, 126, 138, 162, 174]):
            return "Inarmónico"
            
        return None

    asc_position = next((p for p in positions if p["name"] == "ASC"), None)
    
    for i, pos1 in enumerate(positions):
        if pos1["name"] not in traditional_planets:
            continue
            
        for pos2 in positions[i+1:]:
            if pos2["name"] not in traditional_planets:
                continue
                
            angle = calculate_angle(pos1["longitude"], pos2["longitude"])
            aspect_type = determine_aspect_type(angle)
            
            if aspect_type:
                aspect = f"{pos1['name']} {aspect_type} {pos2['name']} ({angle:.2f}°)"
                aspects.append(aspect)
        
        # Aspectos con el ASC
        if asc_position:
            angle = calculate_angle(pos1["longitude"], asc_position["longitude"])
            aspect_type = determine_aspect_type(angle)
            
            if aspect_type:
                aspect = f"{pos1['name']} {aspect_type} ASC ({angle:.2f}°)"
                aspects.append(aspect)
    
    return aspects

def is_dry_birth(positions):
    """
    Determina si un nacimiento es seco basado en la posición del Sol.
    Es seco cuando el Sol está entre las casas 6 y 11 (inclusive).
    """
    sun_pos = next((p for p in positions if p["name"] == "SOL"), None)
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not sun_pos or not asc_pos:
        return False  # Valor predeterminado
    
    # Calcular la casa del Sol relativa al Ascendente
    diff = (sun_pos["longitude"] - asc_pos["longitude"]) % 360
    house = (diff // 30) + 1
    
    # Es seco si el Sol está en las casas 6 a 11
    return 6 <= house <= 11

def calculate_dignity(planet_name, longitude):
    total_points = 0
    sign = get_sign(longitude)
    
    dignities = {
        "SOL": {
            "caida": ["ACUARIO", "OFIUCO", "LIBRA", "PISCIS", "CÁNCER"],
            "exaltacion": ["LEO", "ARIES", "CAPRICORNIO", "VIRGO", "ESCORPIO"],
            "domicilio": ["PEGASO", "GÉMINIS"],
            "exilio": ["SAGITARIO", "TAURO"]
        },
        "LUNA": {
            "caida": ["LEO", "ARIES", "VIRGO", "CAPRICORNIO"],
            "exaltacion": ["ACUARIO", "OFIUCO", "LIBRA", "PISCIS", "CÁNCER", "TAURO"],
            "domicilio": ["SAGITARIO"],
            "exilio": ["GÉMINIS", "ESCORPIO", "PEGASO"]
        },
        "MERCURIO": {
            "caida": ["ACUARIO", "OFIUCO", "LIBRA", "TAURO"],
            "exaltacion": ["GÉMINIS", "CAPRICORNIO", "VIRGO"],
            "domicilio": ["LEO", "ARIES", "ESCORPIO", "PEGASO"],
            "exilio": ["PISCIS", "CÁNCER", "SAGITARIO"]
        },
        "VENUS": {
            "caida": ["CAPRICORNIO", "VIRGO", "GÉMINIS"],
            "exaltacion": ["TAURO", "ACUARIO", "OFIUCO", "LIBRA"],
            "domicilio": ["PISCIS", "CÁNCER", "SAGITARIO"],
            "exilio": ["LEO", "ARIES", "ESCORPIO", "PEGASO"]
        },
        "MARTE": {
            "caida": ["PISCIS", "CÁNCER", "SAGITARIO"],
            "exaltacion": ["LEO", "ARIES", "ESCORPIO", "PEGASO"],
            "domicilio": ["CAPRICORNIO", "VIRGO", "GÉMINIS"],
            "exilio": ["ACUARIO", "OFIUCO", "LIBRA", "TAURO"]
        },
        "JÚPITER": {
            "caida": ["LEO", "ARIES", "ESCORPIO"],
            "exaltacion": ["PISCIS", "CÁNCER", "SAGITARIO", "PEGASO"],
            "domicilio": ["ACUARIO", "OFIUCO", "LIBRA", "TAURO"],
            "exilio": ["CAPRICORNIO", "VIRGO", "GÉMINIS"]
        },
        "SATURNO": {
            "caida": ["TAURO", "ESCORPIO", "PEGASO"],
            "exaltacion": ["SAGITARIO", "OFIUCO", "GÉMINIS"],
            "domicilio": ["ACUARIO", "LIBRA", "ARIES", "LEO"],
            "exilio": ["CAPRICORNIO", "VIRGO", "PISCIS", "CÁNCER"]
        }
    }

    if planet_name in dignities:
        if sign in dignities[planet_name]["exaltacion"]:
            total_points += 6
        if sign in dignities[planet_name]["domicilio"]:
            total_points += 3
        if sign in dignities[planet_name]["caida"]:
            total_points += 0
        if sign in dignities[planet_name]["exilio"]:
            total_points += 3
            
    return total_points

def is_angular(longitude):
    specific_degrees = [354.00, 30.00, 60.00, 90.00, 120.00, 150.00, 186.00, 210.00, 
                       240.00, 252.00, 270.00, 306.00, 324.00, 330.00]
    orb = 1.00
    degree_in_sign = float(longitude) % 360
    
    for degree in specific_degrees:
        if abs(degree_in_sign - degree) <= orb:
            return 6
            
    return 0

def get_house_number(longitude, asc_longitude):
    """Calcula la casa desde el Ascendente."""
    diff = (longitude - asc_longitude) % 360
    house = 1 + (int(diff / 30))
    if house > 12:
        house = house - 12
    return house

def calculate_planet_aspects(planet_name, aspects_list):
    """
    Suma los puntos de los aspectos ya calculados para el planeta.
    """
    total = 0
    for aspect in aspects_list:
        if planet_name in aspect:  # Si el aspecto es de este planeta
            if "Armónico Relevante" in aspect:
                total += 6
            elif "Inarmónico Relevante" in aspect:
                total += -6
            elif "Armónico" in aspect:
                total += 1
            elif "Inarmónico" in aspect:
                total += -1
    return total

def calculate_dignity_table(positions, aspects_list):
    table = []
    total_points = 0
    
    houses_rulers = {
        "SOL": [1, 5, 9],
        "LUNA": [2, 6, 10, 4, 8, 12],
        "MERCURIO": [2, 6, 10, 3, 7, 11],
        "VENUS": [2, 6, 10],
        "MARTE": [1, 5, 9, 4, 8, 12],
        "JÚPITER": [3, 7, 11, 4, 8, 12],
        "SATURNO": [1, 5, 9, 3, 7, 11]
    }
    
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not asc_pos:
        return {"tabla": [], "total_general": 0}
    
    for position in positions:
        if position["name"] in houses_rulers:
            house_num = get_house_number(position["longitude"], asc_pos["longitude"])
            
            dignity_points = calculate_dignity(position["name"], position["longitude"])
            angular_points = is_angular(position["longitude"]) 
            aspect_points = calculate_planet_aspects(position["name"], aspects_list)
            
            # Calculamos puntos de casa
            house_points = 6 if house_num in houses_rulers[position["name"]] else 0
            
            planet_total = dignity_points + angular_points + aspect_points + house_points
            total_points += planet_total
            
            table.append({
                "planeta": position["name"],
                "signo": position["sign"],
                "casa": house_num,
                "puntos_dignidad": dignity_points,
                "puntos_angular": angular_points,
                "puntos_aspectos": aspect_points,
                "total_planeta": planet_total
            })
    
    return {
        "tabla": table,
        "total_general": total_points
    }

SIGNS_BY_ELEMENT = {
    "AIRE": ["GÉMINIS", "ACUARIO", "OFIUCO", "LIBRA"],
    "TIERRA": ["TAURO", "CAPRICORNIO", "VIRGO"],
    "AGUA": ["ESCORPIO", "CÁNCER", "PISCIS", "PEGASO"],
    "FUEGO": ["ARIES", "LEO", "SAGITARIO"]
}

ELEMENT_BY_SIGN = {sign: element for element, signs in SIGNS_BY_ELEMENT.items() for sign in signs}

TRIPLICITIES = {
    "AIRE": {
        "humedo": "MERCURIO",    # Regente de Géminis
        "seco": "SATURNO",       # Regente de Ofiuco
        "participativo": "JÚPITER"  # Regente de Pegaso
    },
    "TIERRA": {
        "humedo": "VENUS",        # Regente de Tauro
        "seco": "MERCURIO",         # Regente de Virgo
        "participativo": "LUNA"  # Regente de Libra
    },
    "FUEGO": {
        "humedo": "SOL",         # Regente de Leo
        "seco": "SATURNO",       # Regente de Ofiuco
        "participativo": "MARTE"    # Regente de Aries
    },
    "AGUA": {
        "humedo": "LUNA",     # Regente de Cáncer
        "seco": "MARTE",         # Regente de Escorpio
        "participativo": "JÚPITER"     # Regente de Piscis
    }
}

HOUSE_MEANINGS = [
    "ÓRGANO DE LA MENTE",
    "UNE EL OBLETO DEL SUSTENTO CON EL ÓRGANO DE LA INTELIGENCIA",
    "ÓRGANO DEL SUSTENTO / RELACIÓN",
    "INTELIGENCIA",
    "EGO",
    "UNE EL OBJETO DE LA INTELIGENCIA CON EL ÓRGANO DEL SUSTENTO",
    "OBJETO DEL SUSTENTO",
    "ÓRGANO DE LA INTELIGENCIA",
    "OBJETO DE LA MENTE",
    "UNE EL OBJETO DE LA INTELIGENCIA CON EL ÓRGANO DE LA RELACIÓN",
    "OBJETO DE RELACIÓN",
    "OBJETO DE LA INTELIGENCIA"
]

def get_element_for_sign(sign):
    """
    Determina el elemento de un signo zodiacal.
    """
    return ELEMENT_BY_SIGN.get(sign, "FUEGO")  # FUEGO como valor predeterminado

def get_triplicity_rulers_for_sign(sign, is_dry_birth):
    """
    Obtiene los regentes de triplicidad para un signo dado.
    """
    element = get_element_for_sign(sign)
    if not element:
        # Si no se encuentra elemento, usar FUEGO por defecto
        element = "FUEGO"
    
    rulers = TRIPLICITIES[element]
    
    return {
        "regente1": rulers["humedo"],
        "regente2": rulers["seco"],
        "regente3": rulers["participativo"]
    }

def calculate_houses_with_triplicities(positions, is_dry_birth):
    """
    Calcula la tabla de casas con sus triplicidades.
    """
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not asc_pos:
        return []  # Si no hay ascendente, no podemos calcular casas
    
    houses_table = []
    
    for i in range(12):
        # Usar el Ascendente como punto de partida para las casas
        house_cusp = (asc_pos["longitude"] + (i * 30.00)) % 360
        sign = get_sign(house_cusp)
        element = get_element_for_sign(sign)
        triplicity_rulers = get_triplicity_rulers_for_sign(sign, is_dry_birth)
        
        house_data = {
            "house_number": i + 1,
            "element": element,
            "sign": sign,
            "cusp_longitude": f"{house_cusp:.2f}°",
            "meaning": HOUSE_MEANINGS[i],
            "triplicity_rulers": triplicity_rulers
        }
        
        houses_table.append(house_data)
    
    return houses_table

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/cities', methods=['GET'])
def get_cities():
    ciudad = request.args.get("ciudad")
    if not ciudad:
        return jsonify({"error": "Debes proporcionar una ciudad"}), 400

    print(f"Búsqueda recibida para ciudad: {ciudad}")
    
    # API key de Geoapify
    api_key = API_KEY
    
    # Usar la API de Geoapify para autocompletado de ciudades
    url = f"https://api.geoapify.com/v1/geocode/autocomplete?text={ciudad}&apiKey={api_key}&limit=20"
    
    try:
        # Hacer la petición a la API
        response = requests.get(url, timeout=10)
        print(f"Estado de respuesta Geoapify: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error en la API: {response.text}")
            raise Exception(f"Error en la API: {response.status_code}")
            
        data = response.json()
        
        # Mostrar la respuesta completa para depuración
        print(f"Respuesta completa de API: {data}")
        
        # Crear lista de ciudades encontradas
        ciudades = []
        
        # Verificar si hay resultados
        if "features" in data and len(data["features"]) > 0:
            print(f"Número de resultados: {len(data['features'])}")
            
            for feature in data["features"]:
                props = feature["properties"]
                # Formatear el nombre de la ciudad con país
                nombre_ciudad = props.get("formatted", "")
                if nombre_ciudad:
                    print(f"Ciudad encontrada: {nombre_ciudad}")
                    ciudades.append(nombre_ciudad)
        else:
            print("No se encontraron resultados en la API")
        
        # Si no hay resultados, generar algunas opciones
        if not ciudades:
            print("Generando opciones")
            ciudades = [
                f"{ciudad}, España",
                f"{ciudad}, México",
                f"{ciudad}, Argentina",
                f"{ciudad}, Estados Unidos",
                f"{ciudad}, Colombia"
            ]
        
        print(f"Total ciudades a devolver: {len(ciudades)}")
        print(f"Ciudades encontradas: {ciudades}")
        
        return jsonify({"ciudades": ciudades})
        
    except Exception as e:
        print(f"Error en búsqueda de ciudades: {str(e)}")
        # En caso de error, generar algunas opciones
        ciudades = [
            f"{ciudad}, España",
            f"{ciudad}, México",
            f"{ciudad}, Argentina",
            f"{ciudad}, Estados Unidos",
            f"{ciudad}, Colombia"
        ]
        
        return jsonify({"ciudades": ciudades})

@app.route('/calculate', methods=['POST', 'OPTIONS'])
def calculate():
    if request.method == 'OPTIONS':
        # Responder a la solicitud preflight de CORS
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
        
    try:
        data = request.get_json()
        if not data or not data.get('city'):
            return jsonify({"error": "Ciudad no especificada"}), 400
            
        city_data = obtener_datos_ciudad(data['city'], data['date'], data['time'])
        
        if isinstance(city_data, dict) and "error" in city_data:
            return jsonify(city_data), 400
            
        if isinstance(city_data, list) and len(city_data) > 0:
            city_data = city_data[0]
        else:
            return jsonify({"error": "No se pudo obtener información de la ciudad"}), 400
        
        try:
            # Obtener zona horaria para las coordenadas
            timezone_info = obtener_zona_horaria(city_data, data['date'])
            
            # Convertir fecha y hora local a UTC
            utc_datetime = convertir_a_utc(data['date'], data['time'], timezone_info)
            
            # Calcular posiciones con el datetime UTC
            positions = calculate_positions_with_utc(utc_datetime, city_data["lat"], city_data["lon"])
            
            # Calcular aspectos entre posiciones
            aspects = calculate_positions_aspects(positions)
            
            # Calcular tabla de dignidades
            dignity_table = calculate_dignity_table(positions, aspects)
            
            # Determinar si es nacimiento seco o húmedo
            birth_type = "seco" if is_dry_birth(positions) else "húmedo"
            
            # Calcular casas y triplicidades
            houses_table = calculate_houses_with_triplicities(positions, birth_type == "seco")
            
            # Generar interpretaciones si el intérprete está disponible
            interpretations = {
                "planets_in_signs": [],
                "planets_in_houses": [],
                "aspects": [],
                "house_rulers": []
            }
            
            if interpreter and interpreter.root:
                # Interpretar planetas en signos
                for planet in positions:
                    if planet["name"] in ["SOL", "LUNA", "MERCURIO", "VENUS", "MARTE", "JÚPITER", "SATURNO"]:
                        sign_interp = interpreter.get_planet_in_sign(planet["name"], planet["sign"])
                        if sign_interp:
                            interpretations["planets_in_signs"].append({
                                "planet": planet["name"],
                                "sign": planet["sign"],
                                "interpretation": sign_interp
                            })
                
                # Interpretar planetas en casas
                asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
                if asc_pos:
                    for planet in positions:
                        if planet["name"] in ["SOL", "LUNA", "MERCURIO", "VENUS", "MARTE", "JÚPITER", "SATURNO"]:
                            house_num = get_house_number(planet["longitude"], asc_pos["longitude"])
                            house_interp = interpreter.get_planet_in_house(planet["name"], house_num)
                            if house_interp:
                                interpretations["planets_in_houses"].append({
                                    "planet": planet["name"],
                                    "house": house_num,
                                    "interpretation": house_interp
                                })
                
                # Interpretar aspectos
                for aspect in aspects:
                    # Extraer los nombres de los planetas y el tipo de aspecto
                    parts = aspect.split()
                    if len(parts) >= 3:
                        planet1 = parts[0]
                        aspect_type = parts[1]
                        planet2 = parts[2]
                        
                        aspect_interp = interpreter.get_aspect_interpretation(planet1, planet2, aspect_type)
                        if aspect_interp:
                            interpretations["aspects"].append({
                                "planets": f"{planet1} - {planet2}",
                                "type": aspect_type,
                                "interpretation": aspect_interp
                            })
                
                # Interpretar regentes de casas
                for house_data in houses_table:
                    house_num = house_data["house_number"]
                    sign = house_data["sign"]
                    element = house_data["element"]
                    rulers = house_data["triplicity_rulers"]
                    
                    # Obtener interpretación para cada tipo de regente
                    ruler_types = ["regente1", "regente2", "regente3"]
                    ruler_names = ["húmedo", "seco", "participativo"]
                    
                    for i, ruler_key in enumerate(ruler_types):
                        ruler = rulers[ruler_key]
                        for planet in positions:
                            if planet["name"] == ruler:
                                # Determinar en qué casa está el regente
                                ruler_house = get_house_number(planet["longitude"], asc_pos["longitude"])
                                
                                # Obtener interpretación
                                ruler_interp = interpreter.get_house_ruler_interpretation(house_num, ruler_house)
                                if ruler_interp:
                                    interpretations["house_rulers"].append({
                                        "house": house_num,
                                        "ruler": ruler,
                                        "ruler_type": ruler_names[i],
                                        "ruler_house": ruler_house,
                                        "interpretation": ruler_interp
                                    })
            
            # Construir respuesta
            response = {
                "positions": positions,
                "coordinates": {
                    "latitude": city_data["lat"],
                    "longitude": city_data["lon"]
                },
                "city": city_data["nombre"],
                "timezone": timezone_info,
                "local_time": f"{data['date']} {data['time']}",
                "utc_time": utc_datetime.strftime("%Y-%m-%d %H:%M"),
                "aspects": aspects,
                "dignity_table": dignity_table,
                "houses_analysis": {
                    "houses": houses_table,
                    "birth_type": birth_type
                },
                "interpretations": interpretations
            }
            
            return jsonify(response)
            
        except Exception as timezone_error:
            print(f"Error con zona horaria: {str(timezone_error)}")
            # Si hay error con la zona horaria, usar la función original
            positions = calculate_positions(
                data['date'],
                data['time'],
                city_data["lat"],
                city_data["lon"]
            )
            
            # Cálculos adicionales con el método original
            aspects = calculate_positions_aspects(positions)
            dignity_table = calculate_dignity_table(positions, aspects)
            birth_type = "seco" if is_dry_birth(positions) else "húmedo"
            houses_table = calculate_houses_with_triplicities(positions, birth_type == "seco")
            
            return jsonify({
                "positions": positions,
                "coordinates": {
                    "latitude": city_data["lat"],
                    "longitude": city_data["lon"]
                },
                "city": city_data["nombre"],
                "error_timezone": f"No se pudo determinar la zona horaria: {str(timezone_error)}",
                "aspects": aspects,
                "dignity_table": dignity_table,
                "houses_analysis": {
                    "houses": houses_table,
                    "birth_type": birth_type
                },
                "interpretations": {
                    "planets_in_signs": [],
                    "planets_in_houses": [],
                    "aspects": [],
                    "house_rulers": []
                }
            })
        
    except Exception as e:
        print(f"Error general: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\nIniciando servidor de carta astral optimizado...")
    preload_resources()
    print("Servidor iniciando en modo producción")
    app.run(host='0.0.0.0', port=10000, debug=False)