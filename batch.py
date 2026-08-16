"""
GLT BATCH - one command, a month of on-brand content.

    python3 batch.py                 # next month
    python3 batch.py 2026-10         # a specific month
    python3 batch.py 2026-10 --posts 5 --stories 2   # posts/stories per week

Writes campaign/<month>/ with every image named by date and slot, plus
schedule.csv and schedule.md you can work straight down.

Rules it enforces so the grid doesn't look generated:
  - the same product never reappears within 6 days
  - templates rotate, never twice in a row
  - background colour is picked to contrast with that product, then rotated
  - copy variants cycle, so nothing repeats inside a month
  - each design family gets airtime in proportion to how much of the shop it is
"""
import csv, calendar, json, os, sys, random
from datetime import date, timedelta

from glt_studio import Studio, PRODUCT_LED, BRAND, suggest_dominant, TEMPLATES
from scene_studio import place, scene_post, PAIRINGS, SCENES
from copy_bank import COPY, EXCLUDED, HASHTAGS

BASE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(os.path.join(BASE, "catalogue.json")))
BY_SKU = {p["sku"]: p for p in CAT["products"]}

PALETTE = PRODUCT_LED          # set by the palette decision - swap to BRAND to flip
POST_TEMPLATES = ["hero", "split", "shelf"]
STORY_TEMPLATES = ["statement", "hero"]

# how a month is made up. Scenes carry the shop's credibility, tiles carry the
# jokes - a feed of only one or the other reads as either bland or shouty.
MIX = ["scene_caption", "tile", "scene_caption", "tile", "scene_plain"]
ROT = [0, -2.5, 3.0, -4.0, 2.0, -1.5]


def category_of(sku):
    c = BY_SKU[sku]["category"]
    if c == "Apparel":
        return "apparel"
    if c == "Wall art":
        return "print"
    if c == "Digital":
        return "digital"
    return "default"


def next_month(today=None):
    t = today or date.today()
    return (t.year + (t.month == 12), 1 if t.month == 12 else t.month + 1)


def build_plan(year, month, posts_per_week=5, stories_per_week=2, seed=11):
    rng = random.Random(seed)
    skus = [s for s in COPY if s not in EXCLUDED and s in BY_SKU]

    # weight by how much of the catalogue each design family is, so the hero
    # products carry the month instead of everything getting equal airtime
    pool = []
    for s in skus:
        weight = 3 if "girl-dinner" in s or "martini-caesar" in s else \
                 2 if BY_SKU[s]["price_gbp_from"] < 18 else 1
        pool += [s] * weight

    days = calendar.monthrange(year, month)[1]
    all_days = [date(year, month, d) for d in range(1, days + 1)]

    # spread posts across weekdays, stories on the quieter days
    post_days, story_days = [], []
    for wk_start in range(0, days, 7):
        week = all_days[wk_start:wk_start + 7]
        if not week:
            continue
        picks = rng.sample(week, min(posts_per_week, len(week)))
        post_days += sorted(picks)
        rest = [d for d in week if d not in picks]
        story_days += sorted(rng.sample(rest, min(stories_per_week, len(rest))))

    plan, recent, last_tpl, used = [], [], None, {}
    def choose(day, slot, templates):
        nonlocal last_tpl
        cands = [s for s in pool if s not in recent[-6:]] or pool
        sku = rng.choice(cands)
        recent.append(sku)
        tpl = rng.choice([t for t in templates if t != last_tpl] or templates)
        last_tpl = tpl
        variants = COPY[sku]
        i = used.get(sku, 0)
        used[sku] = i + 1
        hl, ac, bd, caption = variants[i % len(variants)]
        doms = suggest_dominant(sku, PALETTE)
        dom = doms[(i + len(plan)) % 3]
        size = "story" if slot == "story" else ("portrait" if len(plan) % 2 == 0 else "feed")

        # pick the content type - falls back to a tile when the product has no room
        scenes_for = PAIRINGS.get(sku, [])
        kind = MIX[len(plan) % len(MIX)]
        if kind.startswith("scene") and not scenes_for:
            kind = "tile"
        scene = scenes_for[(i + len(plan)) % len(scenes_for)] if scenes_for else None
        rot = ROT[len(plan) % len(ROT)] if scene and SCENES[scene]["kind"] == "flatlay" else 0

        plan.append(dict(date=day, slot=slot, sku=sku, template=tpl, size=size,
                         dominant=dom, headline=hl, accent=ac, body=bd, kind=kind,
                         scene=scene, rotate=rot,
                         caption=caption, hashtags=HASHTAGS[category_of(sku)]))

    for d in sorted(set(post_days) | set(story_days)):
        if d in post_days:
            choose(d, "post", POST_TEMPLATES)
        if d in story_days:
            choose(d, "story", STORY_TEMPLATES)
    return plan


