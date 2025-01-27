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
            # Realizar la solicitud a la API
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            # Mostrar la respuesta de la API para depuración
            print("Respuesta de la API:", response.json())

            resultados = response.json().get("results", [])

            for obs in resultados:
                taxon = obs.get("taxon", {})
                nombre_cientifico = taxon.get("name", "Desconocido")
                ubicacion = obs.get("location", "").split(",")
                descripcion = obs.get("description", "Sin descripción")

                if len(ubicacion) == 2:
                    planta_latitud = float(ubicacion[0])
                    planta_longitud = float(ubicacion[1])

                    distancia = self.calcular_distancia(
                        latitud_usuario, longitud_usuario,
                        planta_latitud, planta_longitud
                    )
                else:
                    distancia = "Desconocida"

                plantas.append({
                    "nombre_cientifico": nombre_cientifico,
                    "latitud": planta_latitud if 'planta_latitud' in locals() else "Desconocida",
                    "longitud": planta_longitud if 'planta_longitud' in locals() else "Desconocida",
                    "descripcion": descripcion,
                    "distancia": distancia
                })

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar iNaturalist: {e}")

        return pd.DataFrame(plantas)
