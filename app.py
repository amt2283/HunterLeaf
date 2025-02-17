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

# Instancia del agregador para búsqueda por área (bounding box)
aggregator = AreaDataAggregator(generos_interes=GENEROS_INTERES)

# Función para obtener coordenadas desde una dirección
def obtener_coordenadas(direccion):
    geolocalizador = Nominatim(user_agent="plantfinder_app")
    ubicacion = geolocalizador.geocode(direccion, timeout=15)
    if ubicacion:
        return ubicacion.latitude, ubicacion.longitude
    return None, None

# Función para obtener descripción de Wikipedia con manejo de errores.
def obtener_descripcion_wikipedia(nombre_cientifico):
    """Consulta la API de Wikipedia para obtener una descripción general del taxón.
    Si no se encuentra la información, retorna una cadena vacía."""
    base_url = "https://es.wikipedia.org/api/rest_v1/page/summary/"
    url = base_url + nombre_cientifico.replace(" ", "_")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            print(f"Página no encontrada para '{nombre_cientifico}'. Se intentará una búsqueda...")
            search_url = "https://es.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": nombre_cientifico,
                "format": "json"
            }
            search_response = requests.get(search_url, params=params, timeout=10)
            search_response.raise_for_status()
            search_data = search_response.json()
            search_results = search_data.get("query", {}).get("search", [])
            if search_results:
                title = search_results[0]["title"]
                url = base_url + title.replace(" ", "_")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                return data.get("extract", "")
            else:
                print(f"No se encontraron resultados de búsqueda para '{nombre_cientifico}'.")
                return ""
        else:
            response.raise_for_status()
            data = response.json()
            return data.get("extract", "")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener descripción de Wikipedia: {e}")
        return ""

@app.route('/')
def home():
    return render_template('index.html', generos=GENEROS_INTERES)

# Ruta para búsqueda (POST)
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

        # Si se ingresa dirección, se obtienen coordenadas; de lo contrario se usan las ingresadas
        if direccion:
            latitud, longitud = obtener_coordenadas(direccion)
            if latitud is None or longitud is None:
                flash("No se encontraron coordenadas para la dirección proporcionada.", "error")
                return redirect(url_for('home'))
        elif not latitud or not longitud:
            flash("Por favor, ingrese una dirección o latitud y longitud válidas.", "error")
            return redirect(url_for('home'))

        latitud, longitud = float(latitud), float(longitud)

        # Consultar la API de iNaturalist
        procesador = ProcesadorDatos(generos_interes=generos_seleccionados)
        df_plantas = procesador.procesar_inaturalist(latitud, longitud)
        plantas = df_plantas.to_dict(orient="records")

        if not plantas:
            flash("No se encontraron plantas válidas en la ubicación especificada.", "info")
            return render_template('resultados.html', plantas=[], latitud=latitud, longitud=longitud, genero_seleccionado=generos_seleccionados[0])

        # Procesar cada observación: agregar descripción de Wikipedia y otros ajustes
        for planta in plantas:
            planta["descripcion_wikipedia"] = obtener_descripcion_wikipedia(planta["nombre_cientifico"])
            # Si no existe imagen, asignamos un placeholder
            if "imagen_generica" not in planta or not planta["imagen_generica"]:
                planta["imagen_generica"] = "https://via.placeholder.com/100?text=No+Image"
            try:
                planta["latitud"] = round(float(planta["latitud"]), 3)
            except:
                planta["latitud"] = planta["latitud"]
            try:
                planta["longitud"] = round(float(planta["longitud"]), 3)
            except:
                planta["longitud"] = planta["longitud"]

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
        fuente = request.args.get('fuente', 'inaturalist')
    except (TypeError, ValueError):
        flash("Error en las coordenadas proporcionadas.", "error")
        return redirect(url_for('seleccionar_area'))
    
    center_lat = (sw_lat + ne_lat) / 2
    center_lng = (sw_lng + ne_lng) / 2

    order_date = request.args.get('order_date', 'desc')
    source_filter = request.args.get('source_filter', 'mixta')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    plantas = aggregator.obtener_datos_area(sw_lat, sw_lng, ne_lat, ne_lng, fuente)
    
    print(f"Total de observaciones sin filtrar: {len(plantas)}")
    print("Generos obtenidos en las observaciones:")
    for planta in plantas:
        print(planta.get("genero"))
    print("Generos de interés:")
    print(GENEROS_INTERES)
    print(f"Observaciones después del filtrado: {len(plantas)}")

    for planta in plantas:
        if "fuente" not in planta:
            if planta.get("descripcion", "Sin descripción") == "Sin descripción":
                planta["fuente"] = "iNaturalist"
            else:
                planta["fuente"] = "GBIF"
    
    if source_filter != 'mixta':
        plantas = [p for p in plantas if p.get("fuente") == source_filter]

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
