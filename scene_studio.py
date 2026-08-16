"""
GLT SCENE STUDIO - places real products into real rooms.

The product is never redrawn. It is cut from a genuine product photo, scaled,
colour-matched to the room's light, given a shadow that agrees with that light,
and composited in. The scenes are AI-generated empty rooms; the products are not.

All ten scenes are lit from the upper LEFT, so every shadow falls down and to the
RIGHT. That single consistency is what stops a composite reading as fake.

    from scene_studio import place, SCENES, PAIRINGS
    place("glt-mug-sweary-animal-print", "kitchen-counter", "out.jpg")
"""
import os, glob
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops

BASE = os.path.dirname(os.path.abspath(__file__))
CUTOUTS = os.path.join(BASE, "cutouts")
SCENEDIR = os.path.join(BASE, "scenes")
MOUNTED = {
    "glt-print-girl-dinner-martini", "glt-print-girl-dinner-combo",
    "glt-print-girl-dinner-wall-art", "glt-print-cocktail-trends-2025",
    "glt-print-lime-leopard-love-you-bye",
}

# kind:
#   surface - product stands on a horizontal surface (contact + cast shadow)
#   wall    - product hangs flat on a wall (offset drop shadow, no contact)
#   flatlay - shot from directly above (soft all-round shadow, no perspective)
#   hook    - product hangs from a hook (shadow behind, hangs down from anchor)
# anchor: (x, y) as a fraction of the scene. For `surface` and `hook` this is where
#         the BASE / TOP of the product sits; for `wall` and `flatlay` it's the centre.
# height: product height as a fraction of the scene height.
SCENES = {
    "kitchen-counter": dict(file="scene-01-kitchen-counter.jpg", kind="surface",
                            anchor=(0.44, 0.66), height=0.20),
    "bar-cart":        dict(file="scene-02-bar-cart.jpg",        kind="surface",
                            anchor=(0.48, 0.455), height=0.125),
    "bedside-table":   dict(file="scene-03-bedside-table.jpg",   kind="surface",
                            anchor=(0.40, 0.575), height=0.16),
    "gallery-wall":    dict(file="scene-04-gallery-wall.jpg",    kind="wall",
                            anchor=(0.50, 0.36),  height=0.40),
    "kitchen-wall":    dict(file="scene-05-kitchen-wall.jpg",    kind="wall",
                            anchor=(0.53, 0.33),  height=0.38),
    "desk":            dict(file="scene-06-desk.jpg",            kind="surface",
                            anchor=(0.44, 0.710), height=0.235),
    "cafe-table":      dict(file="scene-07-cafe-table.jpg",      kind="surface",
                            anchor=(0.48, 0.675), height=0.145),
    "entryway":        dict(file="scene-08-entryway.jpg",        kind="hook",
                            anchor=(0.60, 0.115), height=0.30),
    "bed-flatlay":     dict(file="scene-09-bed-flatlay.jpg",     kind="flatlay",
                            anchor=(0.50, 0.55),  height=0.62),
    "neutral-flatlay": dict(file="scene-10-neutral-flatlay.jpg", kind="flatlay",
                            anchor=(0.52, 0.55),  height=0.58),
}

# which products belong in which rooms - a mug on a gallery wall helps nobody
PAIRINGS = {
    "glt-mug-sweary-animal-print":        ["kitchen-counter", "bedside-table", "desk", "cafe-table"],
    "glt-notebook-sweary-animal-print":   ["desk", "bedside-table", "neutral-flatlay"],
    "glt-sticker-girl-lunch-martini":     ["desk", "neutral-flatlay"],
    "glt-tote-martini-caesar-fries":      ["entryway", "neutral-flatlay"],
    "glt-tee-girl-dinner":                ["bed-flatlay", "neutral-flatlay"],
    "glt-tee-boxy-neon-fuck-this-shit":   ["bed-flatlay", "neutral-flatlay"],
    "glt-tee-margarita-fun":              ["bed-flatlay", "neutral-flatlay"],
    "glt-tee-martini-salad-chips":        ["bed-flatlay", "neutral-flatlay"],
    "glt-tee-girl-lunch-spicy-marg":      ["bed-flatlay", "neutral-flatlay"],
    "glt-tee-spicy-marg-navy":            ["bed-flatlay", "neutral-flatlay"],
    "glt-print-girl-dinner-martini":      ["gallery-wall", "kitchen-wall"],
    "glt-print-girl-dinner-combo":        ["gallery-wall", "kitchen-wall"],
    "glt-print-girl-dinner-wall-art":     ["gallery-wall", "kitchen-wall"],
    "glt-print-cocktail-trends-2025":     ["gallery-wall", "kitchen-wall"],
    "glt-print-lime-leopard-love-you-bye":["gallery-wall", "kitchen-wall"],
    # sweary poster omitted: its listing artwork still carries the Canva
    # placeholder watermark "reallygreatsite.com" (see notes). Re-add once the
    # source design is fixed and the listing images are replaced.
    "glt-print-spicy-marg-poster":        ["gallery-wall", "kitchen-wall"],
    # The three digital invite templates are omitted from scene work entirely.
    # They are Canva files, not objects - a buyer wants to see the design flat and
    # full-bleed, and cutting them out just yields a floating cocktail glass.
}


