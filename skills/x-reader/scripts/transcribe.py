#!/usr/bin/env python3
"""Transcribe el audio de los videos con whisper.cpp (large-v3-turbo).
Sólo procesa los que tienen audio — muchos videos de UI son mudos.
Uso: ./transcribe.py [--model ruta] [--force]"""
import json, os, re, subprocess, sys, glob

HERE  = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.expanduser("~/tools/ggml-large-v3-turbo.bin")
if "--model" in sys.argv: MODEL = sys.argv[sys.argv.index("--model")+1]
FORCE = "--force" in sys.argv

def main():
    if not os.path.exists(MODEL):
        print(f"falta el modelo: {MODEL}"); return
    # Metal: sin esto whisper.cpp corre mucho más lento en Apple Silicon
    env = dict(os.environ)
    try:
        pref = subprocess.run(["brew","--prefix","whisper-cpp"],capture_output=True,text=True).stdout.strip()
        if pref: env["GGML_METAL_PATH_RESOURCES"] = os.path.join(pref,"share","whisper-cpp")
    except Exception: pass

    vj = os.path.join(HERE,"videos.jsonl")
    if not os.path.exists(vj):
        print(f"No existe {vj}.\nCorré primero:  ./video.py"); return
    rows = [json.loads(l) for l in open(vj,encoding="utf-8") if l.strip()]
    todo = [r for r in rows if r.get("audio_file") and os.path.exists(r["audio_file"])]
    print(f"{len(rows)} videos · {len(todo)} con audio (el resto son mudos, sólo frames)")

    os.makedirs(os.path.join(HERE,"transcripts"), exist_ok=True)
    out = []
    for i, r in enumerate(todo, 1):
        tag = f"{r['author']}-{r['id']}"
        dst = os.path.join(HERE,"transcripts",tag)
        txt = dst + ".txt"
        if os.path.exists(txt) and not FORCE:
            print(f"  · {tag} (ya estaba)")
        else:
            # sin --language: dejar autodetección (es+en mezclados)
            p = subprocess.run(["whisper-cli","-m",MODEL,"-f",r["audio_file"],
                                "-otxt","-of",dst,"--no-prints"],
                               capture_output=True,text=True,env=env,timeout=1800)
            if not os.path.exists(txt):
                print(f"  ✗ {tag}: {p.stderr.strip()[:80]}"); continue
            print(f"  ✓ {tag}")
        content = open(txt,encoding="utf-8").read().strip()
        # Whisper alucina "*music*" / "Thank you." cuando NO hay habla (sólo música o
        # silencio). Marcarlo para no confundirlo con contenido real.
        words = content.split()
        clean = re.sub(r"[*\[\]()]|thank you\.?|music|you|applause|subtitles?|amara\.org",
                       "", content, flags=re.I).strip()
        has_speech = len(words) > 12 and len(clean) > 25
        out.append({**r, "transcript_file": txt, "transcript": content,
                    "has_speech": has_speech,
                    "transcript_note": None if has_speech else "sin habla (música/silencio)"})

    with open(os.path.join(HERE,"transcripts.jsonl"),"w",encoding="utf-8") as f:
        for o in out: f.write(json.dumps(o,ensure_ascii=False)+"\n")
    real = [o for o in out if o.get("has_speech")]
    words = sum(len(o["transcript"].split()) for o in real)
    print(f"✓ {len(out)} procesados · {len(real)} con habla real · {words:,} palabras → transcripts.jsonl")
    if len(out) != len(real):
        print(f"  ({len(out)-len(real)} eran música/silencio — Whisper devuelve '*music*' o 'Thank you.' ahí)")

if __name__ == "__main__":
    main()
