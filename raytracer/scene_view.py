"""Vista 3D de la escena con OpenGL (tubería fija, sin GLU) y selección por rayos."""
import math

import numpy as np
from OpenGL.GL import *  # noqa: F401,F403  (API de OpenGL en estilo C)

from .camera import Camera
from .primitives import Plane, Sphere
from .vectors import normalize

FOV_DEGREES = 45.0
NEAR, FAR = 0.1, 200.0
SPHERE_STACKS, SPHERE_SLICES = 24, 36
PLANE_EXTENT = 20.0


class SceneView:
    """Cámara orbital + dibujo de la escena. No abre ventanas por sí misma."""

    def __init__(self, scene):
        self.scene = scene
        self.yaw, self.pitch, self.distance = 0.0, 18.0, 9.0
        self.target = np.array([0.0, 0.0, -1.0])
        self.texture = None

    # ----------------------------------------------------------- cámara
    def eye_position(self):
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        offset = self.distance * np.array([math.sin(yaw) * math.cos(pitch),
                                           math.sin(pitch),
                                           math.cos(yaw) * math.cos(pitch)])
        return self.target + offset

    def camera(self):
        """Cámara del ray tracer equivalente a la vista OpenGL actual."""
        return Camera(self.eye_position(), self.target, fov_degrees=FOV_DEGREES)

    def orbit(self, dx, dy):
        self.yaw -= dx * 0.4
        self.pitch = float(np.clip(self.pitch + dy * 0.4, -85, 85))

    def zoom(self, steps):
        self.distance = float(np.clip(self.distance * (0.9 ** steps), 1.5, 60.0))

    # -------------------------------------------------------- selección
    def pick(self, x, y, width, height):
        """Objeto bajo el píxel (x, y) del visor, usando las intersecciones del ray tracer."""
        cam = self.camera()
        half_h = math.tan(math.radians(FOV_DEGREES) / 2)
        half_w = half_h * width / height
        px = (x / width * 2 - 1) * half_w
        py = (1 - y / height * 2) * half_h
        direction = normalize(px * cam.u + py * cam.v - cam.w)[None]
        origin = cam.position[None]
        best, best_t = None, np.inf
        for obj in self.scene.objects:
            t = obj.intersect(origin, direction)[0]
            if t < best_t:
                best, best_t = obj, t
        return best

    # ----------------------------------------------------------- dibujo
    def draw_scene(self, rect, selected=None):
        """Dibuja la escena 3D dentro de rect = (x, y, w, h) en coordenadas de OpenGL."""
        x, y, w, h = rect
        glViewport(x, y, w, h)
        glEnable(GL_SCISSOR_TEST)
        glScissor(x, y, w, h)
        sky = self.scene.sky_bottom
        glClearColor(sky[0], sky[1], sky[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        self._apply_camera(w / h)
        self._apply_lights()
        for obj in self.scene.objects:
            if isinstance(obj, Plane):
                self._draw_plane(obj)
            elif isinstance(obj, Sphere):
                self._draw_sphere(obj)
        glDisable(GL_LIGHTING)
        if isinstance(selected, Sphere):
            self._draw_selection(selected)
        self._draw_light_markers()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_SCISSOR_TEST)

    def _apply_camera(self, aspect):
        top = NEAR * math.tan(math.radians(FOV_DEGREES) / 2)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum(-top * aspect, top * aspect, -top, top, NEAR, FAR)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -self.distance)
        glRotatef(self.pitch, 1, 0, 0)
        glRotatef(-self.yaw, 0, 1, 0)
        glTranslatef(*(-self.target))

    def _apply_lights(self):
        glEnable(GL_LIGHTING)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.25, 0.25, 0.25, 1.0))
        for i in range(8):
            glDisable(GL_LIGHT0 + i)
        for i, light in enumerate(self.scene.lights[:8]):
            color = tuple(light.color * light.intensity) + (1.0,)
            glEnable(GL_LIGHT0 + i)
            glLightfv(GL_LIGHT0 + i, GL_POSITION, tuple(light.position) + (1.0,))
            glLightfv(GL_LIGHT0 + i, GL_DIFFUSE, color)
            glLightfv(GL_LIGHT0 + i, GL_SPECULAR, color)

    @staticmethod
    def _sphere_mesh(center, radius, stacks=SPHERE_STACKS, slices=SPHERE_SLICES):
        glPushMatrix()
        glTranslatef(*center)
        for i in range(stacks):
            phi0, phi1 = math.pi * i / stacks, math.pi * (i + 1) / stacks
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                theta = 2 * math.pi * j / slices
                for phi in (phi0, phi1):
                    n = (math.sin(phi) * math.cos(theta), math.cos(phi),
                         math.sin(phi) * math.sin(theta))
                    glNormal3f(*n)
                    glVertex3f(*(radius * c for c in n))
            glEnd()
        glPopMatrix()

    def _draw_sphere(self, sphere):
        m = sphere.material
        glColor3f(*m.color)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (m.specular,) * 3 + (1.0,))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, min(m.shininess, 128.0))
        self._sphere_mesh(sphere.center, sphere.radius)

    def _draw_selection(self, sphere):
        """Malla amarilla alrededor de la esfera seleccionada."""
        glColor3f(1.0, 0.9, 0.2)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        self._sphere_mesh(sphere.center, sphere.radius * 1.04, 12, 18)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def _draw_plane(self, plane):
        m = plane.material
        n = plane.normal
        helper = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(n, helper)
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        size = m.checker_size
        cells = int(PLANE_EXTENT / size)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
        glNormal3f(*n)
        glBegin(GL_QUADS)
        for i in range(-cells, cells):
            for j in range(-cells, cells):
                even = (i + j) % 2 == 0
                glColor3f(*(m.color if even or m.checker is None else m.checker))
                for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    glVertex3f(*(plane.point + (i + di) * size * u + (j + dj) * size * v))
        glEnd()

    def _draw_light_markers(self):
        glPointSize(12)
        glBegin(GL_POINTS)
        for light in self.scene.lights:
            glColor3f(1.0, 0.95, 0.4)
            glVertex3f(*light.position)
        glEnd()

    # ------------------------------------------------- imagen ray tracing
    def upload_image(self, image):
        """Sube la imagen PIL a una textura de OpenGL."""
        data = np.asarray(image, dtype=np.uint8)
        if self.texture is None:
            self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.width, image.height, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, data.tobytes())
        self.image_aspect = image.width / image.height

    def draw_image(self, rect):
        """Muestra la imagen ray tracing centrada en rect, conservando su proporción."""
        x, y, w, h = rect
        glViewport(x, y, w, h)
        glEnable(GL_SCISSOR_TEST)
        glScissor(x, y, w, h)
        glClearColor(0.08, 0.08, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glColor3f(1, 1, 1)
        window_aspect = w / h
        if self.image_aspect > window_aspect:
            sx, sy = 1.0, window_aspect / self.image_aspect
        else:
            sx, sy = self.image_aspect / window_aspect, 1.0
        glBegin(GL_QUADS)
        for (vx, vy), (s, t) in zip(((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)),
                                    ((0, 1), (1, 1), (1, 0), (0, 0))):
            glTexCoord2f(s, t)
            glVertex2f(vx, vy)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_SCISSOR_TEST)
