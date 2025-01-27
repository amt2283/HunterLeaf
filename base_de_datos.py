import sqlite3
import pandas as pd

class BaseDeDatos:
    def __init__(self, db_file='plantas.db'):
        self.db_file = db_file

    def initialize(self):
        """Crea la tabla en la base de datos si no existe."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grupos_plantas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_cientifico TEXT,
                nombre_comun TEXT,
                familia TEXT,
                genero TEXT,
                descripcion TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def importar_datos_iniciales(self, ruta_csv):
        """Importa datos iniciales desde un archivo CSV."""
        try:
            df = pd.read_csv(ruta_csv)
            conn = sqlite3.connect(self.db_file)
            df.to_sql('grupos_plantas', conn, if_exists='replace', index=False)
            conn.commit()
            conn.close()
            print(f"Datos iniciales importados desde {ruta_csv}.")
        except Exception as e:
            print(f"Error al importar datos iniciales: {e}")

    def importar_datos(self, df):
        """Importa un DataFrame a la tabla de SQLite."""
        conn = sqlite3.connect(self.db_file)
        if not df.empty:
            df.to_sql('grupos_plantas', conn, if_exists='append', index=False)
            print("Datos importados exitosamente a la base de datos.")
        else:
            print("No se encontraron datos válidos para importar.")
        conn.commit()
        conn.close()

    def obtener_grupos(self, filtro=None):
        """Devuelve los nombres científicos de los grupos en la base de datos."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        if filtro:
            query = "SELECT nombre_cientifico FROM grupos_plantas WHERE genero = ?"
            cursor.execute(query, (filtro,))
        else:
            query = "SELECT DISTINCT genero FROM grupos_plantas"
            cursor.execute(query)
        grupos = [row[0] for row in cursor.fetchall()]
        conn.close()
        return grupos
