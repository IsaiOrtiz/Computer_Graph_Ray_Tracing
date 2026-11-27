"""Widgets 2D dibujados con OpenGL: texto, botones, sliders, listas."""
import pygame
from OpenGL.GL import *  # noqa: F401,F403

PANEL_BG = (30, 32, 40)
WIDGET_BG = (52, 56, 70)
WIDGET_HOVER = (72, 78, 98)
ACCENT = (90, 150, 240)
TEXT = (230, 232, 240)
TEXT_DIM = (150, 156, 175)
DISABLED = (90, 94, 108)


class UI:
    """Dibujo inmediato en coordenadas de ventana (origen arriba a la izquierda)."""

    MAX_CACHED_TEXTS = 400

    def __init__(self):
        self._fonts = {}
        self._texts = {}

    def begin(self, width, height):
        glViewport(0, 0, width, height)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def rect(self, x, y, w, h, color, alpha=255):
        glColor4f(color[0] / 255, color[1] / 255, color[2] / 255, alpha / 255)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x, y + h)
        glEnd()

    def outline(self, x, y, w, h, color, width=2):
        glColor3f(color[0] / 255, color[1] / 255, color[2] / 255)
        glLineWidth(width)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x, y + h)
        glEnd()

    def _font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def text_width(self, text, size=20):
        return self._font(size).size(text)[0]

    def text(self, text, x, y, size=20, color=TEXT, align="left"):
        if not text:
            return
        key = (text, size, color)
        if key not in self._texts:
            if len(self._texts) > self.MAX_CACHED_TEXTS:
                glDeleteTextures([entry[0] for entry in self._texts.values()])
                self._texts.clear()
            surface = self._font(size).render(text, True, color)
            data = pygame.image.tostring(surface, "RGBA", False)
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surface.get_width(), surface.get_height(),
                         0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            self._texts[key] = (texture, surface.get_width(), surface.get_height())
        texture, w, h = self._texts[key]
        if align == "right":
            x -= w
        elif align == "center":
            x -= w / 2
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        for (vx, vy), (s, t) in zip(((x, y), (x + w, y), (x + w, y + h), (x, y + h)),
                                    ((0, 0), (1, 0), (1, 1), (0, 1))):
            glTexCoord2f(s, t)
            glVertex2f(vx, vy)
        glEnd()
        glDisable(GL_TEXTURE_2D)


class Widget:
    height = 30

    def __init__(self, visible=None):
        self.visible = visible or (lambda: True)
        self.x = self.y = self.w = 0

    def contains(self, pos):
        return self.x <= pos[0] < self.x + self.w and self.y <= pos[1] < self.y + self.height

    def handle(self, event):
        return False

    def draw(self, ui):
        pass


def clicked(widget, event):
    return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            and widget.contains(event.pos))


class Header(Widget):
    height = 24

    def __init__(self, text_fn, visible=None):
        super().__init__(visible)
        self.text_fn = text_fn

    def draw(self, ui):
        ui.text(self.text_fn().upper(), self.x, self.y + 6, 18, ACCENT)
        ui.rect(self.x, self.y + self.height - 2, self.w, 1, WIDGET_BG)


class Button(Widget):
    def __init__(self, label, on_click, enabled=None, visible=None):
        super().__init__(visible)
        self.label, self.on_click = label, on_click
        self.enabled = enabled or (lambda: True)

    def handle(self, event):
        if clicked(self, event) and self.enabled():
            self.on_click()
            return True
        return False

    def draw(self, ui):
        enabled = self.enabled()
        hover = enabled and self.contains(pygame.mouse.get_pos())
        ui.rect(self.x, self.y, self.w, self.height, WIDGET_HOVER if hover else WIDGET_BG)
        label = self.label() if callable(self.label) else self.label
        ui.text(label, self.x + self.w / 2, self.y + 8, 20,
                TEXT if enabled else DISABLED, "center")


class Row(Widget):
    """Reparte varios botones en una misma fila."""

    def __init__(self, buttons, visible=None):
        super().__init__(visible)
        self.buttons = buttons

    def _place(self):
        gap = 6
        width = (self.w - gap * (len(self.buttons) - 1)) / len(self.buttons)
        for i, button in enumerate(self.buttons):
            button.x, button.y, button.w = self.x + i * (width + gap), self.y, width

    def handle(self, event):
        self._place()
        return any(button.handle(event) for button in self.buttons)

    def draw(self, ui):
        self._place()
        for button in self.buttons:
            button.draw(ui)


