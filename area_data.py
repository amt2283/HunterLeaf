import os
import requests
from math import radians, cos, sin, sqrt, atan2
from dotenv import load_dotenv  # Opcional: solo si quieres cargar un archivo .env

base_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_dir, "api-keys.env")

# Cargar variables de entorno desde un archivo .env (solo en desarrollo)
load_dotenv("api-keys.env")
print("TREFLE_API_KEY:", os.environ.get("TREFLE_API_KEY"))

class AreaDataAggregator:
    def __init__(self, generos_interes,
                 inaturalist_api_base_url="https://api.inaturalist.org/v1",
                 plantnet_api_base_url="https://api.plantnet.org/v2",
                 trefle_api_base_url="https://trefle.io/api/v1"):
        """
        Inicializa el agregador con la lista de géneros de interés y las URLs base de las APIs.
        Se ha reemplazado USDA/GBIF por Trefle, y se obtienen las API keys desde variables de entorno.
        """
        self.generos_interes = generos_interes
        self.inaturalist_api_base_url = inaturalist_api_base_url
        self.plantnet_api_base_url = plantnet_api_base_url
        self.trefle_api_base_url = trefle_api_base_url
        
        # Obtener las claves de las variables de entorno; si no están definidas, se usa cadena vacía
        self.plantnet_api_key = os.environ.get("PLANTNET_API_KEY", "")
        self.trefle_api_key = os.environ.get("TREFLE_API_KEY", "")
        
        self.imagen_generica_cache = {}

    @staticmethod
    def extraer_genero(nombre_cientifico):
        if not nombre_cientifico or nombre_cientifico == "Desconocido":
            return "Desconocido"
        partes = nombre_cientifico.split()
        return partes[0].strip().capitalize() if partes else "Desconocido"

    @staticmethod
    def es_nombre_cientifico_valido(nombre_cientifico):
        return bool(nombre_cientifico and nombre_cientifico != "Desconocido")

    def obtener_imagen_generica(self, genero):
        if genero in self.imagen_generica_cache:
            return self.imagen_generica_cache[genero]

        headers = {'User-Agent': 'TuApp/1.0'}
        try:
            response = requests.get(
                f"{self.inaturalist_api_base_url}/taxa",
                params={"q": genero, "per_page": 1},
                headers=headers,
                timeout=10
            )
            if response.ok:
                resultados = response.json().get("results", [])
                if resultados:
                    default_photo = resultados[0].get("default_photo")
                    if default_photo:
                        imagen_url = (default_photo.get("medium_url") or 
                                      default_photo.get("square_url") or 
                                      "https://via.placeholder.com/100?text=No+Image")
                        self.imagen_generica_cache[genero] = imagen_url
                        return imagen_url
        except Exception as e:
            print(f"Error obteniendo imagen para {genero}: {e}")

        default_img = "https://via.placeholder.com/100?text=No+Image"
        self.imagen_generica_cache[genero] = default_img
        return default_img

    def procesar_inaturalist(self, swlat, swlng, nelat, nelng):
        plantas = []
        headers = {'User-Agent': 'TuApp/1.0'}
        for genero in self.generos_interes:
            params = {
                "taxon_name": genero,
                "per_page": 50,
                "swlat": swlat,
                "swlng": swlng,
                "nelat": nelat,
                "nelng": nelng,
                "fields": "taxon,observed_on,description,identifications_count,quality_grade,latitude,longitude,location",
                "iconic_taxa[]": "Plantae",  # Filtra solo observaciones de plantas
                "order": "desc",            # Ordena resultados (más recientes primero)
                "order_by": "created_at"
            }
            try:
                response = requests.get(
                    f"{self.inaturalist_api_base_url}/observations",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                resultados = response.json().get("results", [])
                print(f"Observaciones para '{genero}' en iNaturalist: {len(resultados)}")
                for obs in resultados:
                    # Verificar que el objeto 'taxon' exista y que iconic_taxon_name esté definido y sea 'Plantae'
                    taxon = obs.get("taxon", {})
                    if not taxon:
                        continue
                    if taxon.get("iconic_taxon_name", "").lower() != "plantae":
                        continue

                    nombre_cientifico = taxon.get("name", "Desconocido")
                    if not self.es_nombre_cientifico_valido(nombre_cientifico):
                        continue

                    planta_lat = obs.get("latitude")
                    planta_lng = obs.get("longitude")
                    if planta_lat is None or planta_lng is None:
                        loc = obs.get("location", "")
                        if loc and "," in loc:
                            try:
                                planta_lat, planta_lng = map(float, loc.split(","))
                            except ValueError:
                                planta_lat, planta_lng = None, None

                    # Solo incluir observaciones con coordenadas válidas
                    if planta_lat is None or planta_lng is None or (planta_lat == 0 and planta_lng == 0):
                        print(f"Coordenadas no válidas para {nombre_cientifico}, saltando observación")
                        continue

                    plantas.append({
                        "nombre_cientifico": nombre_cientifico,
                        "genero": self.extraer_genero(nombre_cientifico),
                        "latitud": planta_lat,
                        "longitud": planta_lng,
                        "distancia": "N/A",
                        "fecha_observacion": obs.get("observed_on", "Fecha desconocida"),
                        "identificaciones": obs.get("identifications_count", 0),
                        "calidad": obs.get("quality_grade", "Desconocido"),
                        "descripcion": obs.get("description", "Sin descripción"),
                        "imagen_generica": self.obtener_imagen_generica(self.extraer_genero(nombre_cientifico)),
                        "fuente": "iNaturalist"
                    })

            except Exception as e:
                print(f"Error en iNaturalist para {genero}: {e}")
        return plantas

    def procesar_trefle(self, swlat, swlng, nelat, nelng):
        """
        Consulta la API de Trefle para obtener información de plantas.
        Como Trefle no permite búsqueda por coordenadas, se realiza una búsqueda
        por cada género de interés. Los campos de latitud y longitud se asignan como 'Desconocida'.
        """
        generos_no_soportados = {"Alga", "Hongo", "Líquen", "Briófito", "Pteridófito"}
        
        plantas = []
        headers = {'User-Agent': 'TuApp/1.0'}
        for genero in self.generos_interes:
            if genero in generos_no_soportados:
                print(f"El género '{genero}' no es compatible con Trefle. Se omite la consulta.")
                continue

            params = {
                "q": genero,
                "token": self.trefle_api_key,
                "limit": 50
            }
            try:
                url = f"{self.trefle_api_base_url}/plants/search"
                print(f"\nBuscando en Trefle para el género: {genero}")
                print(f"URL: {url}")
                print(f"Parámetros: {params}")
                response = requests.get(url, params=params, headers=headers, timeout=15)
                print(f"Status code: {response.status_code}")
                if response.status_code != 200:
                    print(f"Error en la respuesta de Trefle para {genero}")
                    continue

                data = response.json()
                plant_list = data.get("data", [])
                print(f"Número de resultados para {genero}: {len(plant_list)}")
                if plant_list:
                    print(f"Ejemplo del primer resultado: {plant_list[0]}")

                for planta_data in plant_list:
                    nombre_cientifico = planta_data.get("scientific_name")
                    if not self.es_nombre_cientifico_valido(nombre_cientifico):
                        print(f"Nombre científico no válido: {nombre_cientifico}")
                        continue

                    common_name = planta_data.get("common_name", "Sin nombre común")
                    family = planta_data.get("family", "Sin familia")
                    descripcion = f"Nombre común: {common_name}. Familia: {family}."

                    planta = {
                        "nombre_cientifico": nombre_cientifico.strip(),
                        "genero": self.extraer_genero(nombre_cientifico),
                        "latitud": "Desconocida",
                        "longitud": "Desconocida",
                        "distancia": "N/A",
                        "fecha_observacion": "No disponible",
                        "identificaciones": 1,
                        "calidad": "Datos oficiales Trefle",
                        "descripcion": descripcion,
                        "imagen_generica": planta_data.get("image_url") or self.obtener_imagen_generica(self.extraer_genero(nombre_cientifico)),
                        "fuente": "Trefle"
                    }
                    plantas.append(planta)
                    print(f"Planta agregada: {planta}")

            except Exception as e:
                print(f"Error en Trefle para {genero}: {e}")
        print(f"Total de plantas procesadas en Trefle: {len(plantas)}")
        return plantas

    def procesar_plantnet(self, swlat, swlng, nelat, nelng):
        plantas = []
        headers = {'User-Agent': 'TuApp/1.0'}
        for genero in self.generos_interes:
            params = {
                "taxon_name": genero,
                "per_page": 50,
                "swlat": swlat,
                "swlng": swlng,
                "nelat": nelat,
                "nelng": nelng,
                "api-key": self.plantnet_api_key
            }
            try:
                response = requests.get(
                    f"{self.plantnet_api_base_url}/observations",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                resultados = response.json().get("results", [])
                print(f"Observaciones para '{genero}' en PlantNet: {len(resultados)}")
                for obs in resultados:
                    taxon = obs.get("taxon", {})
                    nombre_cientifico = taxon.get("name", "Desconocido")
                    if not self.es_nombre_cientifico_valido(nombre_cientifico):
                        continue

                    planta_lat = obs.get("latitude")
                    planta_lng = obs.get("longitude")
                    if planta_lat is None or planta_lng is None:
                        loc = obs.get("location", "")
                        if loc and "," in loc:
                            try:
                                planta_lat, planta_lng = map(float, loc.split(","))
                            except ValueError:
                                planta_lat, planta_lng = None, None

                    plantas.append({
                        "nombre_cientifico": nombre_cientifico,
                        "genero": self.extraer_genero(nombre_cientifico),
                        "latitud": planta_lat or "Desconocida",
                        "longitud": planta_lng or "Desconocida",
                        "distancia": "N/A",
                        "fecha_observacion": obs.get("observed_on", "Fecha desconocida"),
                        "identificaciones": obs.get("identifications_count", 0),
                        "calidad": obs.get("quality_grade", "Desconocido"),
                        "descripcion": obs.get("description", "Sin descripción"),
                        "imagen_generica": self.obtener_imagen_generica(self.extraer_genero(nombre_cientifico)),
                        "fuente": "PlantNet"
                    })

            except Exception as e:
                print(f"Error en PlantNet para {genero}: {e}")
        return plantas

    def agregar_resultados(self, resultados_listas):
        resultados_combinados = []
        vistas = set()
        for fuente in resultados_listas:
            for planta in fuente:
                clave = (planta["nombre_cientifico"], planta["latitud"], planta["longitud"])
                if clave not in vistas:
                    vistas.add(clave)
                    resultados_combinados.append(planta)
        return resultados_combinados

    def obtener_datos_area(self, swlat, swlng, nelat, nelng, fuente):
        if fuente == "inaturalist":
            resultados = self.procesar_inaturalist(swlat, swlng, nelat, nelng)
        elif fuente == "plantnet":
            resultados = self.procesar_plantnet(swlat, swlng, nelat, nelng)
        elif fuente == "trefle":
            resultados = self.procesar_trefle(swlat, swlng, nelat, nelng)
        else:
            resultados = []
        
        resultados.sort(key=lambda x: x.get("identificaciones", 0), reverse=True)
        return resultados
