"""Materiales con las propiedades del modelo de iluminación de Phong."""
from dataclasses import dataclass

import numpy as np


@dataclass
class Material:
    """Propiedades ópticas de una superficie.

    color:        color base RGB en [0, 1].
    ambient:      coeficiente ambiental (k_a).
    diffuse:      coeficiente difuso (k_d).
    specular:     coeficiente especular (k_s).
    shininess:    exponente de brillo de Phong (n).
    reflectivity: fracción de luz que proviene del rayo reflejado, en [0, 1].
    checker:      si no es None, segundo color para un patrón de tablero.
    checker_size: tamaño de cada casilla del tablero.
    """

    color: tuple = (1.0, 1.0, 1.0)
    ambient: float = 0.1
    diffuse: float = 0.9
    specular: float = 0.5
    shininess: float = 50.0
    reflectivity: float = 0.0
    checker: tuple = None
    checker_size: float = 1.0

    def color_at(self, points):
        """Color base en cada punto; solo varía si el material es de tablero."""
        base = np.broadcast_to(np.array(self.color, dtype=float), points.shape).copy()
        if self.checker is None:
            return base
        cells = np.floor(points / self.checker_size).astype(int)
        parity = (cells[:, 0] + cells[:, 2]) % 2 == 0
        base[~parity] = self.checker
        return base
