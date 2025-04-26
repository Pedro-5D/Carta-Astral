import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from skyfield.api import load, wgs84
from math import sin, cos, tan, atan, atan2, radians, degrees
import xml.etree.ElementTree as ET
import numpy as np
import os
import pandas as pd
from flask import Flask, request, jsonify
from skyfield.api import load
ts = load.timescale()
from skyfield.api import load
eph = load('de421.bsp')  # Carga las efemérides
from pathlib import Path

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})# 🔹 Cargar datos de ciudades y coordenadas
import requests
from datetime import datetime

API_KEY = "e19afa2a9d6643ea9550aab89eefce0b"

def obtener_datos_ciudad(ciudad, fecha, hora):
    url = f"https://api.geoapify.com/v1/geocode/search?text={ciudad}&apiKey={API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        datos = response.json()
        if datos.get("features"):
            opciones = [
                {
                    "nombre": resultado["properties"]["formatted"],
                    "lat": resultado["properties"]["lat"],
                    "lon": resultado["properties"]["lon"],
                    "pais": resultado["properties"]["country"],
                    "fecha": fecha,
                    "hora": hora
                }
                for resultado in datos["features"]
            ]
            return opciones
        else:
            return {"error": "Ciudad no encontrada"}
    else:
        return {"error": f"Error en la consulta: {response.status_code}"}

# 🔹 Cargar datos de husos horarios desde CSV
def cargar_husos_horarios():
    columnas = ["timezone", "country_code", "abbreviation", "timestamp", "utc_offset", "dst"]  # Agregar nombres de columna
    df = pd.read_csv("./time_zone.csv", names=columnas, header=None)  # Cargar CSV sin encabezados
    df = df.groupby("country_code").first()  # Agrupa por país y elimina duplicados
    husos_horarios = df.to_dict(orient="index")


husos_horarios = cargar_husos_horarios()

df = pd.read_csv("time_zone.csv")

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def convertir_a_ut_zoneinfo(date_str, time_str, timezone_str):
    """Convierte fecha y hora local a UTC con ajuste de horario de verano/invierno (DST)."""

    try:
        # ✅ Convertir fecha de 'YYYY-MM-DD' a objeto datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        # ✅ Convertir hora a objeto time
        time_obj = datetime.strptime(time_str, "%H:%M").time()

        # ✅ Combinar fecha y hora y aplicar zona horaria local
        dt_local = datetime.combine(date_obj, time_obj).replace(tzinfo=ZoneInfo(timezone_str))
        
        # ✅ Convertir a UTC y detectar horario de verano
        dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
        en_dst = dt_utc.dst() != timedelta(0)

        return dt_utc, en_dst

    except ValueError:
        raise ValueError(f"Formato de fecha inválido: {date_str}. Se esperaba 'YYYY-MM-DD'.")

def init_interpreter():
    global interpreter
    try:
        interpreter = AstrologicalInterpreter()
        print("Intérprete astrológico inicializado correctamente")
    except Exception as e:
        print(f"Error inicializando el intérprete: {str(e)}")
        raise
		
