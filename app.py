from flask import Flask, request, render_template, redirect, url_for, flash
from procesador_archivo import ProcesadorDatos
from base_de_datos import BaseDeDatos
import json
app = Flask(__name__)
app.secret_key = 'una_clave_secreta'  # Necesario para usar mensajes flash

# Inicializar variables globales
GENEROS_INTERES = ['Alga', 'Hongo', 'Líquen', 'Briófito', 'Pteridófito']
db = BaseDeDatos()
db.initialize()


@app.route('/')
def home():
    return render_template('index.html', generos=GENEROS_INTERES)


@app.route('/buscar', methods=['POST'])
def buscar():
    try:
        # Validar y obtener datos del formulario
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        generos_seleccionados = request.form.getlist('generos')  # Captura géneros seleccionados

        if not latitud or not longitud:
            flash("Por favor, ingrese latitud y longitud válidas.", "error")
            return redirect(url_for('home'))

        if not generos_seleccionados:
            flash("Por favor, seleccione al menos un género de interés.", "error")
            return redirect(url_for('home'))

        latitud = float(latitud)
        longitud = float(longitud)

        # Consultar la API de iNaturalist
        procesador = ProcesadorDatos(generos_seleccionados)
        df_api = procesador.procesar_inaturalist(latitud, longitud)

        if df_api.empty:
            flash("No se encontraron plantas en la ubicación especificada.", "info")
            return render_template('resultados.html', plantas=[], latitud=latitud, longitud=longitud)

        # Convertir resultados a diccionario
        plantas = df_api.to_dict(orient='records')
        return render_template('resultados.html', plantas=plantas, latitud=latitud, longitud=longitud)

    except ValueError:
        flash("Por favor, ingrese valores numéricos válidos para latitud y longitud.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Ocurrió un error inesperado: {str(e)}", "error")
        return redirect(url_for('home'))
    
def cargar_grupos():
    with open('C:/Users/AMT22/phyton/paginaweb/grupos_plantas.json', 'r', encoding='utf-8') as f:

        return json.load(f)

GENEROS_INTERES = cargar_grupos()
if __name__ == '__main__':
    app.run(debug=True)
