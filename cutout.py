"""Step 1 of the photography engine: isolate the real product from its supplier mockup.

Every generated scene reuses these cut-outs, so the artwork on the product is always
the genuine artwork - never re-drawn, never re-spelled by a model.
"""
import json, os, sys
import numpy as np, cv2
from rembg import remove, new_session
from PIL import Image


def keep_largest_blob(img):
    """Drop stray specks and slivers the matting model leaves behind - keep only
    the main product silhouette (plus anything big enough to be a real part of it)."""
    a = np.array(img)
    alpha = (a[:, :, 3] > 40).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(alpha, connectivity=8)
    if n <= 2:
        return img
    areas = stats[1:, cv2.CC_STAT_AREA]
    biggest = areas.max()
    keep = {i + 1 for i, ar in enumerate(areas) if ar >= biggest * 0.05}
    mask = np.isin(labels, list(keep))
    a[:, :, 3] = np.where(mask, a[:, :, 3], 0)
    return Image.fromarray(a)

def rect_artwork(img, tol=26):
    """For framed prints the mount is near-white on a near-white backdrop, which no
    matting model can separate. Instead: sample the actual backdrop colour from the
    corners, keep everything far enough from it, and crop that rectangle. Works
    whether the mockup sits on white or on a beige wall.
    """
    a = np.array(img.convert("RGB")).astype(np.int16)
    h, w = a.shape[:2]
    c = max(8, min(h, w) // 25)
    corners = np.concatenate([
        a[:c, :c].reshape(-1, 3), a[:c, -c:].reshape(-1, 3),
        a[-c:, :c].reshape(-1, 3), a[-c:, -c:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    mask = (dist > tol).astype(np.uint8)
    k = np.ones((11, 11), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return img.convert("RGBA")
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, bw, bh = (stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP],
                    stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT])
    if bw * bh < 0.02 * w * h:          # nothing convincing found - leave it alone
        return img.convert("RGBA")
    return img.convert("RGBA").crop((x, y, x + bw, y + bh))


BASE = "/root/girls-love-things"
OUT = os.path.join(BASE, "cutouts")
os.makedirs(OUT, exist_ok=True)

cat = json.load(open(os.path.join(BASE, "catalogue.json")))
session = new_session("u2net")

# image index (1-based) that best shows the product flat/front-on, per SKU
PREFERRED = {
    "glt-digital-martini-invite": 2,
    "glt-digital-spicy-marg-invite": 3,
    "glt-tee-girl-dinner": 1,
    "glt-tote-martini-caesar-fries": 1,
    "glt-mug-sweary-animal-print": 3,
    "glt-print-girl-dinner-martini": 1,
    "glt-tee-boxy-neon-fuck-this-shit": 1,
    "glt-notebook-sweary-animal-print": 1,
    "glt-tee-spicy-marg-navy": 1,
    "glt-print-cocktail-trends-2025": 1,
    "glt-print-lime-leopard-love-you-bye": 1,
    "glt-tee-margarita-fun": 1,
}

only = sys.argv[1:] if len(sys.argv) > 1 else None

for p in cat["products"]:
    sku = p["sku"]
    if only and sku not in only:
        continue
    idx = PREFERRED.get(sku, 1)
    src = os.path.join(BASE, "assets", sku, f"{sku}-{idx:02d}.jpg")
    if not os.path.exists(src):
        print(f"  skip {sku} (no image {idx})")
        continue
    im = Image.open(src).convert("RGBA")
    if sku.startswith("glt-print-"):
        cut = rect_artwork(im)                       # geometric crop, no matting
    else:
        cut = remove(im, session=session, post_process_mask=True)
        cut = keep_largest_blob(cut)
        bbox = cut.getbbox()
        if bbox:
            cut = cut.crop(bbox)
    cut.thumbnail((1600, 1600), Image.LANCZOS)
    dst = os.path.join(OUT, f"{sku}.png")
    cut.save(dst)
    print(f"  {sku}: {cut.size[0]}x{cut.size[1]}")

print("\ncut-outs written to", OUT)
