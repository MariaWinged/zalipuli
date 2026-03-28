import os
import math
import random
import colorsys
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

# ============================================================
# НАСТРОЙКИ
# ============================================================

SHIFT = 50

DROW_WIDTH = 1024 * 4
DROW_HEIGHT = 1024 * 4

WIDTH = DROW_WIDTH + SHIFT * 2
HEIGHT = DROW_HEIGHT + SHIFT * 2


FRAMES = 72       # количество кадров в цикле
FRAMES_SHIFT=18

FPS = 18             # fps для gif
SEED = 17

# Маска воды:
# белое = внутри воды, черное = вне воды
MASK_PATH = "water_mask.png"

# Выходные данные
OUTPUT_DIR = "../sparkle_frames"
GIF_PATH = "../water_sparkles_preview.avif"

# Количество искр
PARTICLE_COUNT = 50000

# Размеры частиц
MIN_RADIUS = 0.8
MAX_RADIUS = 3.2

# Для менее насыщенных искр разрешаем быть более непрозрачными,
# для насыщенных — наоборот.
ALPHA_FOR_DESATURATED = 0.58
ALPHA_FOR_SATURATED = 0.20
ALPHA_MIN_VISIBLE = 0.02

# Скорость мерцания
TWINKLE_SPEED_MIN = 0.6
TWINKLE_SPEED_MAX = 1.5

# Медленный дрейф
DRIFT_AMPLITUDE_X = 2.0
DRIFT_AMPLITUDE_Y = 1.4

# Мягкое свечение
GLOW_STRENGTH = 0.55
BLUR_RADIUS = 0.8

# Насколько сильно яркие искры белеют
WHITE_SHIFT_POWER = 0.72

# Размер фильтра для "безопасной" зоны спавна внутри маски
SPAWN_MASK_SHRINK = 9   # нечётное число: 3,5,7,9...

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clamp(x, a, b: float) -> float:
    return max(a, min(b, x))

def lerp(a, b, t: float) -> float:
    return a + (b - a) * t

