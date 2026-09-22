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
VID = os.path.join(HERE, "videos")
FRM = os.path.join(HERE, "frames")

def sh(args, timeout=300):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None

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

    done = []
    for i, r in enumerate(vids, 1):
        tag = f"{r['author']}-{r['id']}"
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
        sh(["ffmpeg","-loglevel","error","-i",mp4,
            "-vf",f"fps=1/{every},scale=800:-1","-q:v","3",
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
