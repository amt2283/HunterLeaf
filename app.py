from flask import Flask, request, render_template, redirect, url_for, flash
from procesador_archivo import ProcesadorDatos
from base_de_datos import BaseDeDatos
from geopy.geocoders import Nominatim
import json
import requests
from area_data import AreaDataAggregator
from datetime import datetime
import math

app = Flask(__name__, template_folder=r"C:\Users\AMT22\phyton\paginaweb\templates")
app.secret_key = 'una_clave_secreta'  # Necesario para usar mensajes flash

# Inicializar variables globales
db = BaseDeDatos()
db.initialize()

def cargar_categorias():
    """
    Carga las categorías (grupos) y sus géneros desde el archivo JSON.
    Retorna dos estructuras:
      1. Una lista de nombres de grupos (categorías) para el frontend.
      2. Un diccionario que mapea cada grupo a una lista de géneros (aplanando las familias).
    """
    with open('grupos_plantas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    categorias = {}
    nombres_categorias = []
    
    # Iterar sobre los grupos definidos en la clave "plant_groups"
    for grupo in data.get("plant_groups", []):
        grupo_nombre = grupo.get("grupo", "Sin grupo")
        nombres_categorias.append(grupo_nombre)
        generos = []
        # Recorremos las familias dentro del grupo y acumulamos sus géneros
        for familia in grupo.get("familias", []):
            generos.extend(familia.get("generos", []))
        categorias[grupo_nombre] = generos
    
    return nombres_categorias, categorias

# Cargar datos al iniciar la app
CATEGORIAS_NOMBRES, CATEGORIAS = cargar_categorias()

# Cargar la data completa de grupos (lista de diccionarios) para pasar a la plantilla
with open('grupos_plantas.json', 'r', encoding='utf-8') as f:
    GRUPOS_DATA = json.load(f)

# Instancia del agregador para búsqueda por área (bounding box)
CATEGORIA_POR_DEFECTO = CATEGORIAS_NOMBRES[0] if CATEGORIAS_NOMBRES else ""
aggregator = AreaDataAggregator(generos_interes=CATEGORIAS.get(CATEGORIA_POR_DEFECTO, []))

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
    # Se pasan las categorías y la data completa de grupos a la plantilla
    return render_template('index.html', 
                           categorias=CATEGORIAS_NOMBRES, 
                           grupos=GRUPOS_DATA)

# Modificada la función buscar_direccion para validar correctamente las coordenadas de las plantas
@app.route('/buscar', methods=['POST'])
def buscar_direccion():
    try:
        direccion = request.form.get('direccion')
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        categoria_seleccionada = request.form.get('categoria')
        genero_seleccionado = request.form.get('genero', None)
        radio = request.form.get('radio')
        try:
            radio = float(radio)
        except (ValueError, TypeError):
            radio = 10  # Valor por defecto
        
        # Depuración: Imprimir valores iniciales
        print(f"Valores iniciales - Dirección: '{direccion}', Latitud: '{latitud}', Longitud: '{longitud}', Radio: '{radio}'")
        
        # Si se proporcionan coordenadas, convertir comas a puntos
        if latitud and longitud:
            latitud = float(latitud.replace(',', '.'))
            longitud = float(longitud.replace(',', '.'))
            print(f"Coordenadas convertidas: Latitud = {latitud}, Longitud = {longitud}")
        elif direccion:
            latitud, longitud = obtener_coordenadas(direccion)
            print(f"Coordenadas obtenidas de dirección: Latitud = {latitud}, Longitud = {longitud}")
            if latitud is None or longitud is None:
                flash("No se encontraron coordenadas para la dirección proporcionada.", "error")
                return redirect(url_for('home'))
        else:
            flash("Por favor, ingrese una dirección o coordenadas válidas.", "error")
            return redirect(url_for('home'))
        
        # Verificar que las coordenadas son números válidos
        try:
            latitud = float(latitud)
            longitud = float(longitud)
            print(f"Coordenadas finales para búsqueda: Latitud = {latitud}, Longitud = {longitud}")
        except (ValueError, TypeError) as e:
            print(f"Error al convertir coordenadas finales: {e}")
            flash("Error en el formato de las coordenadas. Asegúrese de que sean números válidos.", "error")
            return redirect(url_for('home'))

        # Crear el procesador con la categoría y opcionalmente el género
        procesador = ProcesadorDatos(
            categoria=categoria_seleccionada,
            genero=genero_seleccionado
        )
        
        # Procesar la búsqueda con un radio específico
        df_plantas = procesador.procesar_inaturalist(latitud, longitud, radio=radio)
        
        if df_plantas.empty:
            flash("No se encontraron plantas en la ubicación especificada.", "info")
            return render_template('resultados.html', 
                                   plantas=[], 
                                   latitud=latitud, 
                                   longitud=longitud,
                                   categoria_seleccionada=categoria_seleccionada,
                                   genero_seleccionado=genero_seleccionado)

        # Convertir DataFrame a lista de diccionarios
        plantas = []
        for _, row in df_plantas.iterrows():
            coords_str = row.get('coordenadas', '')
            # Verificar que exista un string válido en 'coordenadas'
            if not coords_str or not isinstance(coords_str, str):
                print(f"Registro omitido por falta de coordenadas válidas: {row.get('nombre', 'Sin nombre')}")
                continue
            coords = coords_str.split(',')
            if len(coords) < 2:
                print(f"Registro omitido por formato incorrecto de coordenadas: {coords_str}")
                continue
            try:
                planta_lat = float(coords[0].strip())
                planta_lon = float(coords[1].strip())
            except (ValueError, IndexError):
                print(f"Registro omitido por error en la conversión de coordenadas: {coords_str}")
                continue

            # Omitir registros con coordenadas (0,0)
            if planta_lat == 0.0 and planta_lon == 0.0:
                print(f"Registro omitido por coordenadas nulas (0,0): {row.get('nombre', 'Sin nombre')}")
                continue

            planta = {
                "nombre_cientifico": row['nombre'],
                "nombre_comun": row.get('nombre_comun', 'N/A'),
                "distancia": row['distancia'],
                "fecha_observacion": row['fecha'],
                "imagen_generica": row['imagen'],
                "latitud": planta_lat,
                "longitud": planta_lon,
                "descripcion_wikipedia": obtener_descripcion_wikipedia(row['nombre'])
            }
            plantas.append(planta)

        return render_template('resultados.html', 
                               plantas=plantas,
                               latitud=latitud,
                               longitud=longitud,
                               categoria_seleccionada=categoria_seleccionada,
                               genero_seleccionado=genero_seleccionado)

    except ValueError as e:
        print(f"Error de valor: {str(e)}")
        flash("Error en el formato de las coordenadas. Use punto decimal en lugar de coma.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
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
    print("Categorías disponibles:", CATEGORIAS.keys())
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
