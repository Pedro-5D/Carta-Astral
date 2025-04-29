from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
import sys
import os
import requests
import math
import json

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Constantes para cálculos astrológicos
PLANET_DATA = {
    'SOL': {'numero': 1},
    'LUNA': {'numero': 6},
    'MERCURIO': {'numero': 4},
    'VENUS': {'numero': 3},
    'MARTE': {'numero': 5},
    'JÚPITER': {'numero': 2},
    'SATURNO': {'numero': 7}
}

PLANET_ORDER = {
    'seco': ['SOL', 'MARTE', 'JÚPITER', 'SATURNO', 'LUNA', 'MERCURIO', 'VENUS'],
    'humedo': ['LUNA', 'MERCURIO', 'VENUS', 'SOL', 'MARTE', 'JÚPITER', 'SATURNO']
}

DURACION_POR_NIVEL = {
    'virgo': 4, 'libra': 3, 'escorpio': 5, 'ofiuco': 7, 'sagitario': 2,
    'capricornio': 1, 'acuario': 6, 'piscis': 2, 'aries': 5, 'tauro': 3,
    'geminis': 4, 'cancer': 6, 'leo': 1
}

SIGNOS = {
    'virgo': {'planeta': 'MERCURIO', 'años': 4},
    'libra': {'planeta': 'VENUS', 'años': 3},
    'escorpio': {'planeta': 'MARTE', 'años': 5},
    'ofiuco': {'planeta': 'SATURNO', 'años': 7},
    'sagitario': {'planeta': 'JÚPITER', 'años': 2},
    'capricornio': {'planeta': 'SOL', 'años': 1},
    'acuario': {'planeta': 'LUNA', 'años': 6},
    'piscis': {'planeta': 'JÚPITER', 'años': 2},
    'aries': {'planeta': 'MARTE', 'años': 5},
    'tauro': {'planeta': 'VENUS', 'años': 3},
    'geminis': {'planeta': 'MERCURIO', 'años': 4},
    'cancer': {'planeta': 'LUNA', 'años': 6},
    'leo': {'planeta': 'SOL', 'años': 1}
}

DURACIONES = {
    'AÑO': 364,
    'MES': 28,
    'SEMANA': 7,
    'DIA': 1
}

SIGNS = [
    {'name': 'ARIES', 'start': 354, 'length': 36, 'symbol': '♈', 'color': '#FFE5E5'},
    {'name': 'TAURUS', 'start': 30, 'length': 30, 'symbol': '♉', 'color': '#E5FFE5'},
    {'name': 'GEMINI', 'start': 60, 'length': 30, 'symbol': '♊', 'color': '#FFFFE5'},
    {'name': 'CANCER', 'start': 90, 'length': 30, 'symbol': '♋', 'color': '#E5FFFF'},
    {'name': 'LEO', 'start': 120, 'length': 30, 'symbol': '♌', 'color': '#FFE5E5'},
    {'name': 'VIRGO', 'start': 150, 'length': 36, 'symbol': '♍', 'color': '#E5FFE5'},
    {'name': 'LIBRA', 'start': 186, 'length': 24, 'symbol': '♎', 'color': '#FFFFE5'},
    {'name': 'SCORPIO', 'start': 210, 'length': 30, 'symbol': '♏', 'color': '#E5FFFF'},
    {'name': 'OPHIUCHUS', 'start': 240, 'length': 12, 'symbol': '⛎', 'color': '#FFFFE5'},
    {'name': 'SAGITTARIUS', 'start': 252, 'length': 18, 'symbol': '♐', 'color': '#FFE5E5'},
    {'name': 'CAPRICORN', 'start': 270, 'length': 36, 'symbol': '♑', 'color': '#E5FFE5'},
    {'name': 'AQUARIUS', 'start': 306, 'length': 18, 'symbol': '♒', 'color': '#FFFFE5'},
    {'name': 'PEGASUS', 'start': 324, 'length': 6, 'symbol': '∩', 'color': '#E5FFFF'},
    {'name': 'PISCES', 'start': 330, 'length': 24, 'symbol': '♓', 'color': '#E5FFFF'}
]

