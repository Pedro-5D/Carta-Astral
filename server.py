def obtener_zona_horaria(ciudad, coordenadas, fecha):
    """
    Obtiene la zona horaria y ajusta para horario de verano/invierno
    basado en las coordenadas y la fecha
    """
    try:
        lat = coordenadas["lat"]
        lon = coordenadas["lon"]
        
        # Usar la API de Geoapify para obtener información de zona horaria exacta
        geotz_url = f"https://api.geoapify.com/v1/timezone?apiKey={API_KEY}&lat={lat}&lon={lon}"
        
        # Hacer la petición
        response = requests.get(geotz_url, timeout=10)
        tzdata = response.json()
        
        print(f"Datos de zona horaria: {tzdata}")
        
        # Obtener nombre de zona horaria
        if "timezone" in tzdata:
            tz_name = tzdata["timezone"]["name"]
            tz_offset = tzdata["timezone"]["offset_STD"]
            dst_active = tzdata["timezone"]["is_dst"]
            
            # Convertir fecha a datetime para verificar DST
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
            
            # Construir respuesta
            return {
                "name": tz_name,
                "offset": tz_offset,
                "abbreviation_STD": tzdata["timezone"].get("abbreviation_STD", ""),
                "abbreviation_DST": tzdata["timezone"].get("abbreviation_DST", ""),
                "is_dst": dst_active
            }
        
        # Si no hay datos, usar zona horaria predeterminada
        return {
            "name": "UTC",
            "offset": 0,
            "abbreviation_STD": "UTC",
            "abbreviation_DST": "UTC",
            "is_dst": False
        }
    
    except Exception as e:
        print(f"Error obteniendo zona horaria: {str(e)}")
        # Fallback a zona horaria basada en país
        try:
            pais = None
            if "pais" in coordenadas:
                pais = coordenadas["pais"]
            elif ", " in ciudad:
                pais = ciudad.split(", ")[-1]
            
            if pais:
                # Asignar zonas horarias comunes
                zonas_por_pais = {
                    "España": {"name": "Europe/Madrid", "offset": 1, "is_dst": False},
                    "México": {"name": "America/Mexico_City", "offset": -6, "is_dst": False},
                    "Argentina": {"name": "America/Argentina/Buenos_Aires", "offset": -3, "is_dst": False},
                    "Estados Unidos": {"name": "America/New_York", "offset": -5, "is_dst": False},
                    "Reino Unido": {"name": "Europe/London", "offset": 0, "is_dst": False},
                    "Francia": {"name": "Europe/Paris", "offset": 1, "is_dst": False},
                    "Alemania": {"name": "Europe/Berlin", "offset": 1, "is_dst": False},
                    "Italia": {"name": "Europe/Rome", "offset": 1, "is_dst": False},
                    "Japón": {"name": "Asia/Tokyo", "offset": 9, "is_dst": False}
                }
                
                if pais in zonas_por_pais:
                    return zonas_por_pais[pais]
            
            # Si no se puede determinar por país, usar UTC
            return {
                "name": "UTC",
                "offset": 0,
                "abbreviation_STD": "UTC",
                "abbreviation_DST": "UTC",
                "is_dst": False
            }
        except:
            # Si todo falla, usar UTC
            return {
                "name": "UTC",
                "offset": 0,
                "abbreviation_STD": "UTC",
                "abbreviation_DST": "UTC",
                "is_dst": False
            }