def lerp_color(c1, c2: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def hsv_to_rgb255(h, s, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

def random_point() -> tuple[int, int]:
    return random.randint(0, DROW_WIDTH) + SHIFT, random.randint(0, DROW_HEIGHT) + SHIFT

def draw_soft_particle(canvas, x, y, radius, rgb, alpha, is_orig=True):
    """
    Рисует мягкую частицу на RGBA canvas (numpy).
    """
    h, w, _ = canvas.shape
    r = max(1, int(math.ceil(radius * 3.2)))

    x0 = max(0, int(x) - r)
    x1 = min(w - 1, int(x) + r)
    y0 = max(0, int(y) - r)
    y1 = min(h - 1, int(y) + r)

    if x0 >= x1 or y0 >= y1:
        return

    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    dx = xx - x
    dy = yy - y
    dist2 = dx * dx + dy * dy

    sigma = max(0.55, radius)
    falloff = np.exp(-dist2 / (2.0 * sigma * sigma))

    local_alpha = np.clip(falloff * alpha, 0.0, 1.0)

    src_rgb = np.zeros((y1 - y0 + 1, x1 - x0 + 1, 3), dtype=np.float32)
    src_rgb[..., 0] = rgb[0]
    src_rgb[..., 1] = rgb[1]
    src_rgb[..., 2] = rgb[2]

    dst = canvas[y0:y1 + 1, x0:x1 + 1].astype(np.float32) / 255.0
    src_a = local_alpha[..., None]
    dst_a = dst[..., 3:4]

    out_a = src_a + dst_a * (1.0 - src_a)
    safe_out_a = np.maximum(out_a, 1e-6)

    out_rgb = (src_rgb / 255.0 * src_a + dst[..., :3] * dst_a * (1.0 - src_a)) / safe_out_a

    out = np.zeros_like(dst)
    out[..., :3] = out_rgb
    out[..., 3:4] = out_a

    canvas[y0:y1 + 1, x0:x1 + 1] = np.clip(out * 255.0, 0, 255).astype(np.uint8)

    if is_orig and x < SHIFT * 2:
        draw_soft_particle(canvas, x + DROW_WIDTH, y, radius, rgb, alpha, False)
    if is_orig and y < SHIFT * 2:
        draw_soft_particle(canvas, x, y + DROW_HEIGHT, radius, rgb, alpha, False)
    if is_orig and x > DROW_WIDTH:
        draw_soft_particle(canvas, x - DROW_WIDTH, y, radius, rgb, alpha, False)
    if is_orig and y > DROW_HEIGHT:
        draw_soft_particle(canvas, x, y - DROW_HEIGHT, radius, rgb, alpha, False)

# ============================================================
# МОДЕЛЬ ЧАСТИЦ
# ============================================================

@dataclass
class Particle:
    base_x: float
    base_y: float
    radius: float

    hue: float
    saturation: float
    value: float

    alpha_peak: float

    twinkle_speed_1: float
    twinkle_speed_2: float
    phase_1: float
    phase_2: float

    drift_phase_x: float
    drift_phase_y: float
    drift_speed_x: float
    drift_speed_y: float

def create_particles(count):
    particles = []

    for _ in range(count):
        x, y = random_point()

        # Случайный цвет искры
        hue = random.random()

        # Делаем насыщенность в широком диапазоне
        # чтобы были как цветные, так и почти белесые искры
        saturation = random.uniform(0.15, 1.0)
        value = random.uniform(0.78, 1.0)

        # Чем насыщеннее искра, тем ниже её максимальная непрозрачность
        sat_t = saturation ** 1.15
        alpha_peak = lerp(ALPHA_FOR_DESATURATED, ALPHA_FOR_SATURATED, sat_t)
        alpha_peak *= random.uniform(0.88, 1.12)
        alpha_peak = clamp(alpha_peak, ALPHA_MIN_VISIBLE, 1.0)

        particles.append(Particle(
            base_x=x,
            base_y=y,
            radius=random.uniform(MIN_RADIUS, MAX_RADIUS),

            hue=hue,
            saturation=saturation,
            value=value,

            alpha_peak=alpha_peak,

            twinkle_speed_1=random.uniform(TWINKLE_SPEED_MIN, TWINKLE_SPEED_MAX),
            twinkle_speed_2=random.uniform(0.18, 0.45),
            phase_1=random.uniform(0, math.tau),
            phase_2=random.uniform(0, math.tau),

            drift_phase_x=random.uniform(0, math.tau),
            drift_phase_y=random.uniform(0, math.tau),
            drift_speed_x=random.uniform(0.08, 0.22),
            drift_speed_y=random.uniform(0.06, 0.16),
        ))

    return particles

def particle_state(p: Particle, t):
    """
    t в диапазоне [0, 1). Все функции периодические => идеальный loop.
    """
    # Основное мерцание
    tw1 = p.twinkle_speed_1 * (0.5 + 0.5 * math.sin(math.tau * t + p.phase_1))
    tw1 = tw1 ** 2.6

    # Медленная дополнительная модуляция, тоже цикличная
    tw2 = p.twinkle_speed_2 * (0.72 + 0.28 * (0.5 + 0.5 * math.sin(math.tau * t + p.phase_2)))

    alpha = p.alpha_peak * tw1 * tw2
    alpha = clamp(alpha, 0.0, 1.0)

    # Очень медленный дрейф
    x = p.base_x + math.sin(math.tau * t + p.drift_phase_x) * DRIFT_AMPLITUDE_X * p.drift_speed_x
    y = p.base_y + math.cos(math.tau * t + p.drift_phase_y) * DRIFT_AMPLITUDE_Y * p.drift_speed_y

    # Базовый случайный цвет искры
    base_color = hsv_to_rgb255(p.hue, p.saturation, p.value)

    # Чем искра более непрозрачна, тем сильнее уходит к белому
    whiten = (alpha / max(p.alpha_peak, 1e-6)) ** WHITE_SHIFT_POWER
    whiten *= 0.85
    whiten = clamp(whiten, 0.0, 1.0)

    color = lerp_color(base_color, (255, 255, 255), whiten)

    # Небольшое "дыхание" размера при вспышке
    radius = p.radius * (0.86 + 0.36 * tw1)

    return x, y, radius, color, alpha

# ============================================================
# ГЕНЕРАЦИЯ
# ============================================================

def generate_frames() -> list[Image.Image]:
    random.seed(SEED)
    np.random.seed(SEED)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    particles = create_particles(PARTICLE_COUNT)
    frames_rgba = []

    for frame_idx in range(-FRAMES_SHIFT, FRAMES):
        t = (frame_idx % FRAMES) / FRAMES  # [0,1), loop без разрыва

        canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)

        for p in particles:
            x, y, radius, color, alpha = particle_state(p, t)

            if alpha < ALPHA_MIN_VISIBLE:
                continue

            draw_soft_particle(canvas, x, y, radius, color, alpha)

            # Мягкий ореол у более ярких искр
            if alpha > 0.16:
                glow_alpha = alpha * GLOW_STRENGTH * 0.24
                glow_radius = radius * 2.5
                draw_soft_particle(canvas, x, y, glow_radius, color, glow_alpha)

        frame: Image.Image = Image.fromarray(canvas, mode="RGBA")

        if BLUR_RADIUS > 0:
            frame = frame.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))

        frame = frame.crop((SHIFT, SHIFT, DROW_WIDTH + SHIFT, DROW_HEIGHT + SHIFT))

        if not (0 <= frame_idx < FRAMES):
            continue

        # для проверки бесшовности
        # frame_big = Image.new("RGBA", (DROW_WIDTH * 2, DROW_HEIGHT * 2), (0, 0, 0, 0))
        # frame_big.paste(frame, (0, 0))
        # frame_big.paste(frame, (0, DROW_HEIGHT))
        # frame_big.paste(frame, (DROW_WIDTH, 0))
        # frame_big.paste(frame, (DROW_WIDTH, DROW_HEIGHT))
        # frame = frame_big.crop((DROW_WIDTH / 2, DROW_HEIGHT / 2, DROW_WIDTH + DROW_WIDTH / 2, DROW_HEIGHT + DROW_HEIGHT / 2))

        frame_path = os.path.join(OUTPUT_DIR, f"frame_{frame_idx:03d}.png")
        frame.save(frame_path)
        frames_rgba.append(frame)

        print(f"[{frame_idx + 1}/{FRAMES}] saved: {frame_path}")

    return frames_rgba

# ============================================================
# GIF
# ============================================================

def rgba_frames_to_gif_preview(frames_rgba: list[Image.Image], gif_path, fps):
    """
    GIF не поддерживает мягкую альфу как PNG,
    поэтому делаем preview, композитя кадры на фон.
    """
    if not frames_rgba:
        return

    duration = int(1000 / fps)

    frames_rgba[0].save(
        gif_path,
        format="AVIF",
        save_all=True,
        append_images=frames_rgba[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=False
    )

    print(f"[OK] GIF saved: {gif_path}")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    frames = generate_frames()
    rgba_frames_to_gif_preview(frames, GIF_PATH, FPS)
    print("[DONE] Loopable sparkle animation generated.")