ASPECTS = {
    'CONJUNCTION': {'angle': 0, 'orb': 2, 'color': '#000080', 'name': 'Armónico Relevante'},
    'SEXTILE': {'angle': 60, 'orb': 2, 'color': '#000080', 'name': 'Armónico Relevante'},
    'SQUARE': {'angle': 90, 'orb': 2, 'color': '#FF0000', 'name': 'Inarmónico Relevante'},
    'TRINE': {'angle': 120, 'orb': 2, 'color': '#000080', 'name': 'Armónico Relevante'},
    'OPPOSITION': {'angle': 180, 'orb': 2, 'color': '#000080', 'name': 'Armónico Relevante'}
}

COLORS = {
    'RED': '#FF0000',
    'GREEN': '#00FF00',
    'BLUE': '#0000FF',
    'YELLOW': '#FFFF00'
}

# API Key para geocodificación
API_KEY = "e19afa2a9d6643ea9550aab89eefce0b"  # Para demo, en producción usar variables de entorno

# Simulación de datos planetarios para fines de demostración
def mockCalculatePositions(is_natal=True, asc_sign=None, asc_longitude=None):
    # Usar los mismos datos que en el archivo original
    base_positions = [
        {"name": "SOL", "longitude": 120 if is_natal else 150, "sign": "LEO" if is_natal else "VIRGO"},
        {"name": "LUNA", "longitude": 186 if is_natal else 210, "sign": "LIBRA" if is_natal else "SCORPIO"},
        {"name": "MERCURIO", "longitude": 135 if is_natal else 145, "sign": "LEO" if is_natal else "VIRGO"},
        {"name": "VENUS", "longitude": 90 if is_natal else 100, "sign": "CANCER" if is_natal else "CANCER"},
        {"name": "MARTE", "longitude": 210 if is_natal else 240, "sign": "SCORPIO" if is_natal else "OPHIUCHUS"},
        {"name": "JÚPITER", "longitude": 270 if is_natal else 290, "sign": "CAPRICORN" if is_natal else "CAPRICORN"},
        {"name": "SATURNO", "longitude": 330 if is_natal else 350, "sign": "PISCES" if is_natal else "PISCES"},
        {"name": "URANO", "longitude": 30 if is_natal else 32, "sign": "TAURUS" if is_natal else "TAURUS"},
        {"name": "NEPTUNO", "longitude": 354 if is_natal else 355, "sign": "ARIES" if is_natal else "ARIES"},
        {"name": "PLUTÓN", "longitude": 252 if is_natal else 254, "sign": "SAGITTARIUS" if is_natal else "SAGITTARIUS"},
        {"name": "ASC", "longitude": 0 if is_natal else 10, "sign": "ARIES" if is_natal else "ARIES"},
        {"name": "MC", "longitude": 270 if is_natal else 280, "sign": "CAPRICORN" if is_natal else "CAPRICORN"}
    ]
    
    # Si no es natal, añadir una variación aleatoria a las posiciones
    if not is_natal:
        import random
        for planet in base_positions:
            planet["longitude"] = (planet["longitude"] + random.uniform(-10, 10)) % 360
            planet["sign"] = get_sign(planet["longitude"])
    
    return base_positions

def get_sign(longitude):
    """Determina el signo zodiacal basado en la longitud eclíptica."""
    longitude = float(longitude) % 360
    
    for sign_data in SIGNS:
        start = sign_data['start']
        length = sign_data['length']
        end = (start + length) % 360
        
        # Caso normal (sin cruzar 0°)
        if start < end:
            if start <= longitude < end:
                return sign_data['name']
        # Caso especial (cruza 0°, como Aries)
        else:
            if longitude >= start or longitude < end:
                return sign_data['name']
    
    return "ARIES"  # Por defecto

def calculate_aspects(planets1, planets2=None):
    """Calcula los aspectos entre planetas."""
    if planets2 is None:
        planets2 = planets1
    
    aspects = []
    traditional_planets = ["SOL", "LUNA", "MERCURIO", "VENUS", "MARTE", "JÚPITER", "SATURNO"]
    
    # Filtrar planetas tradicionales
    valid_planets1 = [p for p in planets1 if p["name"] in traditional_planets]
    valid_planets2 = [p for p in planets2 if p["name"] in traditional_planets]
    
    for i, planet1 in enumerate(valid_planets1):
        # Si estamos calculando aspectos en la misma carta, evitar duplicados
        start_j = i + 1 if planets1 == planets2 else 0
        
        for j in range(start_j, len(valid_planets2)):
            planet2 = valid_planets2[j]
            
            # Evitar comparar un planeta consigo mismo
            if planet1 == planet2:
                continue
            
            # Calcular la diferencia angular
            diff = abs(planet1["longitude"] - planet2["longitude"])
            if diff > 180:
                diff = 360 - diff
            
            # Buscar aspectos
            for aspect_type, aspect_data in ASPECTS.items():
                if abs(diff - aspect_data["angle"]) <= aspect_data["orb"]:
                    aspects.append({
                        "planet1": planet1["name"],
                        "planet2": planet2["name"],
                        "type": aspect_type,
                        "angle": diff,
                        "color": aspect_data["color"],
                        "isInterChart": planets1 is not planets2
                    })
                    break
    
    return aspects

