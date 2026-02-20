🏔️ TrailPrint3D v2.6.1 - CN Enhanced Edition

🌟 Special Tribute to the Original Author

This project is a customized, fully localized (Chinese), and enhanced fork based on the incredible work of EmGi (TrailPrint3D v2.5).
Huge thanks to EmGi for building this amazing tool!
As a secondary developer (Bamboo-fiber), I have translated the entire UI into Chinese and added new features including Quick Draw mode and a Circle Shape base plate.


---
💻 System Requirements

- Blender Version: >= 4.5.0 (Recommended: 4.5.2+)

- Python Version: >= 3.11 (Uses Blender's embedded Python environment)

- Internet Connection: Required for fetching elevation and OpenStreetMap (OSM) data.

- Required Python Packages:requests (usually included/installable in Blender).

🚀 Installation

1. Download the TrailPrint3D_2_6_1.py file.

2. Open Blender, go to Edit > Preferences > Add-ons.

3. Click Install... and select the downloaded .py file.

4. Check the box to enable the add-on: Object: TrailPrint3D.

5. You can find the add-on panel in the 3D Viewport's right sidebar (press N), under the TrailPrint3D tab.

✨ What's New in v2.6.1 (Enhanced Edition)

- Full Chinese Localization: The entire UI has been translated into Chinese for better accessibility for Chinese users.

- New Circle Base Shape: Added a "Circle" option to the map shapes, allowing you to generate elegant round terrain models.

- Quick Draw / Paint Map: Added a feature to directly project OSM data colors onto the map mesh without exporting separate files, optimized for multi-color printing or rendering.

📖 Core Features

- GPS Track Import: Supports .gpx and .igc files.

- Multiple Base Shapes: Choose from Hexagon, Square, Circle, or custom text-embedded base plates, with customizable physical dimensions (default: 100mm).

- Geographical Elements (OSM): Automatically generates physical layers for Water (lakes/rivers), Forests, Cities, and Glaciers.

- Print-Ready Export: Automatically exports to STL (for single-color printing) or OBJ (for multi-color/Bambu Lab printing).

- Mountain Coloring: Automatically assigns different materials to mountain tops based on set altitude thresholds (for snow-capped effects).

- Hardware Assembly Prep: Automatically generate magnet holes and dovetail joints for snapping multiple map tiles together (ideal for fridge magnets or large maps).

- Custom Text Engraving: Supports system fonts (default: Microsoft YaHei msyhbd.ttc) to engrave track distance, elevation gain, and duration on the model.
