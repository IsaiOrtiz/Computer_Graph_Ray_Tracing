import numpy as np
import pytest

from raytracer.camera import Camera
from raytracer.materials import Material
from raytracer.primitives import Plane, Sphere
from raytracer.vectors import reflect

M = Material()


def ray(origin, direction):
    return np.array([origin], dtype=float), np.array([direction], dtype=float)


def test_sphere_hit_distance():
    t = Sphere((0, 0, -5), 1, M).intersect(*ray((0, 0, 0), (0, 0, -1)))
    assert t[0] == pytest.approx(4.0)


def test_sphere_miss():
    t = Sphere((0, 0, -5), 1, M).intersect(*ray((0, 0, 0), (0, 1, 0)))
    assert np.isinf(t[0])


def test_sphere_behind_origin_is_ignored():
    t = Sphere((0, 0, 5), 1, M).intersect(*ray((0, 0, 0), (0, 0, -1)))
    assert np.isinf(t[0])


def test_ray_starting_inside_sphere_hits_far_side():
    t = Sphere((0, 0, 0), 2, M).intersect(*ray((0, 0, 0), (0, 0, -1)))
    assert t[0] == pytest.approx(2.0)


def test_plane_hit_and_parallel():
    plane = Plane((0, -1, 0), (0, 1, 0), M)
    assert plane.intersect(*ray((0, 0, 0), (0, -1, 0)))[0] == pytest.approx(1.0)
    assert np.isinf(plane.intersect(*ray((0, 0, 0), (1, 0, 0)))[0])


def test_reflection_off_floor():
    r = reflect(np.array([[1.0, -1.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    assert np.allclose(r, [[1.0, 1.0, 0.0]])


def test_central_ray_points_to_look_at():
    cam = Camera((0, 0, 5), (0, 0, 0))
    _, dirs = cam.generate_rays(3, 3)
    assert np.allclose(dirs[4], [0, 0, -1])