class AstrologicalInterpreter:
    """Clase para manejar todas las interpretaciones astrológicas"""
    
    def __init__(self, xml_path='interpretations.xml'):
        """Inicializa el intérprete con los datos XML"""
        try:
            self.tree = ET.parse(xml_path)
            self.root = self.tree.getroot()
            print("XML de interpretaciones cargado correctamente")
        except Exception as e:
            print(f"Error al cargar el archivo XML: {e}")
            raise

    def get_planet_in_sign(self, planet, sign):
        """
        Obtiene la interpretación completa de un planeta en un signo
        """
        try:
            # Buscar el elemento del planeta en el signo
            xpath = f".//PLANET_IN_SIGN14/{planet}/{sign}"
            planet_element = self.root.find(xpath)
            
            if planet_element is not None:
                # Extraer el texto completo y separar los planos físico y astral
                full_text = planet_element.text.strip() if planet_element.text else ""
                
                physical_desc = ""
                astral_desc = ""
                
                # Dividir el texto en plano físico y astral
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
        """
        Obtiene la interpretación de un planeta en una casa específica
        """
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
        """
        Obtiene la interpretación de un aspecto entre dos planetas
        """
        try:
            # Obtener el ángulo basado en el tipo de aspecto
            aspect_angles = {
                "Armónico Relevante": ["0", "60", "120", "180"],
                "Inarmónico Relevante": ["90", "150"],
                "Armónico": ["12", "24", "36", "48", "72", "84", "96", "108", "132", "144", "156", "168"],
                "Inarmónico": ["6", "18", "42", "54", "66", "78", "102", "114", "126", "138", "162", "174"]
            }
            
            # Buscar la interpretación del aspecto
            for angles in aspect_angles[aspect_type]:
                xpath = f".//PLANET_IN_ASPECT/{planet1}/{planet2}/ASP_{angles}"
                aspect_element = self.root.find(xpath)
                
                if aspect_element is not None and aspect_element.text:
                    return aspect_element.text.strip()
                
                # Intentar con los planetas en orden inverso
                xpath = f".//PLANET_IN_ASPECT/{planet2}/{planet1}/ASP_{angles}"
                aspect_element = self.root.find(xpath)
                
                if aspect_element is not None and aspect_element.text:
                    return aspect_element.text.strip()
            
            return None
            
        except Exception as e:
            print(f"Error en get_aspect_interpretation: {e}")
            return None

    def get_house_ruler_interpretation(self, ruler_house, house_position):
        """
        Obtiene la interpretación del regente de una casa en otra casa
        """
        try:
            xpath = f".//HRULER_IN_HOUSE/RH{ruler_house}/HS{house_position}"
            ruler_element = self.root.find(xpath)
            
            if ruler_element is not None and ruler_element.text:
                return ruler_element.text.strip()
            return None
            
        except Exception as e:
            print(f"Error en get_house_ruler_interpretation: {e}")
            return None

        print("Cargando efemérides...")
        try:
	    # Ruta al archivo 'de421.bsp' dentro de la carpeta 'docs'
            eph_path = Path('docs') / 'de421.bsp'
	    
	    # Verificar si el archivo existe
            if not eph_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {eph_path}")
	    
	    # Cargar efemérides y escala de tiempo
            eph = load(str(eph_path))  # Convertir a cadena para compatibilidad
            ts = load.timescale()
            print(f"Efemérides cargadas correctamente desde {eph_path}")
        except FileNotFoundError as fnf_error:
            print(f"Error: {fnf_error}")
            print("Asegúrate de que el archivo 'de421.bsp' esté en la carpeta 'docs'.")
        except Exception as e:
            print(f"Error inesperado cargando efemérides: {e}")

SIGNS_BY_ELEMENT = {
    "AIRE": ["GÉMINIS", "ACUARIO", "OFIUCO", "LIBRA"],
    "TIERRA": ["TAURO", "CAPRICORNIO", "VIRGO"],
    "AGUA": ["ESCORPIO", "CÁNCER", "PISCIS", "PEGASO"],
    "FUEGO": ["ARIES", "LEO", "SAGITARIO"]
}
ZODIAC_SIGNS = [
    "ARIES", "TAURO", "GÉMINIS", "CÁNCER", "LEO", "VIRGO", 
    "LIBRA", "ESCORPIO", "OFIUCO", "SAGITARIO", "CAPRICORNIO", 
    "ACUARIO", "PEGASO", "PISCIS"]

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

ELEMENT_BY_SIGN = {sign: element for element, signs in SIGNS_BY_ELEMENT.items() for sign in signs}

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

def get_sign(longitude):
    """
    Determina el signo zodiacal incluyendo los 14 signos.
    
    Args:
        longitude (float): Longitud zodiacal
    
    Returns:
        str: Nombre del signo
    """
    longitude = float(longitude) % 360
    print(f"Calculando signo para longitud: {longitude}")
    
    # Definición completa de los 14 signos con sus longitudes exactas
    signs = [
        ("ARIES", 354.00, 36.00),        # 354° - 30°
        ("TAURO", 30.00, 30.00),         # 30° - 60°
        ("GÉMINIS", 60.00, 30.00),       # 60° - 90°
        ("CÁNCER", 90.00, 30.00),        # 90° - 120°
        ("LEO", 120.00, 30.00),          # 120° - 150°
        ("VIRGO", 150.00, 36.00),        # 150° - 186°
        ("LIBRA", 186.00, 24.00),        # 186° - 210°
        ("ESCORPIO", 210.00, 30.00),     # 210° - 240°
        ("OFIUCO", 240.00, 12.00),       # 240° - 252°
        ("SAGITARIO", 252.00, 18.00),    # 252° - 270°
        ("CAPRICORNIO", 270.00, 36.00),  # 270° - 306°
        ("ACUARIO", 306.00, 18.00),      # 306° - 324°
        ("PEGASO", 324.00, 6.00),        # 324° - 330°
        ("PISCIS", 330.00, 24.00)        # 330° - 354°
    ]
    
    for name, start, length in signs:
        end = start + length
        if start <= longitude < end:
            print(f"Encontrado signo {name} para longitud {longitude} (entre {start} y {end})")
            return name
        elif start > 354.00 and (longitude >= start or longitude < (end % 360)):
            # Caso especial para Aries que cruza 0°
            print(f"Encontrado signo {name} para longitud {longitude} (cruzando 0°)")
            return name
            
    print(f"No se encontró signo para longitud {longitude}, retornando ARIES")
    return "ARIES"

