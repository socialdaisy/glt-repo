"""Render every sensible product x scene combination."""
import os, glob
from scene_studio import place, PAIRINGS, SCENES

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene_library")
os.makedirs(OUT, exist_ok=True)
ROT = [0, -2.5, 3.0, -4.0, 2.0, -1.5, 4.0, -3.0]

n, fails = 0, []
for sku, scenes in PAIRINGS.items():
    if not os.path.exists(f"cutouts/{sku}.png"):
        fails.append((sku, "no cut-out")); continue
    for j, sc in enumerate(scenes):
        rot = ROT[(n + j) % len(ROT)] if SCENES[sc]["kind"] == "flatlay" else 0
        out = os.path.join(OUT, f"{sku.replace('glt-','')}__{sc}.jpg")
        try:
            place(sku, sc, out, rotate=rot)
            n += 1
        except Exception as e:
            fails.append((sku, sc, str(e)))
print(f"{n} scene images -> {OUT}")
for f in fails: print("  FAIL", f)