class Stepper(Widget):
    """Etiqueta con botones [-] valor [+]."""
    height = 32

    def __init__(self, label, value_fn, on_dec, on_inc, visible=None):
        super().__init__(visible)
        self.label, self.value_fn = label, value_fn
        self.minus = Button("-", on_dec)
        self.plus = Button("+", on_inc)

    def _place(self):
        """Con etiqueta: botones a la derecha. Sin etiqueta: el valor ocupa todo el ancho."""
        minus_x = self.x + self.w - 150 if self.label else self.x
        for button, bx in ((self.minus, minus_x), (self.plus, self.x + self.w - 30)):
            button.x, button.y, button.w = bx, self.y, 30

    def handle(self, event):
        self._place()
        return self.minus.handle(event) or self.plus.handle(event)

    def draw(self, ui):
        self._place()
        ui.text(self.label, self.x, self.y + 8, 20, TEXT_DIM)
        self.minus.draw(ui)
        self.plus.draw(ui)
        center = (self.minus.x + 30 + self.plus.x) / 2
        ui.text(self.value_fn(), center, self.y + 8, 20, TEXT, "center")


class Slider(Widget):
    height = 34

    def __init__(self, label, get, set_, low, high, fmt="{:.2f}", visible=None):
        super().__init__(visible)
        self.label, self.get, self.set = label, get, set_
        self.low, self.high, self.fmt = low, high, fmt
        self.dragging = False

    def _value_from(self, mouse_x):
        ratio = min(max((mouse_x - self.x) / self.w, 0.0), 1.0)
        return self.low + ratio * (self.high - self.low)

    def handle(self, event):
        if clicked(self, event):
            self.dragging = True
            self.set(self._value_from(event.pos[0]))
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set(self._value_from(event.pos[0]))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        return False

    def draw(self, ui):
        value = self.get()
        ratio = (value - self.low) / (self.high - self.low)
        ui.text(self.label, self.x, self.y, 18, TEXT_DIM)
        ui.text(self.fmt.format(value), self.x + self.w, self.y, 18, TEXT, "right")
        ui.rect(self.x, self.y + 20, self.w, 6, WIDGET_BG)
        ui.rect(self.x, self.y + 20, self.w * ratio, 6, ACCENT)
        ui.rect(self.x + self.w * ratio - 4, self.y + 16, 8, 14, TEXT)


class ObjectList(Widget):
    ROW = 24

    def __init__(self, items_fn, selected_fn, select_fn, max_rows=6, visible=None):
        super().__init__(visible)
        self.items_fn, self.selected_fn, self.select_fn = items_fn, selected_fn, select_fn
        self.max_rows = max_rows
        self.scroll = 0

    @property
    def height(self):
        return self.max_rows * self.ROW + 16

    def handle(self, event):
        items = self.items_fn()
        self.scroll = min(self.scroll, max(0, len(items) - self.max_rows))
        if event.type == pygame.MOUSEWHEEL and self.contains(pygame.mouse.get_pos()):
            self.scroll = min(max(0, self.scroll - event.y), max(0, len(items) - self.max_rows))
            return True
        if clicked(self, event):
            row = int((event.pos[1] - self.y) // self.ROW) + self.scroll
            if 0 <= row < len(items):
                self.select_fn(row)
            return True
        return False

    def draw(self, ui):
        items = self.items_fn()
        self.scroll = min(self.scroll, max(0, len(items) - self.max_rows))
        selected = self.selected_fn()
        for i in range(self.max_rows):
            index = i + self.scroll
            if index >= len(items):
                break
            label, color = items[index]
            top = self.y + i * self.ROW
            ui.rect(self.x, top, self.w, self.ROW - 2, ACCENT if index == selected else WIDGET_BG)
            ui.rect(self.x + 6, top + 5, 12, 12, color)
            ui.text(label, self.x + 26, top + 5, 19, TEXT)
        if len(items) > self.max_rows:
            ui.text(f"{self.scroll + 1}-{min(self.scroll + self.max_rows, len(items))} de {len(items)}"
                    " (rueda para desplazar)", self.x, self.y + self.height + 2, 16, TEXT_DIM)


def layout(widgets, x, y, width, gap=6):
    """Coloca los widgets visibles en una columna y devuelve la y final."""
    for widget in widgets:
        if widget.visible():
            widget.x, widget.y, widget.w = x, y, width
            y += widget.height + gap
    return y