def get_element_for_sign(sign):
    """
    Determina el elemento de un signo zodiacal.
    
    Args:
        sign (str): Nombre del signo
        
    Returns:
        str: Elemento del signo (AIRE, TIERRA, AGUA, FUEGO)
    """
    # Definición explícita de los 14 signos y sus elementos
    SIGN_ELEMENTS = {
        "ARIES": "FUEGO",
        "TAURO": "TIERRA",
        "GÉMINIS": "AIRE",
        "CÁNCER": "AGUA",
        "LEO": "FUEGO",
        "VIRGO": "TIERRA",
        "LIBRA": "AIRE",
        "ESCORPIO": "AGUA",
        "OFIUCO": "AIRE",        # Ofiuco explícitamente como AIRE
        "SAGITARIO": "FUEGO",
        "CAPRICORNIO": "TIERRA",
        "ACUARIO": "AIRE",
        "PEGASO": "AGUA",        # Pegaso como AGUA
        "PISCIS": "AGUA"
    }
    
    element = SIGN_ELEMENTS.get(sign)
    print(f"Elemento para {sign}: {element}")
    return element

def get_triplicity_rulers_for_sign(sign, is_dry_birth):
    """
    Obtiene los regentes de triplicidad para un signo dado.
    """
    element = get_element_for_sign(sign)
    if not element:
        raise ValueError(f"Elemento no encontrado para el signo {sign}")
    
    rulers = TRIPLICITIES[element]
    
    return {
        "regente1": rulers["humedo"],
        "regente2": rulers["seco"],
        "regente3": rulers["participativo"]
    }

def calculate_houses_with_triplicities(positions, is_dry_birth):
    """
    Calcula la tabla de casas con sus triplicidades.
    Las casas son siempre de 30° exactos,
    pero los signos en las cúspides tienen longitudes variables.
    """
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not asc_pos:
        raise ValueError("No se encontró la posición del ASC")
    
    houses_table = []
    
    # Los signos tienen longitudes variables pero las casas son de 30° exactos
    signs = [
        ("ARIES", 354.00, 36.00),        # 354° - 30°
        ("TAURO", 30.00, 30.00),         # 30° - 60°
        ("GÉMINIS", 60.00, 30.00),       # 60° - 90°
        ("CÁNCER", 90.00, 30.00),        # 90° - 120°
        ("LEO", 120.00, 30.00),          # 120° - 150°
        ("VIRGO", 150.00, 36.00),        # 150° - 186°
        ("LIBRA", 186.00, 24.00),        # 186° - 210°
        ("ESCORPIO", 210.00, 30.00),     # 210° - 240°
        ("OFIUCO", 240.00, 12.00),       # 240° - 252°
        ("SAGITARIO", 252.00, 18.00),    # 252° - 270°
        ("CAPRICORNIO", 270.00, 36.00),  # 270° - 306°
        ("ACUARIO", 306.00, 18.00),      # 306° - 324°
        ("PEGASO", 324.00, 6.00),        # 324° - 330°
        ("PISCIS", 330.00, 24.00)        # 330° - 354°
    ]
    
    for i in range(12):
        # Calcular la cúspide de la casa (siempre 30° cada una)
        house_cusp = (asc_pos["longitude"] + (i * 30)) % 360
        
        # Encontrar qué signo está en esa longitud
        sign = get_sign(house_cusp)
        element = get_element_for_sign(sign)
        triplicity_rulers = get_triplicity_rulers_for_sign(sign, is_dry_birth)
        
        print(f"Casa {i+1}: cúspide={house_cusp:.2f}°, signo={sign}, elemento={element}")  # Debug
        
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

