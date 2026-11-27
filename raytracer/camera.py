"""Cámara virtual: genera un rayo primario por cada píxel del viewport."""
import numpy as np

from .vectors import normalize


class Camera:
    """Cámara de perspectiva con base ortonormal (u, v, w)."""

    def __init__(self, position, look_at, up=(0, 1, 0), fov_degrees=60.0):
        self.position = np.array(position, dtype=float)
        self.fov = np.radians(fov_degrees)
        # w apunta hacia atrás, u hacia la derecha, v hacia arriba.
        self.w = normalize(self.position - np.array(look_at, dtype=float))
        self.u = normalize(np.cross(np.array(up, dtype=float), self.w))
        self.v = np.cross(self.w, self.u)

    def generate_rays(self, width, height):
        """Devuelve (orígenes, direcciones) de forma (width*height, 3).

        El viewport está a distancia 1; su alto es 2 tan(fov/2).
        """
        half_height = np.tan(self.fov / 2.0)
        half_width = half_height * width / height
        xs = (np.arange(width) + 0.5) / width * 2.0 - 1.0
        ys = 1.0 - (np.arange(height) + 0.5) / height * 2.0
        px, py = np.meshgrid(xs * half_width, ys * half_height)
        directions = (px[..., None] * self.u
                      + py[..., None] * self.v
                      - self.w).reshape(-1, 3)
        origins = np.broadcast_to(self.position, directions.shape).copy()
        return origins, normalize(directions)
