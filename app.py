from flask import Flask, request, render_template, redirect, url_for, flash
from procesador_archivo import ProcesadorDatos
from base_de_datos import BaseDeDatos
from geopy.geocoders import Nominatim
import json
import requests
from area_data import AreaDataAggregator
from datetime import datetime
import math

app = Flask(__name__)
app.secret_key = 'una_clave_secreta'  # Necesario para usar mensajes flash

# Inicializar variables globales
db = BaseDeDatos()
db.initialize()

def cargar_grupos():
    """
    Carga la lista de géneros de interés desde el archivo JSON.
    Si el JSON tiene una estructura de diccionario, se extrae la lista
    asumiendo que está bajo la llave "plantas".
    """
    with open('grupos_plantas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("plantas", [])
    return data

GENEROS_INTERES = cargar_grupos()

# Instancia del agregador para búsqueda por área
aggregator = AreaDataAggregator(generos_interes=GENEROS_INTERES)

# Función para obtener coordenadas desde una dirección
def obtener_coordenadas(direccion):
    geolocalizador = Nominatim(user_agent="plantfinder_app")
    ubicacion = geolocalizador.geocode(direccion, timeout=15)
    if ubicacion:
        return ubicacion.latitude, ubicacion.longitude
    return None, None

# Función para obtener descripción de Wikipedia
def obtener_descripcion_wikipedia(nombre_cientifico):
    try:
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{nombre_cientifico.replace(' ', '_')}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("extract", "Descripción no disponible.")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener descripción de Wikipedia: {e}")
        return "Descripción no disponible."

@app.route('/')
def home():
    return render_template('index.html', generos=GENEROS_INTERES)

# Búsqueda por dirección (POST)
@app.route('/buscar', methods=['POST'])
def buscar_direccion():
    try:
        direccion = request.form.get('direccion')
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        generos_seleccionados = request.form.getlist('generos')
        
        if not generos_seleccionados:
            flash("Por favor, seleccione al menos un género de interés.", "error")
            return redirect(url_for('home'))

        if direccion:
            latitud, longitud = obtener_coordenadas(direccion)
            if latitud is None or longitud is None:
                flash("No se encontraron coordenadas para la dirección proporcionada.", "error")
                return redirect(url_for('home'))
        elif not latitud or not longitud:
            flash("Por favor, ingrese una dirección o latitud y longitud válidas.", "error")
            return redirect(url_for('home'))

        latitud, longitud = float(latitud), float(longitud)

        # Consultar la API de iNaturalist (este código sigue funcionando como antes)
        procesador = ProcesadorDatos(generos_seleccionados)
        plantas = procesador.procesar_inaturalist(latitud, longitud)

        if not plantas:
            flash("No se encontraron plantas válidas en la ubicación especificada.", "info")
            return render_template('resultados.html', plantas=[], latitud=latitud, longitud=longitud, genero_seleccionado=generos_seleccionados[0])

        # Agregar descripciones de Wikipedia y redondear coordenadas
        for planta in plantas:
            planta["descripcion_wikipedia"] = obtener_descripcion_wikipedia(planta["nombre_cientifico"])
            planta["latitud"] = round(planta["latitud"], 3)
            planta["longitud"] = round(planta["longitud"], 3)

        # Eliminar duplicados
        plantas_unicas = []
        vistas = set()
        for planta in plantas:
            clave = (planta["nombre_cientifico"], planta["latitud"], planta["longitud"])
            if clave not in vistas:
                vistas.add(clave)
                plantas_unicas.append(planta)

        return render_template('resultados.html', 
                               plantas=plantas_unicas, 
                               latitud=round(latitud, 3), 
                               longitud=round(longitud, 3), 
                               genero_seleccionado=generos_seleccionados[0])

    except ValueError:
        flash("Por favor, ingrese valores numéricos válidos para latitud y longitud.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Ocurrió un error inesperado: {str(e)}", "error")
        return redirect(url_for('home'))

# Búsqueda por área (GET) con ordenación, filtrado por fuente y paginación
@app.route('/buscar_area', methods=['GET'])
def buscar_area():
    try:
        sw_lat = float(request.args.get('swlat'))
        sw_lng = float(request.args.get('swlng'))
        ne_lat = float(request.args.get('nelat'))
        ne_lng = float(request.args.get('nelng'))
    except (TypeError, ValueError):
        flash("Error en las coordenadas proporcionadas.", "error")
        return redirect(url_for('seleccionar_area'))
    
    # Calcular el centro del área para centrar el mapa
    center_lat = (sw_lat + ne_lat) / 2
    center_lng = (sw_lng + ne_lng) / 2

    # Parámetros opcionales para orden y filtrado:
    order_date = request.args.get('order_date', 'desc')
    source_filter = request.args.get('source_filter', 'mixta')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    # Obtener todos los resultados de ambas fuentes
    plantas = aggregator.obtener_datos_area(sw_lat, sw_lng, ne_lat, ne_lng)
    
    # Mostrar en consola el total de observaciones obtenidas
    print(f"Total de observaciones sin filtrar: {len(plantas)}")

    # (Opcional) Imprime en consola los géneros obtenidos y los géneros de interés para depurar
    print("Generos obtenidos en las observaciones:")
    for planta in plantas:
        print(planta.get("genero"))
    print("Generos de interés:")
    print(GENEROS_INTERES)

    # Filtrar para que solo se incluyan plantas (comparando en minúsculas)
    
    print(f"Observaciones después del filtrado: {len(plantas)}")

    # Asignar la fuente si no está presente
    for planta in plantas:
        if "fuente" not in planta:
            if planta.get("descripcion", "Sin descripción") == "Sin descripción":
                planta["fuente"] = "iNaturalist"
            else:
                planta["fuente"] = "GBIF"
    
    # Filtrar por fuente si se selecciona una en particular
    if source_filter != 'mixta':
        plantas = [p for p in plantas if p.get("fuente") == source_filter]

    # Ordenar por fecha de observación
    def get_fecha(p):
        fecha_str = p.get("fecha_observacion", "Fecha desconocida")
        try:
            return datetime.strptime(fecha_str, "%Y-%m-%d")
        except Exception:
            return None

    def sort_key(p):
        fecha = get_fecha(p)
        if fecha is None:
            return (1, datetime.min)
        else:
            return (0, fecha)

    reverse_order = True if order_date == 'desc' else False
    plantas.sort(key=sort_key, reverse=reverse_order)

    # Paginación: mostrar 20 resultados por página
    PER_PAGE = 20
    total = len(plantas)
    total_pages = math.ceil(total / PER_PAGE)
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    plantas_pag = plantas[start:end]

    return render_template('resultado_area.html', 
                           plantas=plantas_pag,
                           swlat=sw_lat,
                           swlng=sw_lng,
                           nelat=ne_lat,
                           nelng=ne_lng,
                           center_lat=center_lat,
                           center_lng=center_lng,
                           page=page,
                           total_pages=total_pages,
                           order_date=order_date,
                           source_filter=source_filter)

@app.route('/seleccionar_area')
def seleccionar_area():
    return render_template('seleccionar_area.html')

if __name__ == '__main__':
    app.run(debug=True)