def get_sign(longitude):
    longitude = float(longitude) % 360
    signs = [
        ("ARIES", 354.00, 36),
        ("TAURO", 30.00, 30),
        ("GÉMINIS", 60.00, 30),
        ("CÁNCER", 90.00, 30),
        ("LEO", 120.00, 30),
        ("VIRGO", 150.00, 36),
        ("LIBRA", 186.00, 24),
        ("ESCORPIO", 210.00, 30),
        ("OFIUCO", 240.00, 12),       # Aquí está la clave
        ("SAGITARIO", 252.00, 18),
        ("CAPRICORNIO", 270.00, 36),
        ("ACUARIO", 306.00, 18),
        ("PEGASO", 324.00, 6),
        ("PISCIS", 330.00, 24)
    ]
    
    for name, start, length in signs:
        if start <= longitude < (start + length):
            return name
    return "ARIES"

def get_element_for_sign(sign):
    """
    Determina el elemento de un signo zodiacal.
    """
    print(f"Buscando elemento para signo: {sign}")
    
    elements = {
        "AIRE": ["GÉMINIS", "ACUARIO", "OFIUCO", "LIBRA"],
        "TIERRA": ["TAURO", "CAPRICORNIO", "VIRGO"],
        "AGUA": ["ESCORPIO", "CÁNCER", "PISCIS", "PEGASO"],
        "FUEGO": ["ARIES", "LEO", "SAGITARIO"]
    }
    
    for element, signs in elements.items():
        if sign in signs:
            print(f"Encontrado elemento {element} para signo {sign}")
            return element
            
    print(f"ADVERTENCIA: No se encontró elemento para signo {sign}")
    return None

def get_triplicity_rulers_for_sign(sign, is_dry_birth):
    """Obtiene los regentes de triplicidad para un signo dado."""
    element = get_element_for_sign(sign)
    if not element:
        raise ValueError(f"Elemento no encontrado para el signo {sign}")
    
    rulers = TRIPLICITIES[element]
    
    if is_dry_birth:
        return {
            "regente1": rulers["seco"],
            "regente2": rulers["humedo"],
            "regente3": rulers["participativo"]
        }
    else:
        return {
            "regente1": rulers["humedo"],
            "regente2": rulers["seco"],
            "regente3": rulers["participativo"]
        }

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

def get_house_number(longitude, mc_longitude):
    """Calcula el número de casa basado en la longitud del planeta y la longitud del MC."""
    longitude = longitude % 360
    mc_longitude = mc_longitude % 360
    
    diff = (longitude - mc_longitude) % 360
    house = 10 - (int(diff / 30))
    if house <= 0:
        house += 12
    
    return house

def is_dry_birth(positions):
    """
    Determina si un nacimiento es seco basado en la posición del Sol.
    Es seco cuando el Sol está entre las casas 6 y 11 (inclusive).
    
    Args:
        positions (list): Lista de posiciones planetarias
        
    Returns:
        bool: True si es nacimiento seco, False si es húmedo
    """
    sun_pos = next((p for p in positions if p["name"] == "SOL"), None)
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not sun_pos or not asc_pos:
        raise ValueError("No se encontró la posición del Sol o del ASC")
    
    # Calcular la casa del Sol relativa al Ascendente
    diff = (sun_pos["longitude"] - asc_pos["longitude"]) % 360
    house = (diff // 30) + 1
    
    print(f"Sol en casa: {house}")  # Debug
    print(f"Longitud Sol: {sun_pos['longitude']}")  # Debug
    print(f"Longitud ASC: {asc_pos['longitude']}")  # Debug
    
    # Es seco si el Sol está en las casas 6 a 11
    return 6 <= house <= 11

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
       
       if asc_position:
           angle = calculate_angle(pos1["longitude"], asc_position["longitude"])
           aspect_type = determine_aspect_type(angle)
           
           if aspect_type:
               aspect = f"{pos1['name']} {aspect_type} ASC ({angle:.2f}°)"
               aspects.append(aspect)
   
   return aspects

def get_aspect_points(aspect_text):
   if "Armónico" in aspect_text:
       if "°)" in aspect_text:
           angle = float(aspect_text.split("(")[1].replace("°)", ""))
           if abs(angle - 120) <= 2 or abs(angle - 180) <= 2 or angle <= 2:
               return 6
           elif abs(angle - 60) <= 2:
               return 3
           else:
               return 1
   elif "Inarmónico" in aspect_text:
       if "°)" in aspect_text:
           angle = float(aspect_text.split("(")[1].replace("°)", ""))
           if abs(angle - 90) <= 2:
               return -6
           elif abs(angle - 45) <= 2 or abs(angle - 135) <= 2 or abs(angle - 150) <= 2:
               return -3
           else:
               return -1
   return 0

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
	
def get_house_number(longitude, asc_longitude):
    """Calcula la casa desde el Ascendente."""
    diff = (longitude - asc_longitude) % 360
    house = 1 + (int(diff / 30))
    if house > 12:
        house = house - 12
    return house

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
                "casa": house_points,  # Aquí ponemos los puntos en vez del número
                "puntos_dignidad": dignity_points,
                "puntos_angular": angular_points,
                "puntos_aspectos": aspect_points,
                "total_planeta": planet_total
            })
    
    return {
        "tabla": table,
        "total_general": total_points
    }

