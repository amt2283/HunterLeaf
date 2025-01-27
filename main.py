from flask import Flask, request, render_template
from procesador_archivo import ProcesadorDatos
from base_de_datos import BaseDeDatos

app = Flask(__name__)

# Inicializar variables globales
GENEROS_INTERES = ['Alga', 'Hongo', 'Líquen', 'Briófito', 'Pteridófito']
db = BaseDeDatos()
db.initialize()

@app.route('/')
def home():
    return render_template('index.html', generos=GENEROS_INTERES)

@app.route('/buscar', methods=['POST'])
def buscar():
    # Obtener datos del formulario
    genero = request.form['genero']
    latitud = float(request.form['latitud'])
    longitud = float(request.form['longitud'])

    # Procesar datos desde la API
    procesador = ProcesadorDatos([genero])
    df_api = procesador.procesar_api()

    # Mostrar resultados
    plantas = df_api.to_dict(orient='records')
    return render_template('resultados.html', plantas=plantas, latitud=latitud, longitud=longitud)

if __name__ == '__main__':
    app.run(debug=True)