def is_dry_birth(sun_longitude, asc_longitude):
    """Determina si un nacimiento es seco o húmedo basado en la posición del Sol."""
    # Es seco cuando el Sol está entre las casas 6 y 11 (inclusive)
    diff = (sun_longitude - asc_longitude) % 360
    house = (diff / 30) + 1
    
    # Es seco si el Sol está en las casas 6 a 11
    return 6 <= house <= 11

# Funciones para Fardarias
def calculate_duration(planet, level):
    """Calcula la duración de un periodo de Fardaria."""
    number = PLANET_DATA[planet]['numero']
    if level == 1:
        return number * DURACIONES['AÑO']
    elif level == 2:
        return number * DURACIONES['MES']
    elif level == 3:
        return number * DURACIONES['SEMANA']
    elif level == 4:
        return number * DURACIONES['DIA']
    return 0

def get_rotated_planets(start_planet, planet_order):
    """Obtiene la secuencia de planetas rotada a partir del planeta inicial."""
    index = planet_order.index(start_planet)
    return planet_order[index:] + planet_order[:index]

def calculate_date(birth_date, day_offset):
    """Calcula una fecha a partir de una fecha base y un desplazamiento en días."""
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d')
    
    date = birth_date + timedelta(days=int(day_offset))
    return date

def calculate_sub_periods(main_planet, level, start_day, end_day, birth_date, planet_order):
    """Calcula subperiodos de Fardarias."""
    if level > 4:
        return []
    
    periods = []
    current_day = start_day
    rotated_planets = get_rotated_planets(main_planet, planet_order)
    
    for planet in rotated_planets:
        duration = calculate_duration(planet, level)
        actual_duration = min(duration, end_day - current_day)
        
        if actual_duration > 0:
            start_date = calculate_date(birth_date, current_day)
            end_date = calculate_date(birth_date, current_day + actual_duration)
            
            period = {
                'planet': planet,
                'level': level,
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'startDay': current_day,
                'durationDays': actual_duration
            }
            
            period['subPeriods'] = calculate_sub_periods(
                planet,
                level + 1,
                current_day,
                current_day + actual_duration,
                birth_date,
                planet_order
            )
            
            periods.append(period)
            current_day += actual_duration
    
    return periods

def calculate_fardaria_periods(birth_date, is_dry):
    """Calcula los periodos de Fardarias para una fecha de nacimiento."""
    planet_order = PLANET_ORDER['seco'] if is_dry else PLANET_ORDER['humedo']
    all_periods = []
    current_day = 0
    
    # Asegurar que birth_date es un objeto datetime
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d')
    
    for planet in planet_order:
        duration = calculate_duration(planet, 1)
        start_date = calculate_date(birth_date, current_day)
        end_date = calculate_date(birth_date, current_day + duration)
        
        period = {
            'planet': planet,
            'level': 1,
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'startDay': current_day,
            'durationDays': duration
        }
        
        # Añadir subperiodos
        period['subPeriods'] = calculate_sub_periods(
            planet,
            2,
            current_day,
            current_day + duration,
            birth_date,
            planet_order
        )
        
        all_periods.append(period)
        current_day += duration
    
    return all_periods

# Funciones para Relevo Zodiacal
def generar_secuencia(inicio):
    """Genera la secuencia de signos a partir del ascendente."""
    orden = list(SIGNOS.keys())
    idx = orden.index(inicio.lower())
    return orden[idx:] + orden[:idx]

