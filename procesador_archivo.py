import pandas as pd
import requests
from math import radians, cos, sin, sqrt, atan2


class ProcesadorDatos:
    def __init__(self, generos_interes, api_base_url="https://api.gbif.org/v1"):
        self.generos_interes = generos_interes
        self.api_base_url = api_base_url

    @staticmethod
    def calcular_distancia(lat1, lon1, lat2, lon2):
        """Calcula la distancia entre dos puntos geográficos usando la fórmula de Haversine."""
        R = 6371  # Radio de la Tierra en kilómetros
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c  # Distancia en kilómetros

    def obtener_info_wikipedia(self, nombre_cientifico):
        """Consulta la API de Wikipedia para obtener una descripción general de la planta."""
        url = "https://es.wikipedia.org/api/rest_v1/page/summary/" + nombre_cientifico.replace(" ", "_")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("extract", "Información no disponible en Wikipedia.")
        except requests.exceptions.RequestException as e:
            print(f"Error al consultar Wikipedia: {e}")
            return "Información no disponible."

    def procesar_inaturalist(self, latitud_usuario, longitud_usuario, radio_km=10):
        """Consulta la API de iNaturalist para obtener observaciones cercanas."""
        url = "https://api.inaturalist.org/v1/observations"
        params = {
            "taxon_name": "Plantae",  # Taxonomía de plantas
            "lat": latitud_usuario,
            "lng": longitud_usuario,
            "radius": radio_km,  # Radio en kilómetros
            "per_page": 50  # Máximo número de resultados por página
        }
        plantas = []

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            resultados = response.json().get("results", [])

            for obs in resultados:
                taxon = obs.get("taxon", {})
                nombre_cientifico = taxon.get("name", "Desconocido")
                genero = taxon.get("genus", "Género desconocido")  # EXTRAER GÉNERO
                ubicacion = obs.get("location", "").split(",")
                descripcion = obs.get("description", "Sin descripción")
                fecha_observacion = obs.get("observed_on", "Fecha desconocida")

                if len(ubicacion) == 2:
                    planta_latitud = float(ubicacion[0])
                    planta_longitud = float(ubicacion[1])

                    distancia = self.calcular_distancia(
                        latitud_usuario, longitud_usuario,
                        planta_latitud, planta_longitud
                    )
                else:
                    distancia = "Desconocida"

                descripcion_wikipedia = self.obtener_info_wikipedia(nombre_cientifico)

                plantas.append({
                    "nombre_cientifico": nombre_cientifico,
                    "genero": genero,  # INCLUIMOS EL GÉNERO CORRECTO
                    "latitud": planta_latitud if 'planta_latitud' in locals() else "Desconocida",
                    "longitud": planta_longitud if 'planta_longitud' in locals() else "Desconocida",
                    "descripcion": descripcion,
                    "descripcion_wikipedia": descripcion_wikipedia,
                    "distancia": distancia,
                    "fecha_observacion": fecha_observacion
                })

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar iNaturalist: {e}")

        return pd.DataFrame(plantas)
