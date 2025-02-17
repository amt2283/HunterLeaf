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
        dlon = radians(lon1 - lon2)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def obtener_info_wikipedia(self, nombre_cientifico):
        """Consulta la API de Wikipedia para obtener una descripción general del taxón.
        Si no se encuentra la información, retorna una cadena vacía."""
        base_url = "https://es.wikipedia.org/api/rest_v1/page/summary/"
        url = base_url + nombre_cientifico.replace(" ", "_")
        try:
            response = requests.get(url, timeout=10)
            # Si la página no existe, se intenta una búsqueda alternativa
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
                    # Tomar el título del primer resultado de búsqueda
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
            print(f"Error al consultar Wikipedia: {e}")
            return ""

    def procesar_inaturalist(self, latitud_usuario, longitud_usuario, radio_km=10):
        """Consulta la API de iNaturalist para obtener observaciones cercanas."""
        url = "https://api.inaturalist.org/v1/observations"
        params = {
            "taxon_name": "Plantae",  # Taxonomía de plantas
            "lat": latitud_usuario,
            "lng": longitud_usuario,
            "radius": radio_km,
            "per_page": 50
        }
        plantas = []
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            resultados = response.json().get("results", [])
            print(f"Observaciones recibidas: {len(resultados)}")  # Depuración

            for obs in resultados:
                taxon = obs.get("taxon", {})
                nombre_cientifico = taxon.get("name", "Desconocido")
                ubicacion = obs.get("location", "")
                descripcion = obs.get("description", "Sin descripción")
                fecha_observacion = obs.get("observed_on", "Fecha desconocida")

                # Extraer coordenadas
                planta_latitud = None
                planta_longitud = None
                if "latitude" in obs and "longitude" in obs and obs["latitude"] and obs["longitude"]:
                    try:
                        planta_latitud = float(obs["latitude"])
                        planta_longitud = float(obs["longitude"])
                    except ValueError:
                        planta_latitud = planta_longitud = None
                elif ubicacion and "," in ubicacion:
                    partes = ubicacion.split(",")
                    if len(partes) >= 2:
                        try:
                            planta_latitud = float(partes[0].strip())
                            planta_longitud = float(partes[1].strip())
                        except ValueError:
                            planta_latitud = planta_longitud = None

                if planta_latitud is not None and planta_longitud is not None:
                    distancia = self.calcular_distancia(
                        latitud_usuario, longitud_usuario, planta_latitud, planta_longitud
                    )
                else:
                    distancia = "Desconocida"

                descripcion_wikipedia = self.obtener_info_wikipedia(nombre_cientifico)
                
                # Intentar obtener imagen genérica del taxón desde la propiedad "default_photo"
                foto = taxon.get("default_photo")
                if foto:
                    imagen_generica = foto.get("medium_url") or foto.get("square_url") or "https://via.placeholder.com/100?text=No+Image"
                else:
                    imagen_generica = "https://via.placeholder.com/100?text=No+Image"

                plantas.append({
                    "nombre_cientifico": nombre_cientifico,
                    "latitud": planta_latitud if planta_latitud is not None else "Desconocida",
                    "longitud": planta_longitud if planta_longitud is not None else "Desconocida",
                    "descripcion": descripcion,
                    "descripcion_wikipedia": descripcion_wikipedia,
                    "distancia": distancia,
                    "fecha_observacion": fecha_observacion,
                    "imagen_generica": imagen_generica
                })
        except requests.exceptions.RequestException as e:
            print(f"Error al consultar iNaturalist: {e}")

        return pd.DataFrame(plantas)
