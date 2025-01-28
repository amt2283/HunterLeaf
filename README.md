<h1 align="center">
  <img src="Logo%20PlantFinder.png" alt="Logo de PlantFinder" width="50" height="50" style="vertical-align: middle;">
  PlantFinder
</h1>

**PlantFinder** es una aplicación web creada con Flask que permite a los usuarios buscar plantas cercanas a una ubicación específica, basándose en géneros de plantas de interés. Utiliza la API de iNaturalist para obtener información sobre las plantas y muestra los resultados en un mapa interactivo.

## Descripción

PlantFinder permite a los usuarios ingresar coordenadas geográficas (latitud y longitud) y seleccionar uno o más géneros de plantas para buscar en los alrededores. La aplicación se conecta con la API de iNaturalist para obtener datos sobre plantas en la ubicación seleccionada, mostrando una lista con la información y ubicación de las plantas encontradas.

### Características

- **Búsqueda por ubicación**: Ingresa latitud y longitud para obtener plantas cercanas.
- **Selección de géneros**: Elige entre géneros de plantas como Alga, Hongo, Líquen, Briófito, y Pteridófito.
- **Mapa interactivo**: Visualiza la ubicación de las plantas en un mapa.
- **Información detallada**: Obtén información detallada sobre las plantas encontradas, incluyendo su distancia desde tu ubicación.

## Tecnologías Utilizadas

- **Python** (Flask)
- **HTML/CSS** (para la interfaz web)
- **JavaScript** (para la visualización de mapas)
- **API de iNaturalist** (para obtener información sobre plantas)
- **Jinja2** (para renderizar plantillas de Flask)

## Instalación

1. Clona este repositorio: `git clone https://github.com/amt2283/PlantFinder.git`
2. Navega al directorio del proyecto: `cd plantfinder`
3. Crea un entorno virtual e instala las dependencias:
   - En Linux/Mac: `python -m venv venv && source venv/bin/activate`
   - En Windows: `python -m venv venv && venv\Scripts\activate`
   - Luego instala las dependencias: `pip install -r requirements.txt`
4. Ejecuta la aplicación: `python app.py`

## Description

PlantFinder enables users to input geographic coordinates (latitude and longitude) and select one or more plant genera to search for in the surrounding area. The application connects to the iNaturalist API to retrieve data about plants in the selected location, displaying a list with the information and location of the found plants.

### Features

- **Location-based search**: Enter latitude and longitude to find nearby plants.
- **Genus selection**: Choose from plant genera such as Alga, Fungus, Lichen, Bryophyte, and Pteridophyte.
- **Interactive map**: Visualize the location of plants on a map.
- **Detailed information**: Get detailed information about the found plants, including their distance from your location.

## Technologies Used

- **Python** (Flask)
- **HTML/CSS** (for the web interface)
- **JavaScript** (for map visualization)
- **iNaturalist API** (to fetch plant information)
- **Jinja2** (for Flask template rendering)

## Installation

1. Clone this repository: `git clone https://github.com/amt2283/PlantFinder.git`
2. Navigate to the project directory: `cd plantfinder`
3. Create a virtual environment and install dependencies:
   - On Linux/Mac: `python -m venv venv && source venv/bin/activate`
   - On Windows: `python -m venv venv && venv\Scripts\activate`
   - Then install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`