def _mount(art, side=0.12, top=0.11, bottom=0.17):
    w, h = art.size
    mx, mt, mb = int(w * side), int(h * top), int(h * bottom)
    card = Image.new("RGBA", (w + 2 * mx, h + mt + mb), (252, 251, 247, 255))
    d = ImageDraw.Draw(card)
    d.rectangle([mx - 3, mt - 3, mx + w + 2, mt + h + 2], outline=(0, 0, 0, 38), width=3)
    card.alpha_composite(art, (mx, mt))
    d.rectangle([0, 0, card.width - 1, card.height - 1], outline=(0, 0, 0, 30), width=2)
    return card


def _load_product(sku, target_h):
    p = os.path.join(CUTOUTS, f"{sku}.png")
    im = Image.open(p).convert("RGBA")
    if sku in MOUNTED:
        im = _mount(im)
    s = target_h / im.height
    return im.resize((max(1, int(im.width * s)), target_h), Image.LANCZOS)


def _light_wrap(prod, scene, box, strength=0.20, warmth=1.04):
    """Bleed a little of the room's colour into the product and warm it slightly,
    so it sits in the same light instead of looking pasted on."""
    x0, y0, x1, y1 = box
    region = scene.crop((max(0, x0), max(0, y0),
                         min(scene.width, x1), min(scene.height, y1))).convert("RGB")
    region = region.resize((1, 1), Image.LANCZOS)
    avg = region.getpixel((0, 0))

    rgb = prod.convert("RGB")
    tint = Image.new("RGB", prod.size, avg)
    rgb = Image.blend(rgb, tint, strength)
    r, g, b = rgb.split()
    r = r.point(lambda v: min(255, int(v * warmth)))
    b = b.point(lambda v: int(v / warmth))
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Contrast(rgb).enhance(0.96)
    out = rgb.convert("RGBA")
    out.putalpha(prod.split()[3])
    return out


