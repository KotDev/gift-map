#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генератор иконок PWA «Подарки» на чистом Python 3.

Зависимости: только стандартная библиотека (zlib, struct, math, sys, os).
Без PIL и чего-либо ещё.

Примеры:
    python3 tools/make_icons.py            # icon-180, icon-192, icon-512
    python3 tools/make_icons.py 96 1024    # произвольные размеры

Картинка:
  * непрозрачный RGB-PNG (color type 2, без альфа-канала) — iOS не заливает
    углы чёрным;
  * фон — мягкий диагональный градиент кремовый -> розовый -> лиловый
    плюс деликатное белое радиальное свечение в верхней трети;
  * по центру золотая четырёхлучевая «искра» (астроида)
    (|dx|/R)**0.62 + (|dy|/R)**0.62 < 1, R = 0.30 размера;
  * две маленькие искры того же типа.
"""

import math
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SIZES = (180, 192, 512)

# --- фон --------------------------------------------------------------------
# (позиция 0..1, RGB)
BACKGROUND = (
    (0.0, (253, 248, 244)),   # кремовый
    (0.5, (251, 227, 234)),   # розовый
    (1.0, (236, 230, 250)),   # лиловый
)

# --- искры ------------------------------------------------------------------
SPARK_CORE = (255, 246, 214)   # почти белый в центре
SPARK_EDGE = (216, 165, 63)    # золото к краям

# (смещение по x, смещение по y, радиус) — в долях от размера картинки
SPARKS = (
    (0.0, 0.0, 0.30),
    (0.24, -0.22, 0.085),
    (-0.26, 0.20, 0.05),
)

ASTROID_POWER = 0.62
EDGE_INNER = 0.94
EDGE_OUTER = 1.02

# --- свечение ---------------------------------------------------------------
GLOW_CENTER = (0.5, 0.28)   # верхняя треть
GLOW_RADIUS = 0.62
GLOW_STRENGTH = 0.38

GRADIENT_LUT_SIZE = 4096


def smoothstep(edge0, edge1, x):
    """Классический smoothstep, возвращает 0..1."""
    if edge1 <= edge0:
        return 0.0 if x < edge1 else 1.0
    t = (x - edge0) / (edge1 - edge0)
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


def build_gradient_lut(n=GRADIENT_LUT_SIZE):
    """Таблица цветов диагонального градиента."""
    stops = BACKGROUND
    lut = []
    for i in range(n):
        t = i / (n - 1)
        color = stops[-1][1]
        for j in range(len(stops) - 1):
            p0, c0 = stops[j]
            p1, c1 = stops[j + 1]
            if t <= p1 or j == len(stops) - 2:
                k = (t - p0) / (p1 - p0)
                k = 0.0 if k < 0.0 else (1.0 if k > 1.0 else k)
                color = (
                    c0[0] + (c1[0] - c0[0]) * k,
                    c0[1] + (c1[1] - c0[1]) * k,
                    c0[2] + (c1[2] - c0[2]) * k,
                )
                break
        lut.append(color)
    return lut


GRADIENT_LUT = build_gradient_lut()


def spark_color(metric):
    """Цвет искры по метрике: почти белый в центре, золото к краям."""
    u = metric if metric < 1.0 else 1.0
    if u < 0.0:
        u = 0.0
    t = u * u
    return (
        SPARK_CORE[0] + (SPARK_EDGE[0] - SPARK_CORE[0]) * t,
        SPARK_CORE[1] + (SPARK_EDGE[1] - SPARK_CORE[1]) * t,
        SPARK_CORE[2] + (SPARK_EDGE[2] - SPARK_CORE[2]) * t,
    )


def render(size):
    """Возвращает список строк (bytearray RGB) для картинки size x size."""
    lut = GRADIENT_LUT
    lut_max = len(lut) - 1

    # центры и радиусы искр в пиксельных координатах
    sparks = []
    for ox, oy, rf in SPARKS:
        r = rf * size
        # за пределами этого квадрата метрика гарантированно > EDGE_OUTER
        lim = r * (EDGE_OUTER ** (1.0 / ASTROID_POWER))
        sparks.append((size * (0.5 + ox), size * (0.5 + oy), r, lim))

    gx0, gy0 = GLOW_CENTER
    glow_r2 = GLOW_RADIUS * GLOW_RADIUS
    power = ASTROID_POWER
    e_in, e_out = EDGE_INNER, EDGE_OUTER

    rows = []
    inv = 1.0 / size
    for y in range(size):
        py = y + 0.5
        v = py * inv
        row = bytearray(size * 3)
        pos = 0
        for x in range(size):
            px = x + 0.5
            u = px * inv

            # --- фон: диагональный градиент ---
            t = (u + v) * 0.5
            idx = int(t * lut_max)
            if idx < 0:
                idx = 0
            elif idx > lut_max:
                idx = lut_max
            bg = lut[idx]
            r = bg[0]
            g = bg[1]
            b = bg[2]

            # --- белое радиальное свечение в верхней трети ---
            dxg = u - gx0
            dyg = v - gy0
            d2 = dxg * dxg + dyg * dyg
            if d2 < glow_r2:
                k = 1.0 - math.sqrt(d2) / GLOW_RADIUS
                glow = GLOW_STRENGTH * smoothstep(0.0, 1.0, k)
                r += (255.0 - r) * glow
                g += (255.0 - g) * glow
                b += (255.0 - b) * glow

            # --- искры ---
            for scx, scy, sr, lim in sparks:
                dx = px - scx
                if dx < 0.0:
                    dx = -dx
                if dx > lim:
                    continue
                dy = py - scy
                if dy < 0.0:
                    dy = -dy
                if dy > lim:
                    continue

                metric = (dx / sr) ** power + (dy / sr) ** power
                if metric >= e_out:
                    continue

                coverage = 1.0 - smoothstep(e_in, e_out, metric)
                if coverage <= 0.0:
                    continue

                sc = spark_color(metric)
                r += (sc[0] - r) * coverage
                g += (sc[1] - g) * coverage
                b += (sc[2] - b) * coverage

            row[pos] = int(r + 0.5)
            row[pos + 1] = int(g + 0.5)
            row[pos + 2] = int(b + 0.5)
            pos += 3
        rows.append(row)
    return rows


def png_chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, size, rows):
    """Непрозрачный RGB PNG: bit depth 8, color type 2, без альфа-канала."""
    raw = bytearray()
    for row in rows:
        raw.append(0)  # filter type 0 (None)
        raw.extend(row)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + png_chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def parse_sizes(argv):
    if not argv:
        return list(DEFAULT_SIZES)
    sizes = []
    for arg in argv:
        try:
            value = int(arg)
        except ValueError:
            raise SystemExit("Не число: %r" % arg)
        if value < 16 or value > 4096:
            raise SystemExit("Размер вне разумных пределов (16..4096): %d" % value)
        sizes.append(value)
    return sizes


def main(argv):
    sizes = parse_sizes(argv)
    print("Папка назначения: %s" % ROOT)
    for size in sizes:
        rows = render(size)
        path = os.path.join(ROOT, "icon-%d.png" % size)
        written = write_png(path, size, rows)
        print("  %-16s %4dx%-4d %8.1f КБ" % (
            os.path.basename(path), size, size, written / 1024.0))
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
