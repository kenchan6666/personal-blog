from __future__ import annotations

from collections import deque
from io import BytesIO
from statistics import median

from PIL import Image


def isolate_hero_subject(data: bytes) -> bytes:
    source = Image.open(BytesIO(data)).convert("RGBA")
    if _has_useful_alpha(source):
        return _png_bytes(_crop_to_opaque(source))

    knocked = _knockout_edge_background(source)
    if knocked.getbbox() is None:
        return _png_bytes(source)
    return _png_bytes(_crop_to_opaque(knocked))


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _has_useful_alpha(image: Image.Image) -> bool:
    extrema = image.getextrema()
    if len(extrema) < 4:
        return False
    amin, amax = extrema[3]
    return amin < 240 and amax > 10


def _color_dist(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    return (
        (left[0] - right[0]) ** 2
        + (left[1] - right[1]) ** 2
        + (left[2] - right[2]) ** 2
    ) ** 0.5


def _knockout_edge_background(image: Image.Image, threshold: int = 34) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    edges: list[tuple[int, int, int]] = []
    for x in range(width):
        edges.append(pixels[x, 0][:3])
        edges.append(pixels[x, height - 1][:3])
    for y in range(height):
        edges.append(pixels[0, y][:3])
        edges.append(pixels[width - 1, y][:3])

    background = tuple(int(median([color[i] for color in edges])) for i in range(3))
    varied = sum(1 for color in edges if _color_dist(color, background) > threshold)
    if varied / max(len(edges), 1) > 0.45:
        return image

    out = image.copy()
    dest = out.load()
    seen = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def offer(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        index = y * width + x
        if seen[index]:
            return
        if _color_dist(pixels[x, y][:3], background) > threshold:
            return
        seen[index] = 1
        queue.append((x, y))

    for x in range(width):
        offer(x, 0)
        offer(x, height - 1)
    for y in range(height):
        offer(0, y)
        offer(width - 1, y)

    while queue:
        x, y = queue.popleft()
        red, green, blue, _alpha = pixels[x, y]
        dest[x, y] = (red, green, blue, 0)
        offer(x - 1, y)
        offer(x + 1, y)
        offer(x, y - 1)
        offer(x, y + 1)

    return _feather_cutout(out)


def _feather_cutout(image: Image.Image) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    soften: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y][3] == 0:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny][3] == 0:
                    soften.append((x, y))
                    break
    for x, y in soften:
        red, green, blue, _alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 140)
    return image


def _crop_to_opaque(image: Image.Image, pad: int = 8) -> Image.Image:
    box = image.getbbox()
    if box is None:
        return image
    left, top, right, bottom = box
    return image.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad),
            min(image.height, bottom + pad),
        )
    )
