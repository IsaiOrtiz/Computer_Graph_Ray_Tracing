"""Trazado recursivo de rayos con iluminación de Phong, sombras y reflexiones."""
import numpy as np
from PIL import Image

from .primitives import EPSILON, NO_HIT
from .vectors import dot, normalize, reflect


class Renderer:
    def __init__(self, scene, camera, max_depth=3):
        self.scene = scene
        self.camera = camera
        self.max_depth = max_depth

    # ------------------------------------------------------------------ API
    def render(self, width, height, supersampling=1):
        """Renderiza la escena y devuelve una imagen PIL.

        supersampling > 1 renderiza a mayor resolución y reduce (antialiasing).
        """
        w, h = width * supersampling, height * supersampling
        origins, directions = self.camera.generate_rays(w, h)
        colors = self.trace(origins, directions, depth=0)
        colors = np.clip(colors, 0.0, 1.0) ** (1 / 2.2)  # corrección gamma
        pixels = (colors.reshape(h, w, 3) * 255).astype(np.uint8)
        image = Image.fromarray(pixels, "RGB")
        if supersampling > 1:
            image = image.resize((width, height), Image.LANCZOS)
        return image

    # ----------------------------------------------------------- núcleo
    def nearest_hit(self, origins, directions):
        """Para cada rayo: distancia al objeto más cercano y su índice."""
        distances = np.stack([obj.intersect(origins, directions)
                              for obj in self.scene.objects])
        index = np.argmin(distances, axis=0)
        t = distances[index, np.arange(len(origins))]
        return t, index

    def trace(self, origins, directions, depth):
        """Color de cada rayo; recursivo para las reflexiones."""
        colors = self.scene.background(directions)
        t, index = self.nearest_hit(origins, directions)
        hit = t < NO_HIT
        if not hit.any():
            return colors

        points = origins[hit] + t[hit, None] * directions[hit]
        view_dirs = directions[hit]
        obj_index = index[hit]
        n_hit = len(points)

        normals = np.zeros((n_hit, 3))
        base = np.zeros((n_hit, 3))
        ka, kd, ks, shin, refl = (np.zeros(n_hit) for _ in range(5))
        for i, obj in enumerate(self.scene.objects):
            sel = obj_index == i
            if not sel.any():
                continue
            m = obj.material
            normals[sel] = obj.normal_at(points[sel])
            base[sel] = m.color_at(points[sel])
            ka[sel], kd[sel], ks[sel] = m.ambient, m.diffuse, m.specular
            shin[sel], refl[sel] = m.shininess, m.reflectivity

        local = self.phong(points, normals, view_dirs, base, ka, kd, ks, shin)

        if depth < self.max_depth:
            mirror = refl > 0
            if mirror.any():
                r_dirs = normalize(reflect(view_dirs[mirror], normals[mirror]))
                r_origins = points[mirror] + EPSILON * normals[mirror]
                reflected = self.trace(r_origins, r_dirs, depth + 1)
                local[mirror] = ((1 - refl[mirror, None]) * local[mirror]
                                 + refl[mirror, None] * reflected)

        colors[hit] = local
        return colors

    def phong(self, points, normals, view_dirs, base, ka, kd, ks, shin):
        """I = ka·base + Σ luz [ kd (N·L) base + ks (R·V)^n ] con sombras."""
        result = ka[:, None] * base
        for light in self.scene.lights:
            to_light = light.position - points
            distance = np.linalg.norm(to_light, axis=1)
            l_dirs = to_light / distance[:, None]

            # Rayo de sombra: ¿hay algo entre el punto y la luz?
            s_origins = points + EPSILON * normals
            shadow_t, _ = self.nearest_hit(s_origins, l_dirs)
            lit = (shadow_t >= distance).astype(float)

            n_dot_l = np.maximum(dot(normals, l_dirs), 0.0)
            r_dirs = reflect(-l_dirs, normals)
            r_dot_v = np.maximum(dot(r_dirs, -view_dirs), 0.0)
            fade = light.intensity / (1.0 + light.attenuation * distance ** 2)

            diffuse = (kd * n_dot_l)[:, None] * base
            specular = (ks * r_dot_v ** shin)[:, None] * np.ones(3)
            result += (lit * fade)[:, None] * light.color * (diffuse + specular)
        return result