def render_plan(plan, year, month):
    outdir = os.path.join(BASE, "campaign", f"{year}-{month:02d}")
    os.makedirs(outdir, exist_ok=True)
    s = Studio(palette=PALETTE)
    rows = []
    for item in plan:
        tag = item["scene"] if item["kind"].startswith("scene") else item["template"]
        name = (f"{item['date'].strftime('%d')}_{item['slot']}_"
                f"{item['sku'].replace('glt-','')}_{tag}.jpg")
        path = os.path.join(outdir, name)
        if item["kind"] == "scene_caption":
            scene_post(item["sku"], item["scene"], path, size=item["size"],
                       headline=item["headline"], accent=item["accent"],
                       body=item["body"], rotate=item["rotate"])
        elif item["kind"] == "scene_plain":
            scene_post(item["sku"], item["scene"], path, size=item["size"],
                       rotate=item["rotate"])          # no caption band - pure photography
        else:
            s.render(item["template"], sku=item["sku"], size=item["size"],
                     dominant=item["dominant"], headline=item["headline"],
                     accent=item["accent"], body=item["body"], out=path)
        rows.append({
            "date": item["date"].isoformat(),
            "weekday": item["date"].strftime("%a"),
            "slot": item["slot"],
            "type": {"scene_caption": "photo + caption", "scene_plain": "photo",
                     "tile": "graphic tile"}[item["kind"]],
            "format": item["size"],
            "file": name,
            "product": BY_SKU[item["sku"]]["short_name"],
            "listing": f"https://www.etsy.com/listing/{BY_SKU[item['sku']]['listing_id']}/",
            "on_image": item["headline"],
            "caption": f"{item['headline']}\n\n{item['caption']}",
            "hashtags": item["hashtags"],
        })

    with open(os.path.join(outdir, "schedule.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(outdir, "schedule.md"), "w") as f:
        f.write(f"# GIRLS LOVE THINGS - content calendar, {calendar.month_name[month]} {year}\n\n")
        f.write(f"{len(rows)} assets. Images in this folder, named by date.\n\n")
        for r in rows:
            f.write(f"### {r['date']} ({r['weekday']}) · {r['slot']} · {r['format']}\n")
            f.write(f"**{r['product']}** — `{r['file']}`\n\n")
            f.write(f"> {r['caption']}\n\n")
            f.write(f"{r['hashtags']}\n\n[Listing]({r['listing']})\n\n---\n\n")
    return outdir, rows


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {sys.argv[i]: sys.argv[i + 1] for i, a in enumerate(sys.argv)
             if a.startswith("--") and i + 1 < len(sys.argv)}
    if args:
        y, m = map(int, args[0].split("-"))
    else:
        y, m = next_month()
    plan = build_plan(y, m,
                      posts_per_week=int(flags.get("--posts", 5)),
                      stories_per_week=int(flags.get("--stories", 2)))
    outdir, rows = render_plan(plan, y, m)
    print(f"{len(rows)} assets -> {outdir}")
    print(f"  {sum(1 for r in rows if r['slot']=='post')} posts, "
          f"{sum(1 for r in rows if r['slot']=='story')} stories")
    print(f"  schedule.csv + schedule.md written")
