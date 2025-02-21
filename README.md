<div align="center">
  <img src="Logo%20PlantFinder.png" alt="PlantFinder Logo" width="120">
  <h1>🌿 HunterLeaf</h1>
  <p>¡Descubre la naturaleza que te rodea! Encuentra plantas cerca de ti con tecnología colaborativa y geolocalización precisa 🌍</p>
  
  [![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://python.org)
  [![Flask](https://img.shields.io/badge/Framework-Flask-green?logo=flask)](https://flask.palletsprojects.com/)
  [![Open Source](https://img.shields.io/badge/Open%20Source-❤%EF%B8%8F-red)](https://opensource.org)
</div>

---

**🌐 Live Demo: https://75c9-89-26-182-41.ngrok-free.app | **📌 Versión Actual:** 1.1.0 | **📜 Licencia:** [Apache 2.0](LICENSE)

---

## 🚀 Novedades en la v1.1.0
- 🆕 **Bounding Box Search**: ¡Nueva función para buscar plantas en áreas específicas!
- 📐 Búsquedas personalizadas mediante coordenadas geográficas
- 🌍 Integración mejorada con APIs de iNaturalist y GBIF
- 🗺 Soporte para polígonos complejos en búsquedas geográficas
- 🚀 Optimización del rendimiento en consultas espaciales

---

## 🗺 Características Principales
- 📍 Búsqueda por coordenadas, dirección o área definida
- 🔍 **Nuevo**: Búsqueda por bounding box (rectángulo geográfico)
- 🗺 Mapa interactivo con selección de áreas y marcadores
- 🌱 Filtrado inteligente por tipos de plantas
- 📊 Datos en tiempo real de múltiples fuentes (iNaturalist, GBIF)
- 📱 Diseño responsive y experiencia de usuario mejorada

---

## 🔧 Configuración Rápida

```bash
# Clona el repositorio
git clone https://github.com/amt2283/HunterLeaf.git
cd HunterLeaf

# Configura entorno virtual e instala dependencias
python -m venv venv && source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Inicia la aplicación
python app.py