def calcular_relevodPeriods(fecha_nac, ascendente):
    """Calcula periodos de relevo zodiacal."""
    secuencia = generar_secuencia(ascendente)
    dia_actual = 0
    periodos = []
    
    # Asegurar que fecha_nac es un objeto datetime
    if isinstance(fecha_nac, str):
        fecha_nac = datetime.strptime(fecha_nac, '%Y-%m-%d')
    
    for signo in secuencia:
        dias_en_periodo = DURACION_POR_NIVEL[signo] * DURACIONES['AÑO']
        fecha_inicio = calculate_date(fecha_nac, dia_actual)
        fecha_fin = calculate_date(fecha_nac, dia_actual + dias_en_periodo)
        
        periodo = {
            'signo': signo,
            'level': 1,
            'planeta': SIGNOS[signo]['planeta'],
            'start': fecha_inicio.strftime('%Y-%m-%d'),
            'end': fecha_fin.strftime('%Y-%m-%d'),
            'startDay': dia_actual,
            'durationDays': dias_en_periodo
        }
        
        # Calcular subperiodos
        periodo['subPeriods'] = calcular_relevodSubperiodos(
            fecha_nac,
            dia_actual,
            dias_en_periodo,
            secuencia,
            secuencia.index(signo),
            2
        )
        
        periodos.append(periodo)
        dia_actual += dias_en_periodo
    
    return periodos

def calcular_relevodSubperiodos(fecha_nac, dia_inicio, duracion_total, secuencia, idx_inicial, nivel):
    """Calcula subperiodos de relevo zodiacal."""
    if nivel > 4:
        return []
    
    periodos = []
    dia_actual = 0
    unidad_tiempo = 'MES' if nivel == 2 else 'SEMANA' if nivel == 3 else 'DIA'
    duracion_unidad = DURACIONES[unidad_tiempo]
    
    while dia_actual < duracion_total:
        for i in range(len(secuencia)):
            if dia_actual >= duracion_total:
                break
                
            signo = secuencia[(idx_inicial + i) % len(secuencia)]
            duracion_periodo = DURACION_POR_NIVEL[signo] * duracion_unidad
            duracion_real = min(duracion_periodo, duracion_total - dia_actual)
            
            if duracion_real > 0:
                fecha_inicio = calculate_date(fecha_nac, dia_inicio + dia_actual)
                fecha_fin = calculate_date(fecha_nac, dia_inicio + dia_actual + duracion_real)
                
                periodo = {
                    'signo': signo,
                    'level': nivel,
                    'planeta': SIGNOS[signo]['planeta'],
                    'start': fecha_inicio.strftime('%Y-%m-%d'),
                    'end': fecha_fin.strftime('%Y-%m-%d'),
                    'startDay': dia_inicio + dia_actual,
                    'durationDays': duracion_real
                }
                
                if nivel < 4:
                    periodo['subPeriods'] = calcular_relevodSubperiodos(
                        fecha_nac,
                        dia_inicio + dia_actual,
                        duracion_real,
                        secuencia,
                        (idx_inicial + i) % len(secuencia),
                        nivel + 1
                    )
                
                periodos.append(periodo)
                dia_actual += duracion_real
    
    return periodos

def extraer_periodos_nivel(periodos, nivel):
    """Extrae todos los periodos de un nivel específico."""
    resultado = []
    
    def recorrer_periodos(periodo):
        if periodo['level'] == nivel:
            resultado.append(periodo)
        elif 'subPeriods' in periodo and periodo['subPeriods']:
            for subperiodo in periodo['subPeriods']:
                recorrer_periodos(subperiodo)
    
    for periodo in periodos:
        recorrer_periodos(periodo)
    
    return resultado

