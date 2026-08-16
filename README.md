# GIRLS LOVE THINGS — content engine

Generates a month of on-brand Instagram content for [etsy.com/shop/GIRLSLOVETHINGS](https://www.etsy.com/shop/GIRLSLOVETHINGS) from one command.

**The rule everything is built on: the product is never regenerated.** Every image uses real pixels cut from a genuine product photo, composited into a scene or a branded layout. An image model would misspell the swearing on the mug roughly every other time. This doesn't, because it never redraws it.

---

## Quick start

```bash
pip install -r requirements.txt

python3 launch.py             # the curated first nine posts, for a new profile
python3 batch.py              # next month
python3 batch.py 2026-11      # a specific month
python3 batch.py 2026-11 --posts 3 --stories 2
```

Output lands in `campaign/<month>/` (or `launch/`) with every image named by date, plus `schedule.csv` and `schedule.md` carrying captions, hashtags and listing links.

---

## What's here

| File | Does |
|---|---|
| `copy_bank.py` | **The voice.** Every headline, accent line and caption. Edit this and all future months change. |
| `batch.py` | Builds a month — picks products, formats, colours and dates. |
| `launch.py` | The hand-curated first nine, for a profile with no posts yet. |
| `glt_studio.py` | Brand-colour tiles — palette, Poppins/Lora type, martini motif, four layouts. |
| `scene_studio.py` | Composites products into the ten room photographs. |
| `cutout.py` | Isolates products from supplier mockups into `cutouts/`. |
| `catalogue.json` | All 20 listings — titles, prices, variations, image URLs. |
| `download_images.py` | Re-downloads the 81 source listing images from Etsy into `assets/`. Not committed — they are large and always re-fetchable. |
| `scenes/` | Ten empty rooms, all lit from the upper left. |

---

## Adding a product

1. Add it to `catalogue.json` (copy an existing block).

> Source mockups aren't stored in git — run `download_images.py` first if `assets/` is empty.
2. `python3 download_images.py` to pull its listing images.
3. `python3 cutout.py <sku>` to isolate it.
4. Add 1–3 copy variants to `copy_bank.py`.
5. Add it to `PAIRINGS` in `scene_studio.py` so it knows which rooms suit it.

It joins the rotation on the next run.

---

## Rules the generator enforces

So a month doesn't read as machine-made:

- the same product never reappears within 6 days
- layouts rotate, never twice in a row
- background colour is picked to *contrast* with that product, so nothing disappears into its own colour
- copy variants cycle — nothing repeats inside a month
- design families get airtime in proportion to how much of the shop they are
- content alternates real-room photography with colour tiles

---

## Currently held back

- **`glt-print-sweary-poster`** — held back pending an artwork fix. Remove from `EXCLUDED` in `copy_bank.py` once resolved.
- **`glt-print-girl-dinner-combo`** — a colourway duplicate of another listing. Re-add once the two listings are merged.
- **The three invite templates** are excluded from *scene* work only. They're Canva files, not objects — cutting one out yields a floating cocktail glass. They still appear as tiles.

---

## Palette

Sampled from the products themselves.

Marg Orange `#F0780C` · Girl Dinner Green `#6EC83C` · Butter Cream `#F7EEDC` · Deep Olive `#2F6B33` · Berry `#A6325C` · Hot Pink `#CC489C` · Espresso Ink `#2A211B`

Type is Poppins Bold for display, Lora Italic for accents, Poppins for body. Nothing else.
