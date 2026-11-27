"""Contenedor de la escena: objetos, luces y color de fondo."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PointLight:
    """Fuente de luz puntual con atenuación cuadrática opcional."""

    position: tuple
    color: tuple = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    attenuation: float = 0.0  # factor k en 1 / (1 + k d^2)

    def __post_init__(self):
        self.position = np.array(self.position, dtype=float)
        self.color = np.array(self.color, dtype=float)


@dataclass
class Scene:
    objects: list = field(default_factory=list)
    lights: list = field(default_factory=list)
    sky_top: tuple = (0.35, 0.55, 0.9)
    sky_bottom: tuple = (0.95, 0.95, 1.0)

    def background(self, directions):
        """Degradado vertical según la componente y de cada rayo."""
        blend = np.clip(0.5 * (directions[:, 1] + 1.0), 0.0, 1.0)[:, None]
        return (1 - blend) * np.array(self.sky_bottom) + blend * np.array(self.sky_top)