def buscar_coincidencias(periodos_fardaria, periodos_relevo):
    """
    Busca coincidencias entre periodos de Fardarias y Relevos.
    Devuelve una lista de coincidencias agrupadas por año.
    """
    coincidencias = []
    
    # Extraer periodos de nivel 4 (días)
    dias_fardaria = extraer_periodos_nivel(periodos_fardaria, 4)
    dias_relevo = extraer_periodos_nivel(periodos_relevo, 4)
    
    # Buscar coincidencias
    for fardaria in dias_fardaria:
        for relevo in dias_relevo:
            if fardaria['planet'] == relevo['planeta']:
                # Convertir fechas a objetos datetime
                fardaria_start = datetime.strptime(fardaria['start'], '%Y-%m-%d')
                fardaria_end = datetime.strptime(fardaria['end'], '%Y-%m-%d')
                relevo_start = datetime.strptime(relevo['start'], '%Y-%m-%d')
                relevo_end = datetime.strptime(relevo['end'], '%Y-%m-%d')
                
                # Verificar si hay superposición de fechas
                if fardaria_start <= relevo_end and fardaria_end >= relevo_start:
                    # Calcular periodo de superposición
                    overlap_start = max(fardaria_start, relevo_start)
                    overlap_end = min(fardaria_end, relevo_end)
                    
                    coincidencias.append({
                        'planeta': fardaria['planet'],
                        'signo': relevo['signo'],
                        'fardariaPeriodo': {
                            'start': fardaria['start'],
                            'end': fardaria['end']
                        },
                        'relevoPeriodo': {
                            'start': relevo['start'],
                            'end': relevo['end'],
                            'signo': relevo['signo']
                        },
                        'overlap': {
                            'start': overlap_start.strftime('%Y-%m-%d'),
                            'end': overlap_end.strftime('%Y-%m-%d'),
                            'year': overlap_start.year
                        }
                    })
    
    # Ordenar por año y fecha de inicio
    coincidencias.sort(key=lambda x: (x['overlap']['year'], x['overlap']['start']))
    
    return coincidencias

def get_planet_color(planet, longitude):
    """Determina el color de un planeta según su posición."""
    if planet in ['ASC', 'MC', 'DSC', 'IC']:
        return '#000000'
    
    if planet == 'JÚPITER':
        if (longitude >= 306.00 and longitude <= 360.00) or (longitude >= 0.00 and longitude <= 150.00):
            return COLORS['BLUE']
        if longitude > 150.00 and longitude < 306.00:
            return COLORS['RED']
    
    if planet == 'SATURNO':
        if (longitude >= 330.00 and longitude <= 360.00) or (longitude >= 0.00 and longitude <= 150.00):
            return COLORS['YELLOW']
        if longitude > 240.00 and longitude <= 252.00:
            return COLORS['YELLOW']
        if longitude > 252.00 and longitude <= 330.00:
            return COLORS['RED']
        if longitude > 150.00 and longitude <= 240.00:
            return COLORS['RED']
        return COLORS['YELLOW']
    
    if longitude > 150.00 and longitude <= 330.00:
        if planet in ['SOL', 'MERCURIO', 'URANO']:
            return COLORS['GREEN']
        if planet in ['VENUS', 'LUNA']:
            return COLORS['YELLOW']
        if planet in ['MARTE', 'PLUTÓN']:
            return COLORS['BLUE']
        if planet == 'NEPTUNO':
            return COLORS['RED']
    else:
        if planet in ['SOL', 'MARTE', 'PLUTÓN']:
            return COLORS['RED']
        if planet == 'VENUS':
            return COLORS['GREEN']
        if planet in ['MERCURIO', 'SATURNO', 'URANO']:
            return COLORS['YELLOW']
        if planet in ['LUNA', 'NEPTUNO']:
            return COLORS['BLUE']
    
    return '#000000'

# Rutas del servidor Flask
@app.route('/')
def index():
    """Sirve la página principal."""
    return send_file('index.html')

@app.route('/cities', methods=['GET'])
def cities():
    """Busca ciudades basado en el texto de entrada."""
    ciudad = request.args.get('ciudad', '')
    if not ciudad:
        return jsonify({'error': 'Debes proporcionar una ciudad'}), 400
    
    try:
        # Usar API de Geoapify para autocompletado
        url = f"https://api.geoapify.com/v1/geocode/autocomplete?text={ciudad}&apiKey={API_KEY}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            ciudades = []
            
            if "features" in data:
                for feature in data["features"]:
                    props = feature["properties"]
                    nombre = props.get("formatted", "")
                    lat = props.get("lat")
                    lon = props.get("lon")
                    
                    if nombre:
                        ciudades.append({
                            "nombre": nombre,
                            "lat": lat,
                            "lon": lon
                        })
            
            return jsonify({"ciudades": ciudades})
        
        # Fallback en caso de error
        return jsonify({"ciudades": [
            {"nombre": f"{ciudad}, España", "lat": 40.416, "lon": -3.703},
            {"nombre": f"{ciudad}, México", "lat": 19.432, "lon": -99.133},
            {"nombre": f"{ciudad}, Argentina", "lat": -34.603, "lon": -58.381}
        ]})
    
    except Exception as e:
        print(f"Error al buscar ciudades: {str(e)}")
        return jsonify({"ciudades": [
            {"nombre": f"{ciudad}, España", "lat": 40.416, "lon": -3.703},
            {"nombre": f"{ciudad}, México", "lat": 19.432, "lon": -99.133},
            {"nombre": f"{ciudad}, Argentina", "lat": -34.603, "lon": -58.381}
        ]})

