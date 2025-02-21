import pandas as pd
import requests
from math import radians, cos, sin, sqrt, atan2
import unicodedata
import json
from typing import Dict, List, Set

# Función para eliminar tildes y normalizar el texto.
def quitar_tildes(cadena):
    return ''.join(c for c in unicodedata.normalize('NFD', cadena) if unicodedata.category(c) != 'Mn')

# Función para obtener información detallada de un taxón (incluyendo ancestros)
def get_taxon_info(taxon_id):
    url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        resultados = json_data.get("results", [])
        if resultados:
            return resultados[0]
    return {}

class ProcesadorDatos:
    def __init__(self, categoria=None, genero=None, familia=None):
        """
        Inicializa el procesador con filtros taxonómicos actualizados.
        """
        if categoria:
            # Normalizamos quitando tildes y convirtiendo a minúsculas
            normalized_cat = quitar_tildes(categoria.strip().lower())
            print("Categoría normalizada antes de quitar 's':", normalized_cat)
            # Si termina en "s", se quita para obtener la forma singular (p.ej. angiospermas -> angiosperma)
            if normalized_cat.endswith("s"):
                normalized_cat = normalized_cat[:-1]
            self.categoria = normalized_cat
        else:
            self.categoria = None
        
        self.genero = quitar_tildes(genero.strip().lower()) if genero else None
        self.familia = quitar_tildes(familia.strip().lower()) if familia else None
        
        # Taxonomía actualizada basada en APG IV y la jerarquía de iNaturalist
        self.categoria_mapping = {
            'pteridofito': {
                'ranks': ['class', 'phylum', 'subphylum'],
                'terms': [
                    'polypodiopsida',    # Helechos verdaderos
                    'pteridophyta',      # Término general para helechos
                    'lycopodiopsida',    # Licopodios
                    'psilotopsida',      # Psilotales
                    'equisetopsida'      # Colas de caballo
                ]
            },
            'angiosperma': {
                'ranks': ['class', 'subclass', 'order'],
                'terms': [
                    'magnoliopsida',     # Dicotiledóneas
                    'liliopsida',        # Monocotiledóneas
                    'angiospermae',      # Término general
                    'eudicots',          # Eudicotiledóneas
                    'monocots'           # Monocotiledóneas (término alternativo)
                ]
            },
            'gimnosperma': {
                'ranks': ['class', 'division', 'phylum'],
                'terms': [
                    'pinopsida',         # Coníferas
                    'ginkgoopsida',      # Ginkgos
                    'cycadopsida',       # Cícadas
                    'gnetopsida',        # Gnetófitas
                    'gymnospermae'       # Término general
                ]
            },
            'alga': {
                'ranks': ['phylum', 'division', 'class'],
                'terms': [
                    'phaeophyceae',        # Algas pardas
                    'rhodophyta',          # Algas rojas
                    'chlorophyta',         # Algas verdes
                    'charophyta',          # Algas carófitas
                    'bacillariophyta',     # Diatomeas
                    'dinoflagellata',      # Dinoflagelados
                    'chromista'            # Reino que incluye varias algas
                ]
            }
        }
        
        print(f"Filtros inicializados - Categoría: {self.categoria}, Género: {self.genero}, Familia: {self.familia}")

    @staticmethod
    def calcular_distancia(lat1, lon1, lat2, lon2):
        """
        Calcula la distancia en kilómetros entre dos puntos usando la fórmula de Haversine.
        """
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        print(f"Calculando distancia entre: ({lat1}, {lon1}) y ({lat2}, {lon2})")
        R = 6371  # Radio de la Tierra en km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        distancia = R * 2 * atan2(sqrt(a), sqrt(1-a))
        print(f"Distancia calculada: {distancia:.1f} km")
        return distancia

    def _cumple_criterios_taxonomicos(self, ancestros: List[Dict], taxon_nombre: str) -> bool:
        """
        Verifica si un taxón cumple con los criterios taxonómicos especificados.
        
        Args:
            ancestros: Lista de diccionarios con información de ancestros
            taxon_nombre: Nombre del taxón actual
            
        Returns:
            bool: True si cumple con los criterios, False en caso contrario
        """
        if not self.categoria:
            return True
            
        mapping = self.categoria_mapping.get(self.categoria)
        if not mapping:
            print(f"Advertencia: Categoría {self.categoria} no encontrada en el mapping")
            return False
            
        # Conjunto para almacenar términos encontrados
        terminos_encontrados: Set[str] = set()
        
        # Verificar en ancestros
        for ancestro in ancestros:
            rango = ancestro.get('rank', '').lower()
            nombre = ancestro.get('name', '').lower()
            
            # Si el rango del ancestro está en los rangos relevantes para la categoría
            if rango in mapping['ranks']:
                # Verificar si algún término de la categoría está en el nombre del ancestro
                for termino in mapping['terms']:
                    if termino in nombre:
                        terminos_encontrados.add(termino)
                        print(f"Término encontrado '{termino}' en ancestro '{nombre}' de rango '{rango}'")
            
            # También buscar en nombres vernáculos si están disponibles
            nombres_vernaculos = ancestro.get('vernacular_names', [])
            for vernacular in nombres_vernaculos:
                nombre_vernacular = vernacular.get('name', '').lower()
                for termino in mapping['terms']:
                    if termino in nombre_vernacular:
                        terminos_encontrados.add(termino)
                        print(f"Término encontrado '{termino}' en nombre vernáculo '{nombre_vernacular}'")
        
        # Si encontramos al menos un término, consideramos que cumple con la categoría
        cumple = len(terminos_encontrados) > 0
        if cumple:
            print(f"Taxón '{taxon_nombre}' cumple con categoría '{self.categoria}'. Términos encontrados: {terminos_encontrados}")
        else:
            print(f"Taxón '{taxon_nombre}' NO cumple con categoría '{self.categoria}'. No se encontraron términos coincidentes.")
        
        return cumple

    def procesar_inaturalist(self, lat, lon, radio=10):
        try:
            lat = float(lat)
            lon = float(lon)
            print(f"\nIniciando búsqueda en: {lat}, {lon} con radio {radio} km")
        except ValueError as e:
            print(f"Error al convertir coordenadas: {e}")
            return pd.DataFrame()

        # Construir parámetros para la API
        params = {
            "lat": lat,
            "lng": lon,
            "radius": radio,
            "per_page": 200,
            "order": "desc",
            "order_by": "created_at",
            "quality_grade": "research",
            "iconic_taxa[]": "Plantae",
            "geoprivacy": "open",  # Observaciones con ubicación pública
            "mappable": "true"     # Observaciones con coordenadas válidas
        }
        
        # Si se indica género y no familia, se añade en la consulta
        if self.genero and not self.familia:
            params["taxon_name"] = self.genero

        print(f"Parámetros de búsqueda: {params}")
        
        try:
            url = "https://api.inaturalist.org/v1/observations"
            response = requests.get(url, params=params, timeout=10)
            print(f"Status code: {response.status_code}")
            print(f"URL de búsqueda: {response.url}")

            if response.status_code != 200:
                print(f"Error en API: {response.text}")
                return pd.DataFrame()

            data = response.json()
            resultados = data.get('results', [])
            print(f"\nObservaciones encontradas en API: {len(resultados)}")
            
            # Diagnóstico de la primera observación
            if resultados:
                primera_obs = resultados[0]
                print("\nDiagnóstico de primera observación:")
                print(f"Latitude: {primera_obs.get('latitude')}")
                print(f"Longitude: {primera_obs.get('longitude')}")
                print(f"Location: {primera_obs.get('location')}")
                if 'geojson' in primera_obs:
                    print(f"GeoJSON coordinates: {primera_obs['geojson'].get('coordinates')}")
            
            plantas = []
            # Abrir el archivo de log (se sobrescribe en cada ejecución)
            with open('ancestros_log.txt', 'w', encoding='utf-8') as log_file:
                for obs in resultados:
                    taxon = obs.get('taxon', {})
                    nombre_cientifico = taxon.get('name', '')
                    taxon_id = taxon.get('id', None)
                    if not nombre_cientifico:
                        print("Saltando observación sin nombre científico")
                        continue

                    # Obtener coordenadas de la observación
                    try:
                        planta_lat = float(obs.get('latitude', 0))
                        planta_lon = float(obs.get('longitude', 0))
                        
                        # Verificar coordenadas válidas
                        if planta_lat == 0 and planta_lon == 0:
                            if 'geojson' in obs:
                                coordinates = obs['geojson'].get('coordinates', [])
                                if coordinates and len(coordinates) == 2:
                                    planta_lon, planta_lat = coordinates
                            if planta_lat == 0 and planta_lon == 0 and 'location' in obs:
                                try:
                                    planta_lat, planta_lon = map(float, obs['location'].split(','))
                                except:
                                    print(f"No se pudieron obtener coordenadas válidas para {nombre_cientifico}")
                                    continue
                        
                        if planta_lat == 0 and planta_lon == 0:
                            print(f"Coordenadas no válidas para {nombre_cientifico}, saltando observación")
                            continue
                        
                        distancia = self.calcular_distancia(lat, lon, planta_lat, planta_lon)
                        if distancia > radio:
                            print(f"Descartando {nombre_cientifico} por distancia: {distancia:.1f} km > {radio} km")
                            continue
                    except Exception as e:
                        print(f"Error al procesar coordenadas para {nombre_cientifico}: {str(e)}")
                        continue

                    # Obtener lista de ancestros; si no existe, intentar obtenerla a través de get_taxon_info
                    ancestros = taxon.get('ancestors', [])
                    if not ancestros and taxon_id:
                        print(f"No se encontraron ancestros en la observación para {nombre_cientifico} (ID: {taxon_id}). Solicitando información adicional...")
                        taxon_info = get_taxon_info(taxon_id)
                        ancestros = taxon_info.get('ancestors', [])
                    
                    # Log de ancestros
                    log_file.write(f"Taxon: {nombre_cientifico} (ID: {taxon_id})\n")
                    if ancestros:
                        for a in ancestros:
                            log_file.write(f"  Ancestro: rango={a.get('rank')}, nombre={a.get('name')}\n")
                            print(f"Ancestro: rango={a.get('rank')}, nombre={a.get('name')}")
                    else:
                        log_file.write("  No se encontraron ancestros.\n")
                        print("  No se encontraron ancestros.")

                    # Filtrar por categoría usando el método actualizado
                    if self.categoria and not self._cumple_criterios_taxonomicos(ancestros, nombre_cientifico):
                        continue

                    # Filtrar por familia (si se especifica)
                    if self.familia:
                        familia_encontrada = False
                        for a in ancestros:
                            if a.get('rank', '').lower() == 'family' and self.familia in a.get('name', '').lower():
                                familia_encontrada = True
                                break
                        if not familia_encontrada:
                            print(f"Descartando {nombre_cientifico} por no coincidir con familia {self.familia}")
                            continue

                    # Filtrar por género de forma local (si se especifica junto con familia)
                    if self.genero and self.familia:
                        genero_encontrado = False
                        if self.genero in nombre_cientifico.lower():
                            genero_encontrado = True
                        else:
                            for a in ancestros:
                                if a.get('rank', '').lower() == 'genus' and self.genero in a.get('name', '').lower():
                                    genero_encontrado = True
                                    break
                        if not genero_encontrado:
                            print(f"Descartando {nombre_cientifico} por no coincidir con género {self.genero}")
                            continue

                    # Registro final
                    registro = {
                        'nombre': nombre_cientifico,
                        'nombre_comun': taxon.get('preferred_common_name', 'N/A'),
                        'distancia': f"{distancia:.1f} km",
                        'fecha': obs.get('observed_on', 'N/A'),
                        'imagen': obs.get('photos', [{}])[0].get('url', ''),
                        'coordenadas': f"{planta_lat}, {planta_lon}",
                        'calidad': obs.get('quality_grade', 'N/A')
                    }
                    plantas.append(registro)
                    print(f"Añadida planta: {nombre_cientifico} a {distancia:.1f} km")
            
            print(f"\nTotal de registros válidos dentro del radio: {len(plantas)}")
            return pd.DataFrame(plantas)

        except Exception as e:
            print(f"Error crítico: {str(e)}")
            return pd.DataFrame()

# Ejemplo de uso:
if __name__ == "__main__":
    # Ejemplo 1: Buscar observaciones de Rosa en categoría angiospermas
    procesador = ProcesadorDatos(categoria="angiospermas", genero="rosa")
    df = procesador.procesar_inaturalist(19.4326, -99.1332, radio=20)  # Coordenadas de CDMX

    # Ejemplo 2: Buscar observaciones filtrando por familia (por ejemplo, dentro de Rosaceae)
    # procesador = ProcesadorDatos(categoria="angiospermas", familia="rosaceae")
    # df = procesador.procesar_inaturalist(19.4326, -99.1332, radio=20)

    if df.empty:
        print("\n⚠️ No se encontraron resultados. Posibles causas:")
        print("- No hay observaciones recientes en el área")
        print("- Los filtros (categoría, género, familia) no coinciden con las observaciones de la zona")
        print("- Problemas de conexión o cambios en la API")
    else:
        print("\n✅ Resultados obtenidos:")
        print(df[['nombre', 'nombre_comun', 'distancia', 'fecha']])
