"""Primitivas geométricas con intersección analítica rayo-objeto."""
import numpy as np

from .vectors import dot, normalize

NO_HIT = np.inf
EPSILON = 1e-4


class Sphere:
    """Esfera definida por centro y radio."""

    def __init__(self, center, radius, material):
        self.center = np.array(center, dtype=float)
        self.radius = float(radius)
        self.material = material

    def intersect(self, origins, directions):
        """Distancia t > 0 al primer impacto de cada rayo (inf si falla).

        Se resuelve |o + t d - c|^2 = r^2, es decir una ecuación cuadrática
        a t^2 + b t + c = 0 con a = d·d, b = 2 d·(o-c), c = |o-c|^2 - r^2.
        """
        oc = origins - self.center
        a = dot(directions, directions)
        b = 2.0 * dot(directions, oc)
        c = dot(oc, oc) - self.radius ** 2
        discriminant = b * b - 4.0 * a * c

        t = np.full(len(origins), NO_HIT)
        has_roots = discriminant >= 0
        sqrt_disc = np.sqrt(np.where(has_roots, discriminant, 0.0))
        t_near = (-b - sqrt_disc) / (2.0 * a)
        t_far = (-b + sqrt_disc) / (2.0 * a)
        # Se toma la raíz más cercana que esté delante del origen.
        chosen = np.where(t_near > EPSILON, t_near, t_far)
        valid = has_roots & (chosen > EPSILON)
        t[valid] = chosen[valid]
        return t

    def normal_at(self, points):
        return normalize(points - self.center)


class Plane:
    """Plano infinito definido por un punto y una normal."""

    def __init__(self, point, normal, material):
        self.point = np.array(point, dtype=float)
        self.normal = normalize(np.array(normal, dtype=float))
        self.material = material

    def intersect(self, origins, directions):
        """Resuelve (o + t d - p)·n = 0, es decir t = (p - o)·n / (d·n)."""
        denominator = dot(directions, self.normal)
        t = np.full(len(origins), NO_HIT)
        not_parallel = np.abs(denominator) > 1e-8
        safe_den = np.where(not_parallel, denominator, 1.0)
        candidate = dot(self.point - origins, np.broadcast_to(self.normal, origins.shape)) / safe_den
        valid = not_parallel & (candidate > EPSILON)
        t[valid] = candidate[valid]
        return t

    def normal_at(self, points):
        return np.broadcast_to(self.normal, points.shape).copy()
