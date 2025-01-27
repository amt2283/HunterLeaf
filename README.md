# PlantFinder

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

1. Clona este repositorio:
  
   git clone https://github.com/amt2283/PlantFinder.git
2. Navega al directorio del proyecto:
 
  Copiar
  cd plantfinder
3. Crea un entorno virtual e instala las dependencias:

 python -m venv venv
 source venv/bin/activate  # En Linux/Mac
 venv\Scripts\activate  # En Windows
 pip install -r requirements.txt
4. Ejecuta la aplicación:
 python app.py

