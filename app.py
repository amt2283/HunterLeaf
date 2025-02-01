from flask import Flask, request, render_template, redirect, url_for, flash
from procesador_archivo import ProcesadorDatos
from base_de_datos import BaseDeDatos
from geopy.geocoders import Nominatim
import json
import requests

app = Flask(__name__)
app.secret_key = 'una_clave_secreta'  # Necesario para usar mensajes flash

# Inicializar variables globales
db = BaseDeDatos()
db.initialize()

def cargar_grupos():
    with open('grupos_plantas.json', 'r', encoding='utf-8') as f:
        return json.load(f)

GENEROS_INTERES = cargar_grupos()

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

@app.route('/buscar', methods=['POST'])
def buscar():
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

        # Consultar la API de iNaturalist
        procesador = ProcesadorDatos(generos_seleccionados)
        plantas = procesador.procesar_inaturalist(latitud, longitud)

        if not plantas:
            flash("No se encontraron plantas válidas en la ubicación especificada.", "info")
            return render_template('resultados.html', plantas=[], latitud=latitud, longitud=longitud, genero_seleccionado=generos_seleccionados[0])

        # Agregar descripciones de Wikipedia
        for planta in plantas:
            planta["descripcion_wikipedia"] = obtener_descripcion_wikipedia(planta["nombre_cientifico"])
            planta["latitud"] = round(planta["latitud"], 3)  # Redondear latitud
            planta["longitud"] = round(planta["longitud"], 3)  # Redondear longitud

        # Eliminar duplicados
        plantas_unicas = []
        vistas = set()
        for planta in plantas:
            clave = (planta["nombre_cientifico"], planta["latitud"], planta["longitud"])
            if clave not in vistas:
                vistas.add(clave)
                plantas_unicas.append(planta)

        return render_template('resultados.html', plantas=plantas_unicas, latitud=round(latitud, 3), longitud=round(longitud, 3), genero_seleccionado=generos_seleccionados[0])

    except ValueError:
        flash("Por favor, ingrese valores numéricos válidos para latitud y longitud.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Ocurrió un error inesperado: {str(e)}", "error")
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