def _cast_shadow(mask, kind, size):
    """Shadow that agrees with light from the upper left, so it falls down-right."""
    w, h = mask.size
    pad = int(max(w, h) * 0.9) + 40
    canvas = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)

    if kind == "wall":
        canvas.paste(mask, (pad + int(w * 0.045), pad + int(h * 0.035)))
        canvas = canvas.filter(ImageFilter.GaussianBlur(max(6, w * 0.030)))
        return canvas, 118
    if kind == "flatlay":
        canvas.paste(mask, (pad + int(w * 0.022), pad + int(h * 0.022)))
        canvas = canvas.filter(ImageFilter.GaussianBlur(max(8, w * 0.035)))
        return canvas, 96
    if kind == "hook":
        canvas.paste(mask, (pad + int(w * 0.06), pad + int(h * 0.03)))
        canvas = canvas.filter(ImageFilter.GaussianBlur(max(8, w * 0.045)))
        return canvas, 105

    # surface: squash the silhouette into the ground plane and shear it right
    sh_h = max(1, int(h * 0.30))
    flat = mask.resize((w, sh_h), Image.LANCZOS)
    shear = Image.new("L", (int(w * 1.7), sh_h), 0)
    shear.paste(flat, (0, 0))
    shear = shear.transform(shear.size, Image.AFFINE, (1, -0.85, 0, 0, 1, 0),
                            resample=Image.BICUBIC)
    canvas.paste(shear, (pad, pad + h - sh_h // 2))
    canvas = canvas.filter(ImageFilter.GaussianBlur(max(7, w * 0.045)))

    # tight contact shadow so the base doesn't float
    contact = Image.new("L", canvas.size, 0)
    cd = ImageDraw.Draw(contact)
    cd.ellipse([pad + int(w * 0.10), pad + h - int(h * 0.045),
                pad + int(w * 0.90), pad + h + int(h * 0.045)], fill=190)
    contact = contact.filter(ImageFilter.GaussianBlur(max(4, w * 0.022)))
    canvas = ImageChops.lighter(canvas, contact)
    return canvas, 130


def place(sku, scene_key, out, height_scale=1.0, dx=0.0, dy=0.0, crop=None, rotate=0.0):
    """Composite one product into one scene.
    height_scale/dx/dy nudge the default placement, rotate tilts the product a few
    degrees (flat-lays look staged when everything is perfectly square), and crop is
    'feed'|'portrait'|None."""
    cfg = SCENES[scene_key]
    scene = Image.open(os.path.join(SCENEDIR, cfg["file"])).convert("RGBA")
    W, H = scene.size

    prod = _load_product(sku, max(8, int(H * cfg["height"] * height_scale)))
    if rotate:
        prod = prod.rotate(rotate, resample=Image.BICUBIC, expand=True)
    pw, ph = prod.size
    ax, ay = cfg["anchor"][0] + dx, cfg["anchor"][1] + dy
    cx = int(W * ax)
    if cfg["kind"] == "surface":
        top = int(H * ay) - ph          # anchor is the base
    elif cfg["kind"] == "hook":
        top = int(H * ay)               # anchor is where it hangs from
    else:
        top = int(H * ay) - ph // 2     # anchor is the centre
    left = cx - pw // 2

    prod = _light_wrap(prod, scene, (left, top, left + pw, top + ph))

    sh_mask, opacity = _cast_shadow(prod.split()[3], cfg["kind"], (pw, ph))
    pad = (sh_mask.width - pw) // 2
    shadow = Image.new("RGBA", sh_mask.size, (38, 30, 24, 0))
    shadow.putalpha(sh_mask.point(lambda v: int(v * opacity / 255)))
    scene.alpha_composite(shadow, (left - pad, top - pad))
    scene.alpha_composite(prod, (left, top))

    if crop in ("feed", "portrait"):
        ratio = 1.0 if crop == "feed" else 4 / 5
        tw = min(W, int(H * ratio))
        th = min(H, int(tw / ratio))
        # keep the product in frame
        cxx = max(tw // 2, min(W - tw // 2, cx))
        cyy = max(th // 2, min(H - th // 2, top + ph // 2))
        scene = scene.crop((cxx - tw // 2, cyy - th // 2, cxx + tw // 2, cyy + th // 2))

    scene.convert("RGB").save(out, quality=94)
    return out


# ---------------------------------------------------------------- captioned scenes

def scene_post(sku, scene_key, out, size="portrait", headline="", accent="", body="",
               band="cream", rotate=0.0, height_scale=1.0):
    """A scene composite cropped to a social format with an on-brand caption band.
    Keeps the room photography as the hero and the type legible over it."""
    import glt_studio as G
    from PIL import Image, ImageDraw

    tmp = out + ".tmp.jpg"
    place(sku, scene_key, tmp, rotate=rotate, height_scale=height_scale)
    im = Image.open(tmp).convert("RGB")
    os.remove(tmp)

    W, H = G.SIZES[size]
    # cover-crop the scene to the target aspect
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    left = (im.width - W) // 2
    top = int((im.height - H) * 0.32)          # bias up: keep the product, lose floor
    im = im.crop((left, top, left + W, top + H))

    if not (headline or accent or body):
        im.save(out, quality=94)
        return out

    pal = G.PRODUCT_LED
    band_rgb = G._hex(pal[band])
    fg = G._hex(pal[G.ON[band]])
    d = ImageDraw.Draw(im)
    M = int(W * 0.075)

    f, lines, lh = G.fit_text(d, headline.upper(), G.F_DISPLAY, W - 2 * M,
                              int(H * 0.14), int(W * 0.062)) if headline else (None, [], 0)
    acc_h = int(W * 0.052) if accent else 0
    bod_h = int(W * 0.042) if body else 0
    band_h = len(lines) * lh + acc_h + bod_h + int(H * 0.055)

    d.rectangle([0, H - band_h, W, H], fill=band_rgb)
    im.paste(G.scallop_strip(W, int(W * 0.022), band_rgb + (255,)).convert("RGB"),
             (0, H - band_h - int(W * 0.022)),
             G.scallop_strip(W, int(W * 0.022), band_rgb + (255,)))

    y = H - band_h + int(H * 0.022)
    if lines:
        y = G.draw_block(d, lines, f, lh, M, y, fg, "center", W - 2 * M)
    if accent:
        fa = G._font(G.F_ACCENT, int(W * 0.046))
        tw = d.textlength(accent, font=fa)
        d.text(((W - tw) / 2, y), accent, font=fa, fill=G._hex(pal["berry"]))
        y += acc_h
    if body:
        fb = G._font(G.F_BODY_R, int(W * 0.032))
        tw = d.textlength(body, font=fb)
        d.text(((W - tw) / 2, y), body, font=fb, fill=fg)

    g = int(W * 0.062)
    im.paste(G.martini_glass(g, fg + (255,)).convert("RGB"),
             (M // 2, H - band_h - g - int(W * 0.030)),
             G.martini_glass(g, fg + (255,)))
    im.save(out, quality=94)
    return out
