import json, os, re, urllib.request, urllib.error

BASE = "/root/girls-love-things"
ASSETS = os.path.join(BASE, "assets")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}

cat = json.load(open(os.path.join(BASE, "catalogue.json")))

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

report = []
for p in cat["products"]:
    folder = os.path.join(ASSETS, p["sku"])
    os.makedirs(folder, exist_ok=True)
    got = 0
    for i, url in enumerate(p["images"], 1):
        # try to upgrade to Etsy's original full-resolution variant
        full = re.sub(r"il_\d+x[N\d]+\.", "il_fullxfull.", url)
        data = None
        used = None
        for candidate in ([full, url] if full != url else [url]):
            try:
                data = fetch(candidate)
                used = candidate
                break
            except Exception:
                continue
        if data is None:
            report.append((p["sku"], i, "FAILED", url))
            continue
        name = f"{p['sku']}-{i:02d}.jpg"
        with open(os.path.join(folder, name), "wb") as f:
            f.write(data)
        got += 1
        report.append((p["sku"], i, f"{len(data)//1024}KB", used.split('/')[-1]))
    print(f"{p['sku']}: {got}/{len(p['images'])}")

fails = [r for r in report if r[2] == "FAILED"]
print("\nTOTAL FILES:", sum(1 for r in report if r[2] != "FAILED"))
print("FAILURES:", len(fails))
for f in fails:
    print("  ", f)