def convertir_a_utc(fecha, hora, timezone_info):
    """
    Convierte fecha y hora local a UTC considerando zona horaria y DST
    """
    try:
        # Combinar fecha y hora en un objeto datetime
        fecha_hora_str = f"{fecha} {hora}"
        dt_local = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
        
        # Agregar la información de zona horaria
        offset_hours = timezone_info["offset"]
        is_dst = timezone_info["is_dst"]
        
        # Ajustar offset si estamos en horario de verano
        if is_dst:
            offset_hours += 1
        
        # Crear un timezone con el offset
        tz = timezone(timedelta(hours=offset_hours))
        
        # Aplicar timezone al datetime
        dt_local_with_tz = dt_local.replace(tzinfo=tz)
        
        # Convertir a UTC
        dt_utc = dt_local_with_tz.astimezone(timezone.utc)
        
        return dt_utc
    except Exception as e:
        print(f"Error en conversión a UTC: {str(e)}")
        # Si falla, usar la hora proporcionada asumiendo UTC
        dt_local = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        return dt_local.replace(tzinfo=timezone.utc)

def calculate_positions_with_utc(utc_datetime, lat=None, lon=None):
    """
    Calcula posiciones planetarias con un datetime UTC
    """
    try:
        # Usar el datetime UTC directamente
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
        raiseimport json
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
import pandas as pd
from pathlib import Path
from functools import lru_cache
import requests

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

import urllib.request
import ssl

# Función para descargar de421.bsp de manera segura
def download_de421():
    urls = [
        'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de421.bsp',
        'https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp',
        'http://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp'
    ]
    
    for url in urls:
        try:
            print(f"Intentando descargar de: {url}")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                with open('de421.bsp', 'wb') as f:
                    f.write(response.read())
            print("Descarga exitosa")
            return True
        except Exception as e:
            print(f"Error descargando de {url}: {e}")
    
    return False

