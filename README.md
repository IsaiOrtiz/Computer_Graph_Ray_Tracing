# Motor de Trazado de Rayos (Ray Tracing)

Proyecto final de Graficación por Computadora (agosto-diciembre 2026).
Renderizador implementado desde cero que calcula de forma analítica la interacción de la luz con esferas y planos.

![Escena de ejemplo](renders/mirror_spheres.png)

| Vista 3D (OpenGL) | Ray tracing desde esa vista |
|---|---|
| ![Aplicación 3D](renders/app_3d.png) | ![Aplicación render](renders/app_render.png) |

## Características
- Cámara de perspectiva con base ortonormal y rayos primarios por píxel.
- Intersección analítica rayo-esfera y rayo-plano.
- Iluminación de Phong (ambiental, difusa y especular) con luces puntuales y atenuación.
- Rayos de sombra y reflexiones recursivas.
- Piso con patrón de tablero, antialiasing por supermuestreo y corrección gamma.
- Exportación a PNG.
- Aplicación de escritorio en una sola ventana (`app.py`): panel de control + visor 3D OpenGL con cámara orbital.
- Selección de objetos con clic (usa las intersecciones del propio ray tracer), edición en vivo de material, color, tamaño, posición y luces.
- Ray tracing desde la vista actual en un hilo aparte, para que la ventana no se congele.

## Tecnologías
Python 3, NumPy (cálculo vectorizado), Pillow (exportación de imagen), pygame-ce y PyOpenGL (visor 3D), pytest.

## Integrantes
- Ortiz Martínez Isai Eliezer

## Instalación
```bash
pip install -r requirements.txt
```

## Ejecución
Aplicación de escritorio (recomendado):
```bash
python app.py
```
- **Pestaña Escena:** cambiar de escena, mover y regular las luces, agregar / eliminar objetos y elegirlos de la lista.
- **Pestaña Objeto:** reflectividad, coeficientes de Phong, brillo, color, radio y posición del objeto seleccionado.
- **Pestaña Render:** resolución, rebotes de reflexión, antialiasing y pruebas automáticas.
- **Visor:** arrastrar = orbitar, rueda = zoom, clic = seleccionar, **R** = renderizar con ray tracing desde la vista actual, **T** = alternar OpenGL / render, **S** = guardar PNG, **Supr** = eliminar objeto, **ESC** = salir.

Línea de comandos:
```bash
python main.py --scene mirror_spheres --width 1000 --height 750 --supersampling 2 --depth 4 --output renders/mirror_spheres.png
python -m pytest
```

## Estructura
| Módulo | Contenido |
|---|---|
| `raytracer/vectors.py` | normalización, producto punto, reflexión |
| `raytracer/camera.py` | generación de rayos primarios |
| `raytracer/primitives.py` | `Sphere`, `Plane` y sus intersecciones |
| `raytracer/materials.py` | propiedades de Phong y patrón de tablero |
| `raytracer/scene.py` | luces, fondo y contenedor de escena |
| `raytracer/renderer.py` | trazado recursivo, Phong, sombras |
| `raytracer/scenes.py` | escenas de ejemplo |
| `raytracer/scene_view.py` | vista 3D OpenGL, cámara orbital y selección |
| `raytracer/ui_widgets.py` | botones, sliders y lista dibujados con OpenGL |
| `raytracer/app.py` | ventana principal que integra panel, visor y render |
| `app.py` | punto de entrada de la aplicación |
| `tests/` | pruebas de intersección, cámara y reflexión |

## Uso de herramientas de IA
Completar según la rúbrica: herramienta usada, para qué, y qué contribuciones fueron propias.

## Referencias
Shirley y Morley, *Realistic Ray Tracing*; Foley et al., *Computer Graphics: Principles and Practice*; Phong (1975).
