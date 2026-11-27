"""Punto de entrada: python main.py --scene mirror_spheres --width 800 ..."""
import argparse
import time

from raytracer.renderer import Renderer
from raytracer.scenes import SCENES


def parse_args():
    parser = argparse.ArgumentParser(description="Motor de trazado de rayos")
    parser.add_argument("--scene", choices=SCENES, default="mirror_spheres")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--depth", type=int, default=3, help="reflexiones máximas")
    parser.add_argument("--supersampling", type=int, default=1, help="factor de antialiasing")
    parser.add_argument("--output", default="renders/output.png")
    return parser.parse_args()


def main():
    args = parse_args()
    scene, camera = SCENES[args.scene]()
    renderer = Renderer(scene, camera, max_depth=args.depth)
    start = time.perf_counter()
    image = renderer.render(args.width, args.height, args.supersampling)
    image.save(args.output)
    print(f"Imagen guardada en {args.output} ({time.perf_counter() - start:.1f} s)")


if __name__ == "__main__":
    main()
