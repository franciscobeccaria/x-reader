#!/usr/bin/env python3
"""Enriquece bookmarks visitando cada tweet: métricas, media, hilo.
Uso: ./enrich.py [desde_fecha] [--in archivo] [--out archivo]"""
import json, subprocess, sys, time, os

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = ["npx", "agent-browser", "--session", os.environ.get("X_SESSION", "x")]
JS = open(os.path.join(HERE, "enrich.js"), encoding="utf-8").read()

def run(args, timeout=90):
    try:
        r = subprocess.run(SESSION + args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""

def unwrap(raw):
    raw = raw.strip()
    if not raw: return None
    line = raw.splitlines()[-1].strip()
    try:
        v = json.loads(line)
        if isinstance(v, str): v = json.loads(v)
        return v if isinstance(v, dict) else None
    except Exception:
        return None

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    frm = args[0] if args else "ALL"   # YYYY-MM-DD, o ALL para todo
    inp = os.path.join(HERE, "bookmarks.jsonl")
    out = os.path.join(HERE, "bookmarks-week.jsonl")
    if "--in" in sys.argv:  inp = sys.argv[sys.argv.index("--in")+1]
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out")+1]

    if not os.path.exists(inp):
        print(f"No existe {inp}.\nCorré primero:  ./run.sh 60   (y después ./enrich.py)")
        return
    rows = [json.loads(l) for l in open(inp, encoding="utf-8") if l.strip()]
    todo = [r for r in rows if r.get("date","") >= frm] if frm != "ALL" else rows
    print(f"a enriquecer: {len(todo)}")

    done = []
    for i, r in enumerate(todo, 1):
        run(["open", r["url"]])
        got = None
        for _ in range(6):
            time.sleep(1.5)
            v = unwrap(run(["eval", JS]))
            if v and "error" not in v:
                got = v; break
        if got:
            ft = got.pop("full_text", None)
            if ft: got["text"] = ft
            r = {**r, **got}
        else:
            r = {**r, "enrich_error": "no article"}
        done.append(r)
        if i % 10 == 0:
            ok = sum(1 for x in done if "likes" in x)
            print(f"  {i}/{len(todo)}  (ok: {ok})")

    with open(out, "w", encoding="utf-8") as f:
        for r in done: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = sum(1 for r in done if "likes" in r)
    print(f"✓ {len(done)} procesados, {ok} con métricas → {out}")

if __name__ == "__main__":
    main()
