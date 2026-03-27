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

WIDTH = 1024
HEIGHT = 1024

FRAMES = 72          # количество кадров в цикле
FPS = 18             # fps для gif
SEED = 42

# Маска воды:
# белое = внутри воды, черное = вне воды
MASK_PATH = "water_mask.png"

# Выходные данные
OUTPUT_DIR = "../sparkle_frames"
GIF_PATH = "../water_sparkles_preview.gif"

# GIF не умеет мягкую альфу, поэтому делаем превью на фоне
GIF_BACKGROUND = (0, 0, 0)

# Количество искр
PARTICLE_COUNT = 180

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

def clamp(x, a, b):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def hsv_to_rgb255(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

def make_default_mask(width, height):
    """
    Если нет water_mask.png, создаём приближённую внутреннюю область бутылки.
    """
    yy, xx = np.mgrid[0:height, 0:width]

    cx = width // 2
    body_half_w = int(width * 0.11)
    top_y = int(height * 0.16)
    bottom_y = int(height * 0.92)
    cap_radius_y = int(body_half_w * 0.50)

    inside_rect = (
        (xx >= cx - body_half_w) &
        (xx <= cx + body_half_w) &
        (yy >= top_y + cap_radius_y) &
        (yy <= bottom_y - cap_radius_y)
    )

    top_ellipse = (
        (((xx - cx) / max(body_half_w, 1)) ** 2) +
        (((yy - (top_y + cap_radius_y)) / max(cap_radius_y, 1)) ** 2) <= 1.0
    ) & (yy < top_y + cap_radius_y)

    bottom_ellipse = (
        (((xx - cx) / max(body_half_w, 1)) ** 2) +
        (((yy - (bottom_y - cap_radius_y)) / max(cap_radius_y, 1)) ** 2) <= 1.0
    ) & (yy > bottom_y - cap_radius_y)

    mask = np.zeros((height, width), dtype=np.uint8)
    mask[inside_rect | top_ellipse | bottom_ellipse] = 255

    return Image.fromarray(mask, mode="L")

def load_mask(path, width, height):
    if os.path.exists(path):
        mask = Image.open(path).convert("L").resize((width, height), Image.LANCZOS)
        return mask
    print(f"[INFO] Маска {path} не найдена. Использую встроенную приближенную форму.")
    return make_default_mask(width, height)

def random_point_from_mask(mask_arr):
    ys, xs = np.where(mask_arr > 0)
    if len(xs) == 0:
        raise ValueError("Маска воды пустая.")
    idx = random.randint(0, len(xs) - 1)
    return float(xs[idx]), float(ys[idx])

def draw_soft_particle(canvas, x, y, radius, rgb, alpha):
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

def create_particles(mask_img, count):
    """
    Создаём частицы в безопасной зоне внутри маски, чтобы меньше вылезали за края.
    """
    if SPAWN_MASK_SHRINK >= 3:
        spawn_mask = mask_img.filter(ImageFilter.MinFilter(size=SPAWN_MASK_SHRINK))
    else:
        spawn_mask = mask_img

    spawn_arr = np.array(spawn_mask, dtype=np.uint8)
    if np.count_nonzero(spawn_arr) == 0:
        spawn_arr = np.array(mask_img, dtype=np.uint8)

    particles = []

    for _ in range(count):
        x, y = random_point_from_mask(spawn_arr)

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
    tw1 = 0.5 + 0.5 * math.sin(math.tau * (t * p.twinkle_speed_1) + p.phase_1)
    tw1 = tw1 ** 2.6

    # Медленная дополнительная модуляция, тоже цикличная
    tw2 = 0.72 + 0.28 * (0.5 + 0.5 * math.sin(math.tau * (t * p.twinkle_speed_2) + p.phase_2))

    alpha = p.alpha_peak * tw1 * tw2
    alpha = clamp(alpha, 0.0, 1.0)

    # Очень медленный дрейф
    x = p.base_x + math.sin(math.tau * (t * p.drift_speed_x) + p.drift_phase_x) * DRIFT_AMPLITUDE_X
    y = p.base_y + math.cos(math.tau * (t * p.drift_speed_y) + p.drift_phase_y) * DRIFT_AMPLITUDE_Y

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

def generate_frames():
    random.seed(SEED)
    np.random.seed(SEED)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    mask_img = load_mask(MASK_PATH, WIDTH, HEIGHT)
    mask_arr = np.array(mask_img, dtype=np.uint8)

    particles = create_particles(mask_img, PARTICLE_COUNT)
    frames_rgba = []

    for frame_idx in range(FRAMES):
        t = frame_idx / FRAMES  # [0,1), loop без разрыва

        canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)

        for p in particles:
            x, y, radius, color, alpha = particle_state(p, t)

            if alpha < ALPHA_MIN_VISIBLE:
                continue

            ix = int(round(x))
            iy = int(round(y))
            if ix < 0 or iy < 0 or ix >= WIDTH or iy >= HEIGHT:
                continue
            if mask_arr[iy, ix] == 0:
                continue

            draw_soft_particle(canvas, x, y, radius, color, alpha)

            # Мягкий ореол у более ярких искр
            if alpha > 0.16:
                glow_alpha = alpha * GLOW_STRENGTH * 0.24
                glow_radius = radius * 2.5
                draw_soft_particle(canvas, x, y, glow_radius, color, glow_alpha)

        frame = Image.fromarray(canvas, mode="RGBA")

        if BLUR_RADIUS > 0:
            frame = frame.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))

        # Повторно режем по маске, чтобы blur не вылезал наружу
        frame_arr = np.array(frame, dtype=np.uint8)
        frame_arr[..., 3] = (
            frame_arr[..., 3].astype(np.float32) *
            (mask_arr.astype(np.float32) / 255.0)
        ).astype(np.uint8)

        frame = Image.fromarray(frame_arr, mode="RGBA")

        frame_path = os.path.join(OUTPUT_DIR, f"frame_{frame_idx:03d}.png")
        frame.save(frame_path)
        frames_rgba.append(frame)

        print(f"[{frame_idx + 1}/{FRAMES}] saved: {frame_path}")

    return frames_rgba

# ============================================================
# GIF
# ============================================================

def rgba_frames_to_gif_preview(frames_rgba, gif_path, fps, bg_color=(0, 0, 0)):
    """
    GIF не поддерживает мягкую альфу как PNG,
    поэтому делаем preview, композитя кадры на фон.
    """
    if not frames_rgba:
        return

    duration = int(1000 / fps)
    gif_frames = []

    for frame in frames_rgba:
        bg = Image.new("RGBA", frame.size, bg_color + (255,))
        composed = Image.alpha_composite(bg, frame).convert("P", palette=Image.ADAPTIVE, colors=255)
        gif_frames.append(composed)

    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
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
    rgba_frames_to_gif_preview(frames, GIF_PATH, FPS, GIF_BACKGROUND)
    print("[DONE] Loopable sparkle animation generated.")
