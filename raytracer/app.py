"""Aplicación de escritorio: panel de control + visor 3D OpenGL + ray tracing."""
import copy
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pygame
from OpenGL.GL import glDeleteTextures  # noqa: F401  (comprueba que PyOpenGL esté instalado)

from .materials import Material
from .primitives import Plane, Sphere
from .renderer import Renderer
from .scene_view import SceneView
from .scenes import SCENES
from .ui_widgets import (ACCENT, PANEL_BG, TEXT, TEXT_DIM, UI, Button, Header,
                         ObjectList, Row, Slider, Stepper, layout)

PANEL_WIDTH = 340
MARGIN = 14
TABS = ["Escena", "Objeto", "Render"]
RENDER_HEIGHTS = [120, 240, 360, 480, 600, 768]
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RENDERS_DIR = PROJECT_ROOT / "renders"


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Motor de Ray Tracing - Graficación por Computadora")
        self.size = (1280, 780)
        pygame.display.set_mode(self.size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self.ui = UI()

        self.scene_names = list(SCENES)
        self.scene_index = 0
        self.view = SceneView(SCENES[self.scene_names[0]]()[0])
        self.selected = None
        self.light_index = 0
        self.resolution_index = 1
        self.depth = 3
        self.supersampling = 1
        self.tab = 0

        self.show_raytraced = False
        self.has_image = False
        self.last_image = None
        self.worker = None
        self.result = None
        self.status = "Listo. Arrastra para orbitar, clic para seleccionar, R para renderizar."
        self.orbiting, self.drag_distance = False, 0

        self._build_widgets()
        self._select_first_sphere()

    # ------------------------------------------------------------ estado
    @property
    def scene(self):
        return self.view.scene

    def light(self):
        return self.scene.lights[self.light_index]

    def _select_first_sphere(self):
        spheres = [o for o in self.scene.objects if isinstance(o, Sphere)]
        self.selected = spheres[0] if spheres else None

    def _object_label(self, obj):
        kind = "Plano" if isinstance(obj, Plane) else "Esfera"
        return f"{kind} {self.scene.objects.index(obj) + 1}"

    def _is_sphere(self):
        return isinstance(self.selected, Sphere)

    def _has_object(self):
        return self.selected is not None

    # ----------------------------------------------------------- acciones
    def load_scene(self, step):
        self.scene_index = (self.scene_index + step) % len(self.scene_names)
        self.reset_scene()

    def reset_scene(self):
        self.view.scene = SCENES[self.scene_names[self.scene_index]]()[0]
        self.light_index = 0
        self._select_first_sphere()
        self.status = f"Escena '{self.scene_names[self.scene_index]}' cargada."

    def add_sphere(self):
        material = Material(color=(0.9, 0.6, 0.1), reflectivity=0.2, shininess=80)
        sphere = Sphere(tuple(self.view.target + np.array([0.0, 0.0, 1.5])), 0.8, material)
        self.scene.objects.append(sphere)
        self.selected = sphere
        self.status = f"{self._object_label(sphere)} agregada. Edítala en la pestaña Objeto."

    def delete_selected(self):
        if self.selected is not None and len(self.scene.objects) > 1:
            self.scene.objects.remove(self.selected)
            self.selected = None
            self._select_first_sphere()
            self.status = "Objeto eliminado."

    def select_from_list(self, row):
        self.selected = self.scene.objects[row]

    def change_light(self, step):
        self.light_index = (self.light_index + step) % len(self.scene.lights)

    def change_resolution(self, step):
        self.resolution_index = min(max(self.resolution_index + step, 0), len(RENDER_HEIGHTS) - 1)

    def change_depth(self, step):
        self.depth = min(max(self.depth + step, 0), 8)

    def change_supersampling(self, step):
        self.supersampling = min(max(self.supersampling + step, 1), 4)

    def render_size(self):
        """Mismo encuadre que el visor: la altura la elige el usuario, el ancho sigue su proporción."""
        _, _, viewport_w, viewport_h = self.viewport()
        height = RENDER_HEIGHTS[self.resolution_index]
        return round(height * viewport_w / viewport_h), height

    def render_busy(self):
        return self.worker is not None and self.worker.is_alive()

    def start_render(self):
        """Lanza el ray tracing en un hilo, con la cámara actual del visor 3D."""
        if self.render_busy():
            return
        scene, camera = copy.deepcopy(self.scene), self.view.camera()
        width, height = self.render_size()
        depth, supersampling = self.depth, self.supersampling
        self.result = None
        started = time.perf_counter()

        def work():
            try:
                image = Renderer(scene, camera, max_depth=depth).render(width, height, supersampling)
                self.result = (image, time.perf_counter() - started, None)
            except Exception as error:  # se informa en la barra de estado
                self.result = (None, 0.0, error)

        self.status = f"Renderizando {width}x{height}..."
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def poll_render(self):
        if self.result is None or self.render_busy():
            return
        image, seconds, error = self.result
        self.result = None
        if error is not None:
            self.status = f"Error al renderizar: {error}"
            return
        self.last_image = image
        self.view.upload_image(image)
        self.has_image = True
        self.show_raytraced = True
        self.status = f"Render listo en {seconds:.1f} s. Pulsa T para volver a la vista 3D."

    def toggle_view(self):
        if self.has_image:
            self.show_raytraced = not self.show_raytraced

    def save_image(self):
        if self.last_image is None:
            self.status = "Aún no hay un render que guardar."
            return
        RENDERS_DIR.mkdir(exist_ok=True)
        path = RENDERS_DIR / f"captura_{datetime.now():%Y%m%d_%H%M%S}.png"
        self.last_image.save(path)
        self.status = f"Imagen guardada en renders/{path.name}"

    def run_tests(self):
        try:
            done = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=PROJECT_ROOT,
                                  capture_output=True, text=True, timeout=120)
            lines = done.stdout.strip().splitlines()
            self.status = "Pruebas: " + (lines[-1] if lines else "sin salida")
        except (OSError, subprocess.TimeoutExpired) as error:
            self.status = f"No se pudieron ejecutar las pruebas: {error}"

    # ------------------------------------------------------------ widgets
    def _material_slider(self, label, attr, low, high, fmt="{:.2f}"):
        return Slider(label, lambda: getattr(self.selected.material, attr),
                      lambda v: setattr(self.selected.material, attr, v),
                      low, high, fmt, visible=self._has_object)

    def _color_slider(self, label, channel):
        def set_channel(value):
            color = list(self.selected.material.color)
            color[channel] = value
            self.selected.material.color = tuple(color)
        return Slider(label, lambda: self.selected.material.color[channel], set_channel,
                      0.0, 1.0, visible=self._is_sphere)

    def _position_slider(self, label, axis):
        def set_axis(value):
            self.selected.center[axis] = value
        return Slider(label, lambda: float(self.selected.center[axis]), set_axis,
                      -8.0, 8.0, visible=self._is_sphere)

    def _light_slider(self, label, axis):
        def set_axis(value):
            position = self.light().position.copy()
            position[axis] = value
            self.light().position = position
        return Slider(label, lambda: float(self.light().position[axis]), set_axis, -10.0, 10.0)

    def _set_radius(self, value):
        self.selected.radius = value

    def _build_widgets(self):
        def items():
            return [(self._object_label(o), tuple(int(c * 255) for c in o.material.color))
                    for o in self.scene.objects]

        self.tab_widgets = [
            [  # --- Escena
                Header(lambda: "Escena"),
                Stepper("", lambda: self.scene_names[self.scene_index],
                        lambda: self.load_scene(-1), lambda: self.load_scene(1)),
                Header(lambda: "Luces"),
                Stepper("Luz", lambda: f"{self.light_index + 1} de {len(self.scene.lights)}",
                        lambda: self.change_light(-1), lambda: self.change_light(1)),
                self._light_slider("Posición X", 0),
                self._light_slider("Posición Y", 1),
                self._light_slider("Posición Z", 2),
                Slider("Intensidad", lambda: self.light().intensity,
                       lambda v: setattr(self.light(), "intensity", v), 0.0, 2.0),
                Header(lambda: "Objetos"),
                Row([Button("Agregar", self.add_sphere),
                     Button("Eliminar", self.delete_selected, self._has_object),
                     Button("Reiniciar", self.reset_scene)]),
                ObjectList(items, lambda: self.scene.objects.index(self.selected)
                           if self.selected in self.scene.objects else -1,
                           self.select_from_list),
            ],
            [  # --- Objeto
                Header(lambda: f"Seleccionado: {self._object_label(self.selected)}"
                       if self.selected else "Ningún objeto seleccionado"),
                self._material_slider("Reflectividad", "reflectivity", 0.0, 1.0),
                self._material_slider("Especular (ks)", "specular", 0.0, 1.0),
                self._material_slider("Difuso (kd)", "diffuse", 0.0, 1.0),
                self._material_slider("Brillo (exponente)", "shininess", 1.0, 500.0, "{:.0f}"),
                self._color_slider("Color rojo", 0),
                self._color_slider("Color verde", 1),
                self._color_slider("Color azul", 2),
                Slider("Radio", lambda: self.selected.radius, self._set_radius, 0.2, 3.0,
                       visible=self._is_sphere),
                self._position_slider("Posición X", 0),
                self._position_slider("Posición Y", 1),
                self._position_slider("Posición Z", 2),
            ],
            [  # --- Render
                Header(lambda: "Calidad del render"),
                Stepper("Resolución", lambda: "{}x{}".format(*self.render_size()),
                        lambda: self.change_resolution(-1), lambda: self.change_resolution(1)),
                Stepper("Rebotes", lambda: str(self.depth),
                        lambda: self.change_depth(-1), lambda: self.change_depth(1)),
                Stepper("Antialiasing", lambda: f"x{self.supersampling}",
                        lambda: self.change_supersampling(-1), lambda: self.change_supersampling(1)),
                Header(lambda: "Verificación"),
                Button("Ejecutar pruebas automáticas", self.run_tests),
            ],
        ]
        self.tab_buttons = [Button(name, lambda i=i: setattr(self, "tab", i))
                            for i, name in enumerate(TABS)]
        self.bottom_buttons = [
            Button(lambda: "Renderizando..." if self.render_busy() else "Renderizar (R)",
                   self.start_render, lambda: not self.render_busy()),
            Row([Button(lambda: "Ver 3D (T)" if self.show_raytraced else "Ver render (T)",
                        self.toggle_view, lambda: self.has_image),
                 Button("Guardar PNG (S)", self.save_image, lambda: self.has_image)]),
        ]

    def _layout(self):
        width, height = self.size
        inner = PANEL_WIDTH - 2 * MARGIN
        tab_width = inner / len(TABS)
        for i, button in enumerate(self.tab_buttons):
            button.x, button.y, button.w = MARGIN + i * tab_width, MARGIN, tab_width - 4
        layout(self.tab_widgets[self.tab], MARGIN, MARGIN + 44, inner)
        layout(self.bottom_buttons, MARGIN, height - 82, inner)

    def _active_widgets(self):
        widgets = self.tab_buttons + self.bottom_buttons
        return widgets + [w for w in self.tab_widgets[self.tab] if w.visible()]

    # ------------------------------------------------------------- eventos
    def viewport(self):
        width, height = self.size
        return PANEL_WIDTH, 0, width - PANEL_WIDTH, height

    def _in_viewport(self, pos):
        x, y, w, h = self.viewport()
        return x <= pos[0] < x + w and y <= pos[1] < y + h

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            actions = {pygame.K_r: self.start_render, pygame.K_t: self.toggle_view,
                       pygame.K_s: self.save_image, pygame.K_DELETE: self.delete_selected}
            if event.key in actions:
                actions[event.key]()
            return True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                          pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            consumed = False
            self._layout()
            for widget in self._active_widgets():
                consumed = widget.handle(event) or consumed
                if consumed and event.type == pygame.MOUSEBUTTONDOWN:
                    break
            if not consumed:
                self._handle_viewport_event(event)
        return True

    def _handle_viewport_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._in_viewport(event.pos):
            self.orbiting, self.drag_distance = True, 0
        elif event.type == pygame.MOUSEMOTION and self.orbiting:
            self.drag_distance += abs(event.rel[0]) + abs(event.rel[1])
            if self.drag_distance > 4:
                self.show_raytraced = False
                self.view.orbit(*event.rel)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.orbiting:
            self.orbiting = False
            if self.drag_distance <= 4 and not self.show_raytraced:
                x, _, w, h = self.viewport()
                self.selected = self.view.pick(event.pos[0] - x, event.pos[1], w, h)
                self.status = (f"{self._object_label(self.selected)} seleccionado."
                               if self.selected else "Selección vacía.")
        elif event.type == pygame.MOUSEWHEEL and self._in_viewport(pygame.mouse.get_pos()):
            self.show_raytraced = False
            self.view.zoom(event.y)

    # -------------------------------------------------------------- dibujo
    def draw(self):
        from OpenGL.GL import (GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClear, glClearColor,
                               glDisable, GL_SCISSOR_TEST)
        width, height = self.size
        glDisable(GL_SCISSOR_TEST)
        glClearColor(*(c / 255 for c in PANEL_BG), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        vx, _, vw, vh = self.viewport()
        gl_rect = (vx, 0, vw, vh)
        if self.show_raytraced and self.has_image:
            self.view.draw_image(gl_rect)
        else:
            self.view.draw_scene(gl_rect, self.selected)

        self.ui.begin(width, height)
        self._layout()
        self.ui.rect(0, 0, PANEL_WIDTH, height, PANEL_BG)
        for i, button in enumerate(self.tab_buttons):
            button.draw(self.ui)
            if i == self.tab:
                self.ui.rect(button.x, button.y + button.height - 3, button.w, 3, ACCENT)
        for widget in self.tab_widgets[self.tab]:
            if widget.visible():
                widget.draw(self.ui)
        for widget in self.bottom_buttons:
            widget.draw(self.ui)
        self._draw_status(vx, vw, height)

    def _draw_status(self, vx, vw, height):
        self.ui.rect(vx, height - 28, vw, 28, (20, 22, 28), 220)
        self.ui.text(self.status, vx + 10, height - 21, 19, TEXT)
        hint = "Arrastrar: orbitar | Rueda: zoom | Clic: seleccionar | Supr: eliminar"
        self.ui.text(hint, vx + vw - 10, height - 21, 17, TEXT_DIM, "right")

    # ------------------------------------------------------------ principal
    def run(self):
        clock, running = pygame.time.Clock(), True
        while running:
            self.size = pygame.display.get_surface().get_size()
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.poll_render()
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()


def main():
    App().run()