# Precarga de recursos al inicio
def preload_resources():
    global eph, ts, interpreter, time_zone_df, common_cities
    
    print("Precargando recursos...")
    
    # Cargar efemérides
    try:
        # Primero intentar cargar el archivo local si existe
        eph_path = Path('de421.bsp')
        if not eph_path.exists():
            # Si no existe localmente, intentar desde la carpeta docs
            eph_path = Path('docs') / 'de421.bsp'
        
        if eph_path.exists():
            print(f"Cargando efemérides desde: {eph_path}")
            eph = load(str(eph_path))
        else:
            print("Archivo de efemérides no encontrado localmente, intentando descargar...")
            if download_de421():
                eph = load('de421.bsp')
            else:
                # Usar alternativa más ligera
                print("Usando archivo de efemérides alternativo...")
                eph = load('de440s.bsp')  # Versión más pequeña
    except Exception as e:
        print(f"Error cargando efemérides: {e}")
        raise
    
    ts = load.timescale()
    
    # Cargar intérprete
    interpreter = AstrologicalInterpreter()
    
    # Cargar zonas horarias
    time_zone_df = pd.read_csv("time_zone.csv", 
                              names=["timezone", "country_code", "abbreviation", "timestamp", "utc_offset", "dst"],
                              header=None)
    
    # Precargar ciudades comunes
    cities = ["Madrid", "Barcelona", "Londres", "París", "Nueva York", "Buenos Aires", "México DF"]
    for city in cities:
        common_cities[city.lower()] = obtener_datos_ciudad(city, "", "")
    
    print("Recursos precargados correctamente")

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
                    "pais": resultado["properties"]["country"]
                }
                for resultado in datos["features"]]
                return opciones
            return {"error": "Ciudad no encontrada"}
        return {"error": f"Error en la consulta: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "Timeout en la consulta"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

class AstrologicalInterpreter:
    def __init__(self, xml_path='interpretations.xml'):
        try:
            self.tree = ET.parse(xml_path)
            self.root = self.tree.getroot()
            print("XML de interpretaciones cargado correctamente")
        except Exception as e:
            print(f"Error al cargar el archivo XML: {e}")
            raise

    def get_planet_in_sign(self, planet, sign):
        try:
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
            xpath = f".//HRULER_IN_HOUSE/RH{ruler_house}/HS{house_position}"
            ruler_element = self.root.find(xpath)
            
            if ruler_element is not None and ruler_element.text:
                return ruler_element.text.strip()
            return None
        except Exception as e:
            print(f"Error en get_house_ruler_interpretation: {e}")
            return None

# Funciones astrológicas
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
            return name
    
    return "ARIES"

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
        raise

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
        raise

# Rutas de la aplicación
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
            
        positions = calculate_positions(
            data['date'],
            data['time'],
            city_data["lat"],
            city_data["lon"]
        )
        
        # Cálculos simplificados para respuesta rápida
        response = {
            "positions": positions,
            "coordinates": {
                "latitude": city_data["lat"],
                "longitude": city_data["lon"]
            },
            "city": city_data["nombre"],
            "aspects": [],  # Simplificado para mayor velocidad
            "dignity_table": {"tabla": [], "total_general": 0},  # Simplificado
            "houses_analysis": {
                "houses": [],
                "birth_type": "húmedo"
            },
            "interpretations": {
                "planets_in_signs": [],
                "planets_in_houses": [],
                "aspects": [],
                "house_rulers": []
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def obtener_ciudades(ciudad):
    # Usar dos APIs distintas para mejorar la cobertura global
    url_geoapify = f"https://api.geoapify.com/v1/geocode/autocomplete?text={ciudad}&apiKey={API_KEY}&limit=20"
    
    try:
        print(f"Buscando ciudad: {ciudad}")
        respuesta = requests.get(url_geoapify, timeout=10)
        print(f"Status code: {respuesta.status_code}")
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # Procesar resultados de Geoapify
        ciudades = []
        if "features" in datos and datos["features"]:
            for feature in datos["features"]:
                if "properties" in feature and "formatted" in feature["properties"]:
                    nombre = feature["properties"]["formatted"]
                    print(f"Ciudad encontrada (Geoapify): {nombre}")
                    ciudades.append(nombre)
        
        # Si no obtuvimos suficientes resultados, intentar con OpenStreetMap Nominatim
        if len(ciudades) < 5:
            print("Intentando con Nominatim...")
            url_nominatim = f"https://nominatim.openstreetmap.org/search?q={ciudad}&format=json&addressdetails=1&limit=10"
            headers = {'User-Agent': 'CartaAstral/1.0'}
            
            respuesta_nom = requests.get(url_nominatim, headers=headers, timeout=10)
            respuesta_nom.raise_for_status()
            datos_nom = respuesta_nom.json()
            
            for lugar in datos_nom:
                # Construir un nombre formateado
                nombre_partes = []
                if "name" in lugar:
                    nombre_partes.append(lugar["name"])
                elif "display_name" in lugar:
                    nombre_partes.append(lugar["display_name"].split(",")[0])
                
                if "address" in lugar:
                    if "city" in lugar["address"]:
                        if not nombre_partes or lugar["address"]["city"] != nombre_partes[0]:
                            nombre_partes.append(lugar["address"]["city"])
                    
                    if "country" in lugar["address"]:
                        nombre_partes.append(lugar["address"]["country"])
                
                if nombre_partes:
                    nombre_formateado = ", ".join(nombre_partes)
                    print(f"Ciudad encontrada (Nominatim): {nombre_formateado}")
                    if nombre_formateado not in ciudades:
                        ciudades.append(nombre_formateado)
        
        # Eliminar duplicados y ordenar
        ciudades = list(set(ciudades))
        
        if ciudades:
            return ciudades
        else:
            print("No se encontraron ciudades en ninguna API")
            return {"error": "No se encontraron ciudades para la consulta."}
            
    except Exception as e:
        print(f"Error en búsqueda de ciudades: {str(e)}")
        return {"error": f"Error en la búsqueda: {str(e)}"}

if __name__ == '__main__':
    print("\nIniciando servidor de carta astral optimizado...")
    preload_resources()
    print("Servidor iniciando en modo producción")
    app.run(host='0.0.0.0', port=10000, debug=False)  # Debug desactivado para mejor rendimiento
