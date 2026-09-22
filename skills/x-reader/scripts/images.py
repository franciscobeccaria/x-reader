#!/usr/bin/env python3
"""Descarga las imágenes de los bookmarks (no thumbnails de video).
Uso: ./images.py [--in bookmarks-week.jsonl] [--size medium|large|orig]"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "images")

def main():
    inp = os.path.join(HERE, "bookmarks-week.jsonl")
    if "--in" in sys.argv: inp = sys.argv[sys.argv.index("--in")+1]
    size = sys.argv[sys.argv.index("--size")+1] if "--size" in sys.argv else "medium"

    if not os.path.exists(inp):
        print(f"No existe {inp}.\nCorré primero:  ./run.sh 60   (y después ./enrich.py)")
        return
    rows = [json.loads(l) for l in open(inp, encoding="utf-8") if l.strip()]
    os.makedirs(OUT, exist_ok=True)
    todo = [(r, u) for r in rows for u in (r.get("images") or [])]
    print(f"imágenes a bajar: {len(todo)} (de {sum(1 for r in rows if r.get('images'))} bookmarks)")

    ok = fail = 0
    manifest = []
    for r, u in todo:
        # pedir la resolución deseada al CDN de X
        base = u.split("?")[0]
        url = f"{base}?format=jpg&name={size}" if "pbs.twimg.com" in base else u
        idx = (r.get("images") or []).index(u)
        dst = os.path.join(OUT, f"{r['author']}-{r['id']}-{idx}.jpg")
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            ok += 1; manifest.append({**{k:r[k] for k in ('id','author','url','text')}, "file": dst}); continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=25).read()
            if len(data) < 500: raise ValueError("respuesta muy chica")
            open(dst, "wb").write(data)
            ok += 1
            manifest.append({**{k:r[k] for k in ('id','author','url','text')}, "file": dst})
        except Exception as e:
            fail += 1
            print(f"  ✗ {r['author']}-{r['id']}: {type(e).__name__}")
    with open(os.path.join(HERE,"images.jsonl"),"w",encoding="utf-8") as f:
        for m in manifest: f.write(json.dumps(m,ensure_ascii=False)+"\n")
    print(f"✓ {ok} descargadas, {fail} fallaron → images/ (manifiesto: images.jsonl)")

if __name__ == "__main__":
    main()
