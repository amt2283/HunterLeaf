import requests
from math import radians, cos, sin, sqrt, atan2

class ProcesadorDatos:
    def __init__(self, generos_interes, api_base_url="https://api.inaturalist.org/v1"):
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

    @staticmethod
    def extraer_genero(nombre_cientifico):
        """Extrae el género del nombre científico."""
        if nombre_cientifico and " " in nombre_cientifico:  # Verifica si es un nombre de especie
            return nombre_cientifico.split()[0]
        return "Desconocido"

    @staticmethod
    def es_nombre_cientifico_valido(nombre_cientifico):
        """Verifica si el nombre científico es válido (género y especie)."""
        return nombre_cientifico and " " in nombre_cientifico

    def procesar_inaturalist(self, latitud_usuario, longitud_usuario, radio_km=10):
        """Consulta la API de iNaturalist para obtener observaciones cercanas."""
        url = f"{self.api_base_url}/observations"
        plantas = []

        try:
            for genero in self.generos_interes:
                params = {
                    "taxon_name": genero,  # Filtrar por género
                    "lat": latitud_usuario,
                    "lng": longitud_usuario,
                    "radius": radio_km,  # Radio en kilómetros
                    "per_page": 50  # Máximo número de resultados por página
                }

                # Realizar la solicitud a la API
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                resultados = response.json().get("results", [])

                for obs in resultados:
                    taxon = obs.get("taxon", {})
                    nombre_cientifico = taxon.get("name", "Desconocido")
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

                    # Filtrar solo nombres científicos válidos
                    if self.es_nombre_cientifico_valido(nombre_cientifico):
                        plantas.append({
                            "nombre_cientifico": nombre_cientifico,
                            "genero": self.extraer_genero(nombre_cientifico),
                            "latitud": planta_latitud if 'planta_latitud' in locals() else "Desconocida",
                            "longitud": planta_longitud if 'planta_longitud' in locals() else "Desconocida",
                            "descripcion": descripcion,
                            "distancia": distancia,
                            "fecha_observacion": fecha_observacion
                        })

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar iNaturalist: {e}")

        return plantas
