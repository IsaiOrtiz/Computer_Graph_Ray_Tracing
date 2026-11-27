"""Escenas de ejemplo listas para renderizar."""
from .camera import Camera
from .materials import Material
from .primitives import Plane, Sphere
from .scene import PointLight, Scene


def mirror_spheres():
    """Tres esferas (mate, brillante y espejo) sobre un piso de tablero."""
    floor = Material(color=(0.9, 0.9, 0.9), checker=(0.15, 0.15, 0.15),
                     checker_size=1.5, specular=0.1, reflectivity=0.25)
    red = Material(color=(0.85, 0.12, 0.12), specular=0.6, shininess=80, reflectivity=0.15)
    green = Material(color=(0.15, 0.7, 0.25), specular=0.9, shininess=200, reflectivity=0.3)
    chrome = Material(color=(0.95, 0.95, 0.95), ambient=0.05, diffuse=0.2,
                      specular=1.0, shininess=300, reflectivity=0.85)

    scene = Scene(
        objects=[
            Plane(point=(0, -1, 0), normal=(0, 1, 0), material=floor),
            Sphere((-2.2, 0.0, -1.0), 1.0, red),
            Sphere((0.0, 0.0, -3.0), 1.0, chrome),
            Sphere((2.2, 0.0, -1.0), 1.0, green),
        ],
        lights=[
            PointLight((-5, 6, 4), intensity=0.9),
            PointLight((6, 4, 2), color=(1.0, 0.9, 0.8), intensity=0.5, attenuation=0.005),
        ],
    )
    camera = Camera(position=(0, 1.5, 6), look_at=(0, 0, -1.5), fov_degrees=50)
    return scene, camera


SCENES = {"mirror_spheres": mirror_spheres}
