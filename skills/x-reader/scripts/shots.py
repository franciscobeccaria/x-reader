#!/usr/bin/env python3
"""Captura el tweet principal de cada URL como PNG recortado al <article>.

agent-browser NO tiene screenshot por selector: capturamos la página entera y
recortamos con sips usando getBoundingClientRect() * devicePixelRatio.

Uso:  ./shots.py urls.txt [dir_salida]
      urls.txt = una por linea, formato  <url>  <nombre-archivo>
Env:  X_SESSION (default "x")
"""
import json, subprocess, time, os, sys

S = ["npx", "agent-browser", "--session", os.environ.get("X_SESSION", "x")]

def run(a, t=180):
    try:
        return subprocess.run(S + a, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception:
        return ""

def unwrap(r):
    r = (r or "").strip()
    if not r:
        return None
    try:
        v = json.loads(r.splitlines()[-1])
        return json.loads(v) if isinstance(v, str) else v
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath("shots")
    os.makedirs(out, exist_ok=True)
    targets = []
    for line in open(sys.argv[1], encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        url = parts[0]
        name = parts[1] if len(parts) > 1 else url.rstrip("/").split("/")[-1]
        targets.append((url, name))

    run(["set", "viewport", "1000", "1400"])
    for url, name in targets:
        run(["open", url])
        box = None
        for _ in range(10):
            time.sleep(1.6)
            box = unwrap(run(["eval", '''(()=>{const a=document.querySelector("article");if(!a)return null;
              document.querySelectorAll("[data-testid=sidebarColumn],header[role=banner]").forEach(e=>e.style.display="none");
              window.scrollTo(0,0);
              const r=a.getBoundingClientRect();
              return JSON.stringify({x:Math.max(0,r.x|0),y:Math.max(0,r.y|0),w:r.width|0,h:r.height|0,dpr:window.devicePixelRatio});})()''']))
            if box and box.get("w", 0) > 200:
                break
        if not box:
            print(f"  x  {name} (no cargó)")
            continue
        tmp = f"/tmp/_shot_{name}.png"
        run(["screenshot", tmp], 240)
        if not os.path.exists(tmp):
            print(f"  x  {name} (sin screenshot)")
            continue
        d = box.get("dpr") or 1
        x, y, w, h = [int(box[k] * d) for k in ("x", "y", "w", "h")]
        dst = os.path.join(out, f"{name}.png")
        subprocess.run(["sips", "-c", str(h), str(w), "--cropOffset", str(y), str(x),
                        tmp, "--out", dst], capture_output=True, text=True)
        print((f"  ok {name}  {w}x{h}") if os.path.exists(dst) else f"  x  {name}")
        os.remove(tmp)

if __name__ == "__main__":
    main()
