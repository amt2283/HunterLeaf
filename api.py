import requests
import time

class ApiAvistamientos:
    def __init__(self, lat, lon, delay_inicial=1):
        self.lat = lat
        self.lon = lon
        self.delay_inicial = delay_inicial
        self.url = "https://api.inaturalist.org/v1/observations"

    def obtener_avistamientos(self, grupo):
        """Obtiene avistamientos para un grupo dado."""
        params = {
            'family': grupo,
            'lat': self.lat,
            'lng': self.lon,
            'radius': 50,
            'per_page': 10,
            'order_by': 'observed_on',
            'order': 'desc',
        }

        retries = 0
        delay = self.delay_inicial

        while retries < 5:
            try:
                response = requests.get(self.url, params=params)
                response.raise_for_status()
                return response.json().get('results', [])
            except requests.exceptions.RequestException as e:
                print(f"Error al obtener datos para {grupo}: {e}")
                retries += 1
                time.sleep(delay)
                delay = min(delay * 2, 300)

        return []