def get_triplicity_rulers_for_sign(sign, is_dry_birth):
    """Obtiene los regentes de triplicidad para un signo dado."""
    element = get_element_for_sign(sign)
    if not element:
        raise ValueError(f"Elemento no encontrado para el signo {sign}")
    
    rulers = TRIPLICITIES[element]
    
    # El orden de los regentes ya está definido aquí
    return {
        "regente1": rulers["humedo"],  # Primer regente (húmedo)
        "regente2": rulers["seco"],    # Segundo regente (seco)
        "regente3": rulers["participativo"]  # Tercer regente (participativo)
    }

def calculate_houses_with_triplicities(positions, is_dry_birth):
    """Calcula la tabla de casas con sus triplicidades."""
    asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
    
    if not asc_pos:
        raise ValueError("No se encontró la posición del ASC")
    
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
	
def calculate_asc_mc(t, lat, lon):
    """
    Cálculo de ASC y MC con ajuste según la distancia entre ambos
    """
    try:
        # Obtener GAST y LST
        gst = t.gast
        lst = (gst * 15 + lon) % 360
        
        # MC sigue siendo el LST
        mc = lst % 360
        
        # Cálculo del ASC
        lat_rad = np.radians(lat)
        ra_rad = np.radians(lst)
        eps_rad = np.radians(23.4367)
        
        # Fórmula base del ASC
        tan_asc = np.cos(ra_rad) / (np.sin(ra_rad) * np.cos(eps_rad) + np.tan(lat_rad) * np.sin(eps_rad))
        asc = np.degrees(np.arctan(-tan_asc))
        
        # Ajuste inicial basado en el LST
        if 0 <= lst <= 180:
            if np.cos(ra_rad) > 0:
                asc = (asc + 180) % 360
        else:
            if np.cos(ra_rad) < 0:
                asc = (asc + 180) % 360
                
        asc = asc % 360
        
        # Nuevo ajuste: si la distancia entre MC y ASC es mayor a 180°, invertir ASC
        dist_mc_asc = (asc - mc) % 360
        if dist_mc_asc > 180:
            asc = (asc + 180) % 360
        
        # Debug info
        print(f"GAST: {gst * 15:.2f}°")
        print(f"LST: {lst:.2f}°")
        print(f"MC final: {mc:.2f}° en {get_sign(mc)}")
        print(f"ASC final: {asc:.2f}° en {get_sign(asc)}")
        print(f"Distancia MC-ASC: {dist_mc_asc:.2f}°")
        
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
            location = wgs84.latlon(lat, lon)
            observer = earth + location
            
            gast = t.gast
            lst = (gast * 15 + lon) % 360
            
            lst_rad = np.radians(lst)
            lat_rad = np.radians(lat)
            eps = np.radians(23.4367)
            
            mc = lst % 360
            
            tan_asc = -(np.cos(lst_rad) / 
                       (np.sin(lst_rad) * np.cos(eps) + 
                        np.tan(lat_rad) * np.sin(eps)))
            asc = np.degrees(np.arctan(tan_asc))
            
            # Ajuste inicial basado en el LST
            if np.cos(lst_rad) > 0:
                asc += 180
            asc = asc % 360
            
            # Nuevo ajuste: invertir ASC si está a más de 180° del MC
            dist_mc_asc = (asc - mc) % 360
            if dist_mc_asc > 180:
                asc = (asc + 180) % 360
            
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

