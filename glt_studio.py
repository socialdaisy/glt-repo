"""
GLT STUDIO - the Girls Love Things photography engine.

Takes a real cut-out product and composes it into a branded scene.
The product pixels are never regenerated, so the artwork and any swearing on it
stays exactly as printed. Everything around it is drawn to the brand guidelines:
palette colours only, Poppins + Lora only, a martini motif in every layout,
one dominant colour per tile.

Usage:
    from glt_studio import Studio, BRAND, PRODUCT_LED
    s = Studio(palette=BRAND)
    s.render("hero", sku="glt-mug-sweary-animal-print", size="feed",
             headline="GIRL DINNER O'CLOCK", accent="well, hello",
             body="Mugs from GBP 10.35", dominant="pink", out="tile.png")
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
CUTOUTS = os.path.join(BASE, "cutouts")
FONTDIR = "/usr/share/fonts/truetype/google-fonts"

F_DISPLAY = os.path.join(FONTDIR, "Poppins-Bold.ttf")
F_BODY    = os.path.join(FONTDIR, "Poppins-Medium.ttf")
F_BODY_R  = os.path.join(FONTDIR, "Poppins-Regular.ttf")
F_ACCENT  = os.path.join(FONTDIR, "Lora-Italic-Variable.ttf")

# ---------------------------------------------------------------- palettes

# Straight from GIRLSLOVETHINGSbrandguidelines.pdf
BRAND = {
    "cream":  "#F7EEDC",   # Butter Cream  - main background
    "pink":   "#E14B7A",   # Spritz Pink   - primary
    "olive":  "#7C8A3F",   # Martini Olive - primary secondary
    "ink":    "#2A211B",   # Espresso Ink  - body text
    "blush":  "#F1C9BC",   # Blush
    "berry":  "#A6325C",   # Berry
    "deep":   "#55602A",   # Deep Olive
    "negroni":"#DE5230",   # Negroni       - use sparingly
    "gold":   "#E9A63A",   # Marg Gold     - highlights
    "white":  "#FFFFFF",
}

# Sampled from what the products are actually printed in
PRODUCT_LED = {
    "cream":  "#F7EEDC",
    "pink":   "#E14B7A",
    "olive":  "#7CB342",   # the bright green on the Girl Dinner artwork
    "ink":    "#1C2B21",
    "blush":  "#F1C9BC",
    "berry":  "#A6325C",
    "deep":   "#2F6B33",
    "negroni":"#F5901E",   # the orange on the tote and Girl Dinner print
    "gold":   "#E9A63A",
    "white":  "#FFFFFF",
}

# Only these ship with a mountboard window frame - the two posters are sold
# unframed, so we must not draw a mount around them.
MOUNTED = {
    "glt-print-girl-dinner-martini",
    "glt-print-girl-dinner-combo",
    "glt-print-girl-dinner-wall-art",
    "glt-print-cocktail-trends-2025",
    "glt-print-lime-leopard-love-you-bye",
}

SIZES = {
    "feed":     (1080, 1080),   # square grid post
    "portrait": (1080, 1350),   # 4:5, the one that takes most feed space
    "story":    (1080, 1920),   # stories + reels cover
}

# text colour that stays readable on each background
ON = {
    "cream": "ink", "blush": "ink", "gold": "ink", "white": "ink",
    "pink": "cream", "olive": "cream", "ink": "cream",
    "berry": "cream", "deep": "cream", "negroni": "cream",
}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- motifs

def martini_glass(size, colour, width=None):
    """Line-drawn martini glass with three olives - the brand's thread motif."""
    S = size
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = width or max(2, S // 26)
    m = S * 0.14
    # bowl
    d.line([(m, m * 1.5), (S - m, m * 1.5)], fill=colour, width=w)
    d.line([(m, m * 1.5), (S / 2, S * 0.58)], fill=colour, width=w)
    d.line([(S - m, m * 1.5), (S / 2, S * 0.58)], fill=colour, width=w)
    # stem + foot
    d.line([(S / 2, S * 0.58), (S / 2, S - m)], fill=colour, width=w)
    d.line([(S * 0.30, S - m), (S * 0.70, S - m)], fill=colour, width=w)
    # olives on a stick
    d.line([(S * 0.52, S * 0.46), (S * 0.80, S * 0.12)], fill=colour, width=max(1, w // 2))
    r = S * 0.055
    for i, (ox, oy) in enumerate([(0.53, 0.44), (0.58, 0.38), (0.63, 0.32)]):
        cx, cy = S * ox, S * oy
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    return im


def sparkle(size, colour):
    """Four-point star."""
    S = size
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, k = S / 2, S * 0.13
    d.polygon([(c, 0), (c + k, c - k), (S, c), (c + k, c + k),
               (c, S), (c - k, c + k), (0, c), (c - k, c - k)], fill=colour)
    return im


def scallop_strip(width, radius, colour, flip=False):
    """A row of half-circles - the scalloped edge from the guidelines."""
    h = radius
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = max(1, width // (radius * 2))
    step = width / n
    for i in range(n + 1):
        cx = i * step + step / 2
        box = [cx - step / 2, -h if flip else 0, cx + step / 2, h if flip else 2 * h]
        d.ellipse(box, fill=colour)
    return im


def checkerboard_strip(width, cell, colour_a, colour_b):
    im = Image.new("RGBA", (width, cell * 2), _hex(colour_b) + (255,))
    d = ImageDraw.Draw(im)
    for i in range(width // cell + 1):
        for j in range(2):
            if (i + j) % 2 == 0:
                d.rectangle([i * cell, j * cell, (i + 1) * cell, (j + 1) * cell], fill=colour_a)
    return im


def polka_field(size, colour, spacing, radius, jitter=0):
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = random.Random(7)
    for y in range(0, h + spacing, spacing):
        offset = (spacing // 2) if (y // spacing) % 2 else 0
        for x in range(-spacing, w + spacing, spacing):
            cx = x + offset + (rng.randint(-jitter, jitter) if jitter else 0)
            cy = y + (rng.randint(-jitter, jitter) if jitter else 0)
            d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=colour)
    return im


def wavy_line(width, amp, period, colour, thickness):
    im = Image.new("RGBA", (width, amp * 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(x, amp * 1.5 + amp * math.sin(2 * math.pi * x / period)) for x in range(width)]
    d.line(pts, fill=colour, width=thickness, joint="curve")
    return im


# ---------------------------------------------------------------- text

def _font(path, size):
    return ImageFont.truetype(path, size)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, path, max_w, max_h, start, min_size=20, leading=1.06):
    """Shrink until the wrapped block fits the box. Returns (font, lines, line_h)."""
    size = start
    while size > min_size:
        f = _font(path, size)
        lines = _wrap(draw, text, f, max_w)
        lh = int(size * leading)
        if len(lines) * lh <= max_h:
            return f, lines, lh
        size -= 2
    f = _font(path, min_size)
    return f, _wrap(draw, text, f, max_w), int(min_size * leading)


def draw_block(draw, lines, font, lh, x, y, fill, align="left", box_w=0):
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=font)
        dx = x
        if align == "center":
            dx = x + (box_w - tw) / 2
        elif align == "right":
            dx = x + box_w - tw
        draw.text((dx, y + i * lh), ln, font=font, fill=fill)
    return y + len(lines) * lh


# ---------------------------------------------------------------- studio

class Studio:
    def __init__(self, palette=BRAND):
        self.p = palette

    def c(self, name):
        return _hex(self.p[name])

    # -- product placement ------------------------------------------------
    @staticmethod
    def _mount(art, side=0.12, top=0.11, bottom=0.17):
        """Wrap a print's artwork in a clean white mount board, the way it ships.
        Drawn rather than cut out, so the edges are always crisp."""
        w, h = art.size
        mx, mt, mb = int(w * side), int(h * top), int(h * bottom)
        card = Image.new("RGBA", (w + 2 * mx, h + mt + mb), (252, 251, 247, 255))
        d = ImageDraw.Draw(card)
        # faint bevel where the mount window meets the print
        d.rectangle([mx - 3, mt - 3, mx + w + 2, mt + h + 2], outline=(0, 0, 0, 38), width=3)
        card.alpha_composite(art, (mx, mt))
        d.rectangle([0, 0, card.width - 1, card.height - 1], outline=(0, 0, 0, 30), width=2)
        return card

    def _product(self, sku, target_h, shadow=True):
        path = os.path.join(CUTOUTS, f"{sku}.png")
        if not os.path.exists(path):
            raise FileNotFoundError(f"no cut-out for {sku} - run cutout.py first")
        im = Image.open(path).convert("RGBA")
        if sku in MOUNTED:
            im = self._mount(im)
        scale = target_h / im.height
        im = im.resize((max(1, int(im.width * scale)), target_h), Image.LANCZOS)
        if not shadow:
            return im, None
        # soft contact shadow so the product sits in the scene instead of floating
        sh = Image.new("RGBA", (im.width + 120, im.height + 120), (0, 0, 0, 0))
        mask = im.split()[3]
        dark = Image.new("RGBA", im.size, (0, 0, 0, 70))
        sh.paste(dark, (60, 72), mask)
        sh = sh.filter(ImageFilter.GaussianBlur(28))
        return im, sh

    def _paste_product(self, canvas, sku, target_h, cx, cy, shadow=True):
        im, sh = self._product(sku, target_h, shadow)
        if sh is not None:
            canvas.alpha_composite(sh, (int(cx - sh.width / 2), int(cy - sh.height / 2)))
        canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
        return im

    # -- templates --------------------------------------------------------
    def render(self, template, sku, size="feed", dominant="pink",
               headline="", accent="", body="", out="out.png"):
        W, H = SIZES[size]
        fn = getattr(self, f"_t_{template}")
        canvas = fn(W, H, sku, dominant, headline, accent, body)
        canvas.convert("RGB").save(out, quality=95)
        return out

    # HERO - solid dominant colour, product large and centred, scalloped trim
    def _t_hero(self, W, H, sku, dom, headline, accent, body):
        bg, fg = self.c(dom), self.c(ON[dom])
        cv = Image.new("RGBA", (W, H), bg + (255,))
        d = ImageDraw.Draw(cv)
        M = int(W * 0.085)

        # scalloped trim along the top
        r = int(W * 0.030)
        cv.alpha_composite(scallop_strip(W, r, self.c("cream") + (255,)), (0, -r))

        y = int(H * 0.10)
        if headline:
            f, lines, lh = fit_text(d, headline.upper(), F_DISPLAY,
                                    W - 2 * M, int(H * 0.20), int(W * 0.098))
            y = draw_block(d, lines, f, lh, M, y, fg, "center", W - 2 * M)
        if accent:
            fa = _font(F_ACCENT, int(W * 0.055))
            tw = d.textlength(accent, font=fa)
            d.text(((W - tw) / 2, y + int(H * 0.012)), accent, font=fa, fill=fg)
            y += int(H * 0.012) + int(W * 0.055)

        foot = int(H * 0.115)
        ph = int((H - y - foot) * 0.92)
        self._paste_product(cv, sku, ph, W // 2, y + (H - y - foot) // 2)

        # martini motif bottom-left, body copy bottom-right
        g = int(W * 0.105)
        cv.alpha_composite(martini_glass(g, fg + (255,)), (M, H - foot - int(g * 0.15)))
        if body:
            fb = _font(F_BODY, int(W * 0.036))
            tw = d.textlength(body, font=fb)
            d.text((W - M - tw, H - foot + int(g * 0.20)), body, font=fb, fill=fg)
        return cv

    # SPLIT - two-tone, arch backdrop, text sitting under the product
    def _t_split(self, W, H, sku, dom, headline, accent, body):
        top, bot = self.c(dom), self.c("cream")
        fg_top, fg_bot = self.c(ON[dom]), self.c("ink")
        cv = Image.new("RGBA", (W, H), bot + (255,))
        d = ImageDraw.Draw(cv)
        M = int(W * 0.085)
        splity = int(H * 0.58)
        d.rectangle([0, 0, W, splity], fill=top)

        # arch backdrop behind the product
        aw, ah = int(W * 0.62), int(H * 0.50)
        ax, ay = (W - aw) // 2, int(H * 0.10)
        arch = Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
        ad = ImageDraw.Draw(arch)
        ad.pieslice([0, 0, aw, aw], 180, 360, fill=self.c("cream") + (255,))
        ad.rectangle([0, aw // 2, aw, ah], fill=self.c("cream") + (255,))
        cv.alpha_composite(arch, (ax, ay))

        # dots scattered on the colour block
        cv.alpha_composite(polka_field((W, splity), fg_top + (60,), int(W * 0.11), int(W * 0.012)))

        self._paste_product(cv, sku, int(H * 0.42), W // 2, ay + int(ah * 0.56))

        y = splity + int(H * 0.045)
        if headline:
            f, lines, lh = fit_text(d, headline.upper(), F_DISPLAY,
                                    W - 2 * M, int(H * 0.20), int(W * 0.085))
            y = draw_block(d, lines, f, lh, M, y, fg_bot, "center", W - 2 * M)
        if accent:
            fa = _font(F_ACCENT, int(W * 0.050))
            tw = d.textlength(accent, font=fa)
            d.text(((W - tw) / 2, y + int(H * 0.010)), accent, font=fa, fill=self.c("berry"))
            y += int(H * 0.010) + int(W * 0.052)
        if body:
            fb = _font(F_BODY_R, int(W * 0.034))
            tw = d.textlength(body, font=fb)
            d.text(((W - tw) / 2, y + int(H * 0.012)), body, font=fb, fill=fg_bot)

        g = int(W * 0.085)
        cv.alpha_composite(martini_glass(g, fg_top + (255,)), (M, int(H * 0.045)))
        cv.alpha_composite(sparkle(int(W * 0.055), self.c("gold") + (255,)),
                           (W - M - int(W * 0.055), int(H * 0.055)))
        return cv

    # STATEMENT - text-led, the joke is the hero, product small and low
    def _t_statement(self, W, H, sku, dom, headline, accent, body):
        bg, fg = self.c(dom), self.c(ON[dom])
        cv = Image.new("RGBA", (W, H), bg + (255,))
        d = ImageDraw.Draw(cv)
        M = int(W * 0.085)

        cv.alpha_composite(polka_field((W, H), fg + (34,), int(W * 0.13), int(W * 0.014)))

        y = int(H * 0.11)
        if accent:
            fa = _font(F_ACCENT, int(W * 0.052))
            d.text((M, y), accent, font=fa, fill=self.c("gold"))
            y += int(W * 0.070)
        if headline:
            f, lines, lh = fit_text(d, headline.upper(), F_DISPLAY,
                                    W - 2 * M, int(H * 0.34), int(W * 0.125), leading=0.99)
            y = draw_block(d, lines, f, lh, M, y, fg, "left", W - 2 * M)

        cv.alpha_composite(wavy_line(int(W * 0.34), int(W * 0.016), int(W * 0.11),
                                     self.c("gold") + (255,), max(3, W // 190)),
                           (M, y + int(H * 0.018)))

        ph = int(H * 0.42)
        self._paste_product(cv, sku, ph, int(W * 0.66), int(H * 0.715))

        cv.alpha_composite(martini_glass(int(W * 0.15), fg + (255,)),
                           (M, int(H * 0.635)))
        if body:
            fb = _font(F_BODY, int(W * 0.034))
            d.text((M, H - int(H * 0.075)), body, font=fb, fill=fg)
        return cv

    # SHELF - cream room-ish scene with a surface, for wall art and homeware
    def _t_shelf(self, W, H, sku, dom, headline, accent, body):
        wall, fg = self.c("cream"), self.c("ink")
        accent_c = self.c(dom)
        cv = Image.new("RGBA", (W, H), wall + (255,))
        d = ImageDraw.Draw(cv)
        M = int(W * 0.085)

        # colour block behind, surface below - reads as a styled corner
        d.rectangle([0, int(H * 0.055), W, int(H * 0.635)], fill=accent_c)
        d.rectangle([0, int(H * 0.635), W, int(H * 0.668)], fill=self.c("ink"))
        cv.alpha_composite(checkerboard_strip(W, int(W * 0.030),
                                              self.c("ink") + (255,), self.p["cream"]),
                           (0, int(H * 0.668)))

        ph = int(H * 0.455)
        self._paste_product(cv, sku, ph, W // 2, int(H * 0.635) - ph // 2 + int(H * 0.008))

        g = int(W * 0.12)
        cv.alpha_composite(martini_glass(g, self.c(ON[dom]) + (255,)),
                           (W - M - g, int(H * 0.10)))
        cv.alpha_composite(sparkle(int(W * 0.05), self.c("gold") + (255,)),
                           (M, int(H * 0.115)))

        # measure the whole text block first, then place it so nothing runs off
        # the bottom edge when the headline wraps to two lines
        band_top, pad = int(H * 0.715), int(H * 0.030)
        fa = _font(F_ACCENT, int(W * 0.046)) if accent else None
        fb = _font(F_BODY_R, int(W * 0.031)) if body else None
        acc_h = int(W * 0.058) if accent else 0
        bod_h = int(W * 0.044) if body else 0
        avail = H - band_top - pad
        f = lines = None
        lh = 0
        if headline:
            f, lines, lh = fit_text(d, headline.upper(), F_DISPLAY,
                                    W - 2 * M, max(int(W * 0.05), avail - acc_h - bod_h),
                                    int(W * 0.072))
        total = (len(lines) * lh if lines else 0) + acc_h + bod_h
        y = band_top + max(0, (avail - total) // 2)

        if lines:
            y = draw_block(d, lines, f, lh, M, y, fg, "center", W - 2 * M)
        if accent:
            tw = d.textlength(accent, font=fa)
            d.text(((W - tw) / 2, y), accent, font=fa, fill=self.c("berry"))
            y += int(W * 0.058)
        if body:
            tw = d.textlength(body, font=fb)
            d.text(((W - tw) / 2, y), body, font=fb, fill=fg)
        return cv


TEMPLATES = ["hero", "split", "statement", "shelf"]


# ---------------------------------------------------------------- contrast guard

def product_avg_colour(sku):
    """Average RGB of the product's visible pixels - used to avoid putting an
    orange product on an orange background."""
    im = Image.open(os.path.join(CUTOUTS, f"{sku}.png")).convert("RGBA")
    im.thumbnail((200, 200))
    px = [p[:3] for p in im.getdata() if p[3] > 200]
    if not px:
        return (128, 128, 128)
    n = len(px)
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def suggest_dominant(sku, palette=BRAND,
                     exclude=("white", "ink", "gold", "cream", "blush")):
    """Rank the saturated block colours by distance from the product's own colour,
    so the product always separates from its background. Cream and blush are
    excluded - the guidelines cast those as backgrounds, not dominant blocks."""
    pr = product_avg_colour(sku)
    scored = []
    for name, hx in palette.items():
        if name in exclude:
            continue
        c = _hex(hx)
        dist = sum((c[i] - pr[i]) ** 2 for i in range(3)) ** 0.5
        scored.append((dist, name))
    scored.sort(reverse=True)
    return [n for _, n in scored]
