"""Operaciones vectoriales sobre arreglos de forma (N, 3)."""
import numpy as np


def normalize(vectors):
    """Devuelve los vectores con longitud 1 (los vectores nulos quedan en cero)."""
    vectors = np.asarray(vectors, dtype=float)
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.where(lengths == 0, 1.0, lengths)


def dot(a, b):
    """Producto punto fila por fila."""
    return np.sum(a * b, axis=-1)


def reflect(incident, normal):
    """Reflexión especular: r = d - 2 (d · n) n, con n unitario."""
    return incident - 2.0 * dot(incident, normal)[..., None] * normal