from datetime import datetime

def obtener_zona_horaria(ciudad, fecha):
    resultado = df[df.iloc[:, 0].str.contains(ciudad, case=False, na=False)]
    
    if not resultado.empty:
        zona_horaria = resultado.iloc[-1][2]  # Ajusta según la columna correcta
        
        # Convertir la fecha ingresada a un objeto datetime
        try:
            fecha_consulta = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return "Formato de fecha inválido. Usa YYYY-MM-DD."
        
        mes = fecha_consulta.month
        
        # Definir reglas según el hemisferio
        if "Europe/" in resultado.iloc[-1][0] or "America/New_York" in resultado.iloc[-1][0]:  # Hemisferio Norte
            if 3 <= mes <= 10:
                zona_horaria = "CEST"  # Verano en Europa
        elif "America/Santiago" in resultado.iloc[-1][0] or "Australia/Sydney" in resultado.iloc[-1][0]:  # Hemisferio Sur
            if mes in [12, 1, 2, 3]:
                zona_horaria = "CLST"  # Verano en Chile
        
        return zona_horaria

    return "Ciudad no encontrada en la base de datos."

def obtener_zona_horaria(ciudad, fecha):
    resultado = df[df.iloc[:, 0].str.contains(ciudad, case=False, na=False)]
    
    if not resultado.empty:
        zona_horaria = resultado.iloc[-1][2]  # Ajusta el índice según la columna correcta
        
        # Convertir la fecha ingresada a un objeto datetime
        try:
            fecha_consulta = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return "Formato de fecha inválido. Usa YYYY-MM-DD."
        
        mes = fecha_consulta.month
        
        # Definir reglas según el hemisferio
        if "Europe/" in resultado.iloc[-1][0] or "America/New_York" in resultado.iloc[-1][0]:  # Hemisferio Norte
            if 3 <= mes <= 10:
                zona_horaria = "CEST"  # Verano en Europa
        elif "America/Santiago" in resultado.iloc[-1][0] or "Australia/Sydney" in resultado.iloc[-1][0]:  # Hemisferio Sur
            if mes in [12, 1, 2, 3]:
                zona_horaria = "CLST"  # Verano en Chile
        
        return zona_horaria

    return "Ciudad no encontrada en la base de datos."