@app.route('/calculate', methods=['POST'])
def calculate():
    """Calcula la carta astral y devuelve los resultados."""
    try:
        data = request.json
        city = data.get('city')
        date = data.get('date')
        time = data.get('time')
        
        if not all([city, date, time]):
            return jsonify({"error": "Faltan datos necesarios"}), 400
        
        # Simulación de cálculo de posiciones planetarias
        positions = mockCalculatePositions(True)
        
        # Obtener ASC y SOL para determinar si es seco o húmedo
        asc_pos = next((p for p in positions if p["name"] == "ASC"), None)
        sun_pos = next((p for p in positions if p["name"] == "SOL"), None)
        
        if asc_pos and sun_pos:
            is_dry = is_dry_birth(sun_pos["longitude"], asc_pos["longitude"])
            
            # Calcular Fardarias
            birth_date = datetime.strptime(date, '%Y-%m-%d')
            fardarias = calculate_fardaria_periods(birth_date, is_dry)
            
            # Calcular Relevo Zodiacal
            signo_asc = asc_pos["sign"].lower()
            signo_map = {
                "ARIES": "aries", "TAURUS": "tauro", "GEMINI": "geminis", "CANCER": "cancer",
                "LEO": "leo", "VIRGO": "virgo", "LIBRA": "libra", "SCORPIO": "escorpio",
                "OPHIUCHUS": "ofiuco", "SAGITTARIUS": "sagitario", "CAPRICORN": "capricornio",
                "AQUARIUS": "acuario", "PISCES": "piscis"
            }
            relevo_signo = signo_map.get(signo_asc, "aries")
            relevos = calcular_relevodPeriods(birth_date, relevo_signo)
            
            # Calcular coincidencias
            coincidencias = buscar_coincidencias(fardarias, relevos)
            
            # Calcular aspectos entre planetas
            aspects = calculate_aspects(positions)
            
            # Construir respuesta
            return jsonify({
                "positions": positions,
                "isDry": is_dry,
                "aspects": aspects,
                "fardarias": fardarias,
                "relevos": relevos,
                "coincidencias": coincidencias
            })
            
        return jsonify({"error": "No se pudo determinar el ASC o SOL"}), 500
        
    except Exception as e:
        print(f"Error en el cálculo: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/calculate_transit', methods=['POST'])
def calculate_transit():
    """Calcula los tránsitos para una fecha específica."""
    try:
        data = request.json
        date = data.get('date')
        
        if not date:
            return jsonify({"error": "Fecha no especificada"}), 400
        
        # Simular posiciones planetarias para la fecha de tránsito
        transit_positions = mockCalculatePositions(False)
        
        return jsonify({
            "positions": transit_positions
        })
        
    except Exception as e:
        print(f"Error en el cálculo de tránsitos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/calculate_coincidence', methods=['POST'])
def calculate_coincidence():
    """Calcula posiciones planetarias para una fecha de coincidencia específica."""
    try:
        data = request.json
        date = data.get('date')
        
        if not date:
            return jsonify({"error": "Fecha no especificada"}), 400
        
        # Simular posiciones planetarias para la fecha de coincidencia
        transit_positions = mockCalculatePositions(False)
        
        # Añadir variación específica basada en la fecha
        try:
            coincidence_date = datetime.strptime(date, '%Y-%m-%d')
            day_of_year = coincidence_date.timetuple().tm_yday
            
            for planet in transit_positions:
                # Hacer una variación determinista basada en la fecha
                planet["longitude"] = (planet["longitude"] + day_of_year) % 360
                planet["sign"] = get_sign(planet["longitude"])
        except:
            pass
        
        return jsonify({
            "positions": transit_positions
        })
        
    except Exception as e:
        print(f"Error en el cálculo de coincidencia: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Detectar si estamos en producción (Render) o desarrollo
    is_prod = os.environ.get('RENDER', False)
    port = int(os.environ.get('PORT', 5000))
    
    if is_prod:
        # En producción, Gunicorn se encargará de ejecutar la app
        print("Servidor configurado para producción con Gunicorn")
    else:
        # En desarrollo, usar el servidor de Flask
        print(f"Iniciando servidor de desarrollo en puerto {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
