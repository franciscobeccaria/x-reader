#!/usr/bin/env python3
"""Descarga videos de bookmarks y extrae frames para analizarlos.
Uso: ./video.py [--in bookmarks-week.jsonl] [--limit N] [--every 3]
Los frames quedan en frames/<autor>-<id>/ listos para leer."""
import json, subprocess, sys, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
# preferir el yt-dlp de brew (se actualiza con `brew upgrade yt-dlp`, el primer paso
# cuando X rompe el extractor); caer al venv si no está
import shutil
YTDLP = shutil.which("yt-dlp") or os.path.join(HERE, ".venv/bin/yt-dlp")
COOKIES = os.path.join(HERE, ".x-cookies.txt")
SESSION = os.environ.get("X_SESSION", "xreal")
MAX_FRAMES = int(os.environ.get("X_MAX_FRAMES", "120"))
PORT = os.environ.get("BOT_BROWSER_PORT", "9333")
# Por defecto, sin cookies: el navegador del bot abre el tweet y el reproductor
# pide la playlist pública (.m3u8) a video.twimg.com; ffmpeg la baja directo.
# X_USE_BOT_BROWSER=0 vuelve al modo viejo (yt-dlp + cookies.txt exportado).
USE_BOT = os.environ.get("X_USE_BOT_BROWSER", "1") == "1" and shutil.which("bot-browser")
VID = os.path.join(HERE, "videos")
FRM = os.path.join(HERE, "frames")

def sh(args, timeout=300):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None

def ab(*args, timeout=60):
    r = sh(["agent-browser", "--session", SESSION, *args], timeout=timeout)
    return (r.stdout if r else "").strip()

def via_bot(r, out_mp4):
    """Abre el tweet en el navegador del bot y baja su video desde la playlist pública."""
    import re, time
    ab("network", "requests", "--clear")
    ab("open", r["url"])
    poster, master = "", None
    for _ in range(10):  # el reproductor tarda en pedir la playlist
        time.sleep(1.5)
        poster = ab("eval", '(()=>{const v=document.querySelector("article video");return v?v.poster:""})()').strip('"')
        m = re.search(r"(?:amplify_video_thumb|ext_tw_video_thumb|tweet_video_thumb)/(\d+)", poster)
        reqs = ab("network", "requests", "--filter", "video.twimg.com")
        urls = re.findall(r"GET (https://video\.twimg\.com/\S+\.m3u8\?\S*tag=\S*)", reqs)
        if m: urls = [u for u in urls if f"/{m.group(1)}/" in u]
        if urls: master = urls[0]; break
    if not master:
        mp4 = re.search(r"https://video\.twimg\.com/tweet_video/\S+\.mp4", poster + ab("network", "requests", "--filter", "tweet_video"))
        master = mp4.group(0) if mp4 else None  # GIFs de X son mp4 sueltos
    if not master: return False
    res = sh(["ffmpeg", "-loglevel", "error", "-y", "-i", master, "-c", "copy", out_mp4], timeout=600)
    return os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 0

def main():
    inp = os.path.join(HERE, "bookmarks-week.jsonl")
    if "--in" in sys.argv: inp = sys.argv[sys.argv.index("--in")+1]
    limit = int(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else None
    every = int(sys.argv[sys.argv.index("--every")+1]) if "--every" in sys.argv else 3

    if not os.path.exists(inp):
        print(f"No existe {inp}.\nCorré primero:  ./run.sh 60   (y después ./enrich.py)")
        return
    rows = [json.loads(l) for l in open(inp, encoding="utf-8") if l.strip()]
    vids = [r for r in rows if r.get("has_video")]
    if limit: vids = vids[:limit]
    print(f"videos a procesar: {len(vids)}")
    os.makedirs(VID, exist_ok=True); os.makedirs(FRM, exist_ok=True)
    if USE_BOT:
        sh(["bot-browser", "start"]); ab("connect", PORT)

    done = []
    for i, r in enumerate(vids, 1):
        tag = f"{r['author']}-{r['id']}"
        if USE_BOT:
            mp4 = os.path.join(VID, tag + ".mp4")
            files = [mp4] if (os.path.exists(mp4) or via_bot(r, mp4)) else []
            if not files: print(f"  ✗ {tag}: no encontré la playlist del video"); continue
        else:
          out = os.path.join(VID, tag + ".%(ext)s")
          # yt-dlp: sleeps para no gatillar el rate limit de X
          res = sh([YTDLP, "--cookies", COOKIES, "--no-warnings", "--quiet",
                    "--sleep-requests", "2", "-o", out, r["url"]])
          files = glob.glob(os.path.join(VID, tag + ".*"))
          files = [f for f in files if not f.endswith((".part", ".ytdl"))]
          if not files:
              # fallback: sin cookies (bug conocido de yt-dlp con X)
              sh([YTDLP, "--no-warnings", "--quiet", "-o", out, r["url"]])
              files = [f for f in glob.glob(os.path.join(VID, tag+".*"))
                       if not f.endswith((".part",".ytdl"))]
          if not files:
              print(f"  ✗ {tag}: no se pudo descargar"); continue

        mp4 = files[0]
        fdir = os.path.join(FRM, tag)
        os.makedirs(fdir, exist_ok=True)
        # videos largos: tope de MAX_FRAMES fotogramas (una charla de 50 min no
        # necesita 1000 imágenes; ahí manda la transcripción)
        dur = sh(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",mp4])
        try: dur = float(dur.stdout.strip())
        except Exception: dur = 0
        step = max(every, dur / MAX_FRAMES) if dur else every
        sh(["ffmpeg","-loglevel","error","-i",mp4,
            "-vf",f"fps=1/{step:.2f},scale=800:-1","-q:v","3",
            os.path.join(fdir,"f-%02d.jpg")])
        n = len(glob.glob(os.path.join(fdir,"*.jpg")))
        # audio para transcribir después
        wav = os.path.join(VID, tag+".wav")
        sh(["ffmpeg","-loglevel","error","-y","-i",mp4,"-ar","16000","-ac","1",
            "-c:a","pcm_s16le",wav])
        done.append({**r, "video_file": mp4, "frames_dir": fdir, "frames": n,
                     "audio_file": wav if os.path.exists(wav) else None})
        print(f"  ✓ {tag}: {n} frames")

    with open(os.path.join(HERE,"videos.jsonl"),"w",encoding="utf-8") as f:
        for d in done: f.write(json.dumps(d,ensure_ascii=False)+"\n")
    print(f"✓ {len(done)}/{len(vids)} → videos.jsonl")

if __name__ == "__main__":
    main()
