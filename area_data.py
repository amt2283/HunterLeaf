import requests

class AreaDataAggregator:
    def __init__(self, generos_interes,
                 inaturalist_api_base_url="https://api.inaturalist.org/v1",
                 gbif_api_base_url="https://api.gbif.org/v1"):
        """
        Inicializa el agregador con la lista de géneros de interés y las URLs base de las APIs.
        """
        self.generos_interes = generos_interes
        self.inaturalist_api_base_url = inaturalist_api_base_url
        self.gbif_api_base_url = gbif_api_base_url
        self.imagen_generica_cache = {}

    @staticmethod
    def extraer_genero(nombre_cientifico):
        """
        Extrae el género a partir del nombre científico (la primera palabra) y lo normaliza.
        Se elimina espacios extra, se convierte la primera letra a mayúscula y el resto a minúsculas.
        """
        if nombre_cientifico and " " in nombre_cientifico:
            genero = nombre_cientifico.split()[0].strip()
            return genero.capitalize()
        return "Desconocido"

    @staticmethod
    def es_nombre_cientifico_valido(nombre_cientifico):
        """
        Valida que el nombre científico contenga al menos dos palabras.
        """
        return nombre_cientifico and " " in nombre_cientifico

    def obtener_imagen_generica(self, genero):
        """
        Obtiene una imagen genérica para el género consultando la API de iNaturalist y
        almacenándola en caché para evitar solicitudes repetidas.
        """
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

    def obtener_gbif_genus_key(self, genero):
        """
        Consulta la API de GBIF para obtener la clave (key) de un género.
        Devuelve el valor del campo 'key' del primer resultado, o None en caso de error.
        """
        headers = {'User-Agent': 'TuApp/1.0'}
        params = {"q": genero, "rank": "genus", "limit": 1}
        try:
            response = requests.get(
                f"{self.gbif_api_base_url}/species/search",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            resultados = response.json().get("results", [])
            if resultados:
                return resultados[0].get("key")
            return None
        except Exception as e:
            print(f"Error obteniendo genus key para {genero} en GBIF: {e}")
            return None

    def procesar_inaturalist(self, swlat, swlng, nelat, nelng):
        """
        Consulta la API de iNaturalist para obtener observaciones dentro del área
        definida por el bounding box (swlat, swlng, nelat, nelng).
        Se ha eliminado la restricción por taxon_id y rank para no limitar la búsqueda a Plantae.
        """
        plantas = []
        headers = {'User-Agent': 'TuApp/1.0'}
        for genero in self.generos_interes:
            params = {
                "taxon_name": genero,
                # Se eliminaron "taxon_id": 47126 y "rank": "genus" para no restringir la búsqueda.
                "per_page": 50,
                "swlat": swlat,
                "swlng": swlng,
                "nelat": nelat,
                "nelng": nelng,
                "fields": "taxon,observed_on,description,identifications_count,quality_grade,latitude,longitude,location"
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
                print(f"Observaciones para el género '{genero}' en iNaturalist: {len(resultados)}")
                for obs in resultados:
                    taxon = obs.get("taxon", {})
                    nombre_cientifico = taxon.get("name", "Desconocido")
                    if not self.es_nombre_cientifico_valido(nombre_cientifico):
                        continue

                    # Se intentan obtener las coordenadas
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
                        "latitud": planta_lat if planta_lat is not None else "Desconocida",
                        "longitud": planta_lng if planta_lng is not None else "Desconocida",
                        "distancia": "N/A",
                        "fecha_observacion": obs.get("observed_on", "Fecha desconocida"),
                        "identificaciones": obs.get("identifications_count", 0),
                        "calidad": obs.get("quality_grade", "Desconocido"),
                        "descripcion": obs.get("description", "Sin descripción"),
                        "imagen_generica": self.obtener_imagen_generica(self.extraer_genero(nombre_cientifico))
                    })
            except Exception as e:
                print(f"Error en API iNaturalist para {genero}: {e}")
        return plantas

    def procesar_gbif(self, swlat, swlng, nelat, nelng):
        """
        Consulta la API de GBIF para obtener registros de ocurrencias dentro del área
        definida por el bounding box.
        Se ha eliminado el filtro 'taxonKey': 6 para no limitar la búsqueda a Plantae.
        """
        plantas = []
        headers = {'User-Agent': 'TuApp/1.0'}
        for genero in self.generos_interes:
            genus_key = self.obtener_gbif_genus_key(genero)
            if not genus_key:
                continue
            try:
                wkt_polygon = f"POLYGON(({swlng} {swlat}, {nelng} {swlat}, {nelng} {nelat}, {swlng} {nelat}, {swlng} {swlat}))"
                params = {
                    "hasCoordinate": "true",
                    "genusKey": genus_key,
                    # Se eliminó "taxonKey": 6 para no restringir la búsqueda.
                    "geometry": wkt_polygon,
                    "limit": 50
                }
                response = requests.get(
                    f"{self.gbif_api_base_url}/occurrence/search",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                resultados = response.json().get("results", [])
                print(f"Observaciones en GBIF para el género '{genero}' (genusKey {genus_key}): {len(resultados)}")
                for occ in resultados:
                    nombre_cientifico = occ.get("scientificName", "Desconocido")
                    if not self.es_nombre_cientifico_valido(nombre_cientifico):
                        continue

                    planta_lat = occ.get("decimalLatitude")
                    planta_lng = occ.get("decimalLongitude")
                    plantas.append({
                        "nombre_cientifico": nombre_cientifico,
                        "genero": self.extraer_genero(nombre_cientifico),
                        "latitud": planta_lat if planta_lat is not None else "Desconocida",
                        "longitud": planta_lng if planta_lng is not None else "Desconocida",
                        "distancia": "N/A",
                        "fecha_observacion": occ.get("eventDate", "Fecha desconocida"),
                        "identificaciones": occ.get("identifications_count", 0),
                        "calidad": occ.get("occurrenceStatus", "Desconocido"),
                        "descripcion": occ.get("habitat", "Sin descripción"),
                        "imagen_generica": self.obtener_imagen_generica(self.extraer_genero(nombre_cientifico))
                    })
            except Exception as e:
                print(f"Error en API GBIF para {genero}: {e}")
        return plantas

    def agregar_resultados(self, resultados_listas):
        """
        Combina los resultados de las distintas fuentes y elimina duplicados.
        """
        resultados_combinados = []
        vistas = set()
        for fuente in resultados_listas:
            for planta in fuente:
                clave = (planta["nombre_cientifico"], planta["latitud"], planta["longitud"])
                if clave not in vistas:
                    vistas.add(clave)
                    resultados_combinados.append(planta)
        return resultados_combinados

    def obtener_datos_area(self, swlat, swlng, nelat, nelng):
        """
        Obtiene datos de iNaturalist y GBIF para el área definida,
        combinándolos y ordenándolos.
        """
        resultados_inaturalist = self.procesar_inaturalist(swlat, swlng, nelat, nelng)
        resultados_gbif = self.procesar_gbif(swlat, swlng, nelat, nelng)
        resultados = self.agregar_resultados([resultados_inaturalist, resultados_gbif])
        resultados.sort(key=lambda x: x.get("identificaciones", 0), reverse=True)
        return resultados