@app.route('/open-file')
def open_file():
    try:
        file_path = request.args.get('path')

        # ✅ Si es una URL, devolverla directamente para que JavaScript la abra
        if file_path and file_path.startswith("https://"):
            return jsonify({"url": file_path})

        # ✅ Si es un archivo local, verificar existencia y enviarlo
        if file_path and os.path.exists(file_path):
            return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

        return jsonify({'error': 'Archivo no encontrado'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

from flask_cors import cross_origin
import requests

@app.route('/cities', methods=['GET'])
def get_cities():
    city_name = request.args.get("city", "").lower()
    api_url = f"https://srv801859.izarren.top/cities?city={city_name}"
    response = requests.get(api_url)

    if response.status_code == 200:
        return jsonify(response.json())
    return jsonify({"error": "Ciudad no encontrada"}), 404

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Inicializar el intérprete
        interpreter = AstrologicalInterpreter()
        
        data = request.get_json()
        if not data or not data.get('city'):
            return jsonify({"error": "Ciudad no especificada"}), 400
            
        city_data = CITIES_DB.get(data['city'].lower())
        positions = calculate_positions(
            data['date'],
            data['time'],
            city_data["lat"],
            city_data["lon"]
        )
        
        aspects = calculate_positions_aspects(positions)
        dignity_table = calculate_dignity_table(positions, aspects)
        
        # Calcular casas y triplicidades
        asc = next((p for p in positions if p["name"] == "ASC"), None)
        houses_data = calculate_houses_with_triplicities(positions, is_dry_birth(positions))
        
        # Generar interpretaciones
        interpretations = {
            "planets_in_signs": [],
            "planets_in_houses": [],
            "aspects": [],
            "house_rulers": []
        }
        
        # Interpretar planetas en signos
        Reporte_planets = ["SOL", "LUNA", "MERCURIO", "VENUS", "MARTE", "JÚPITER", "SATURNO", "URANO", "NEPTUNO", "PLUTÓN"]
        for position in positions:
            if position["name"] in Reporte_planets:
                sign_interp = interpreter.get_planet_in_sign(position["name"], position["sign"])
                if sign_interp:
                    interpretations["planets_in_signs"].append({
                        "planet": position["name"],
                        "sign": position["sign"],
                        "interpretation": sign_interp
                    })
        
        # Interpretar planetas en casas
        mc = next((p for p in positions if p["name"] == "MC"), None)
        for position in positions:
            if position["name"] in Reporte_planets:
                house = get_house_number(position["longitude"], asc["longitude"])
                house_interp = interpreter.get_planet_in_house(position["name"], house)
                if house_interp:
                    interpretations["planets_in_houses"].append({
                        "planet": position["name"],
                        "house": house,
                        "interpretation": house_interp
                    })

        # Interpretar aspectos
        for aspect in aspects:
            tokens = aspect.split()
            planet1, aspect_type = tokens[0], tokens[1]
            planet2 = tokens[2]
            interp = interpreter.get_aspect_interpretation(planet1, planet2, aspect_type)
            if interp:
                interpretations["aspects"].append({
                    "planets": f"{planet1}-{planet2}",
                    "type": aspect_type,
                    "interpretation": interp
                })

        # Interpretar regentes de casas
        for house in houses_data:
            house_num = house["house_number"]
            rulers = house.get("triplicity_rulers", {})
            
            for ruler_type, ruler in rulers.items():
                if ruler:
                    ruler_house = get_house_number(
                        next((p["longitude"] for p in positions if p["name"] == ruler), 0),
                        mc["longitude"]
                    )
                    
                    interp = interpreter.get_house_ruler_interpretation(house_num, ruler_house)
                    if interp:
                        interpretations["house_rulers"].append({
                            "house": house_num,
                            "ruler": ruler,
                            "ruler_type": ruler_type,
                            "ruler_house": ruler_house,
                            "interpretation": interp
                        })

        # Construir respuesta
        response = {
            "positions": positions,
            "coordinates": {
                "latitude": city_data["lat"],
                "longitude": city_data["lon"]
            },
            "city": city_data["name"],
            "aspects": aspects,
            "dignity_table": dignity_table,
            "houses_analysis": {
                "houses": houses_data,
                "birth_type": "seco" if is_dry_birth(positions) else "húmedo"
            },
            "interpretations": interpretations
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Ruta para obtener la zona horaria
@app.route("/zona_horaria", methods=["GET"])
def zona_horaria():
    ciudad = request.args.get("ciudad")
    fecha = request.args.get("fecha")  # Obtener fecha de la consulta

    if not ciudad or not fecha:
        return jsonify({"error": "Debes proporcionar ciudad y fecha."}), 400
    
    zona_horaria = obtener_zona_horaria(ciudad, fecha)  # Ahora enviamos ambos parámetros
    return jsonify({"ciudad": ciudad, "zona_horaria": zona_horaria})

# 🔹 Endpoint para obtener coordenadas y huso horario
from flask import request, jsonify

@app.route("/coordenadas")
def obtener_coordenadas():
    ciudad = request.args.get("ciudad")
    fecha = request.args.get("fecha")
    hora = request.args.get("hora")
 
    if not ciudad or not fecha or not hora:
        return jsonify({"error": "Debes proporcionar ciudad, fecha y hora."}), 400
 
    datos_ciudad = obtener_datos_ciudad(ciudad)
    return jsonify(datos_ciudad)

from flask import Flask, send_file

app = Flask(__name__, static_folder="docs")

@app.after_request
def add_headers(response):
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
    return response

@app.route('/')
def home():
    return "Servidor funcionando correctamente"

# Esto ya estaba en tu código, no lo cambies
if __name__ == '__main__':
    print("\nIniciando servidor de carta astral con interpretaciones completas...")
    print("Cargando efemérides, configuración e interpretaciones...")
    
    # Inicializar el intérprete al arrancar el servidor
    init_interpreter()
    
    print("\nCiudades disponibles desde API...")
    print("\nServidor listo. Accediendo a API de ciudades...")
    app.run(host='0.0.0.0', port=10000, debug=True)
