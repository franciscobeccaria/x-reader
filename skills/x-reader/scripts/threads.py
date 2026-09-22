#!/usr/bin/env python3
"""Abre cada bookmark en el browser y extrae el hilo DEL AUTOR (root + continuaciones).
Uso: ./threads.py [--in bookmarks-week.jsonl] [--out threads.jsonl] [--only-with-replies]"""
import json, subprocess, sys, time, os

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = ["npx", "agent-browser", "--session", "xreal"]
JS = open(os.path.join(HERE, "thread.js"), encoding="utf-8").read()

def run(args, timeout=90):
    try:
        return subprocess.run(SESSION+args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except subprocess.TimeoutExpired:
        return ""

def unwrap(raw):
    raw = (raw or "").strip()
    if not raw: return None
    line = raw.splitlines()[-1].strip()
    try:
        v = json.loads(line)
        if isinstance(v, str): v = json.loads(v)
        return v if isinstance(v, dict) else None
    except Exception:
        return None

def main():
    inp = os.path.join(HERE, "bookmarks-week.jsonl")
    out = os.path.join(HERE, "threads.jsonl")
    if "--in"  in sys.argv: inp = sys.argv[sys.argv.index("--in")+1]
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out")+1]

    if not os.path.exists(inp):
        print(f"No existe {inp}.\nCorré primero:  ./run.sh 60   (y después ./enrich.py)")
        return
    rows = [json.loads(l) for l in open(inp, encoding="utf-8") if l.strip()]
    if "--only-with-replies" in sys.argv:
        rows = [r for r in rows if r.get("replies", 0) > 0]
    print(f"a procesar: {len(rows)}")

    results, found = [], 0
    for i, r in enumerate(rows, 1):
        run(["open", r["url"]])
        d = None
        for _ in range(6):
            time.sleep(1.5)
            d = unwrap(run(["eval", JS]))
            if d and d.get("count", 0) > 0: break
        if not d:
            results.append({**r, "thread_error": "no cargó"}); continue

        posts = d.get("posts", [])
        # el hilo del autor: root + posts del mismo autor que NO son replies de terceros
        chain = [p for p in posts if p.get("is_root") or p.get("is_author_self_thread")]
        chain.sort(key=lambda p: p.get("pos", 0))
        # dedupe: X a veces renderiza el mismo post dos veces (mismo id, o mismo texto)
        seen_ids, seen_txt, dedup = set(), set(), []
        for p in chain:
            key_id, key_tx = p.get("id"), (p.get("text") or "").strip()[:120]
            if key_id and key_id in seen_ids: continue
            if key_tx and key_tx in seen_txt: continue
            if key_id: seen_ids.add(key_id)
            if key_tx: seen_txt.add(key_tx)
            dedup.append(p)
        chain = dedup
        root_id = d.get("root")
        extra = [p for p in chain if p.get("id") != root_id]
        if extra: found += 1

        rec = {**r,
               "thread_len": len(chain),
               "thread_posts": extra,          # sólo las continuaciones
               "replies_visible": sum(1 for p in posts if not p.get("is_root") and not p.get("is_author_self_thread"))}
        # texto completo del hilo concatenado, útil para búsqueda
        if extra:
            rec["thread_text"] = " ⏎ ".join([p["text"] for p in chain if p.get("text")])
            links = []
            for p in chain: links += p.get("images", [])
            if links: rec["thread_images"] = list(dict.fromkeys(links))
        results.append(rec)

        if i % 10 == 0: print(f"  {i}/{len(rows)}  (con hilo: {found})")

    with open(out, "w", encoding="utf-8") as f:
        for r in results: f.write(json.dumps(r, ensure_ascii=False)+"\n")
    print(f"✓ {len(results)} procesados · {found} tienen hilo del autor → {out}")

if __name__ == "__main__":
    main()
