#!/bin/bash
# Scrapea los bookmarks ("Guardados") de X con agent-browser sobre una COPIA
# del perfil de Chrome — el perfil por defecto bloquea el puerto de debug.
# Uso: ./run.sh [n_scrolls]   (default 60)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
COPY="$HERE/.chrome-copy"
SRC="$HOME/Library/Application Support/Google/Chrome"
PROFILE="${X_CHROME_PROFILE:-Default}"   # el perfil de Chrome donde tenés la sesión de X
                                         # (X_CHROME_PROFILE="Profile 1" para el segundo perfil)

if ! curl -s --max-time 2 http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
  echo "→ copiando sesión del perfil…"
  rm -rf "$COPY"; mkdir -p "$COPY/Default"
  cp "$SRC/Local State" "$COPY/Local State" 2>/dev/null || true
  for f in Cookies "Login Data" "Web Data" Preferences "Secure Preferences" "Network Persistent State"; do
    cp "$SRC/$PROFILE/$f" "$COPY/Default/$f" 2>/dev/null || true
  done
  for d in Network "Local Storage" "Session Storage" IndexedDB; do
    cp -R "$SRC/$PROFILE/$d" "$COPY/Default/$d" 2>/dev/null || true
  done
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --remote-debugging-port=9222 --user-data-dir="$COPY" \
    --profile-directory="Default" --no-first-run --no-default-browser-check \
    > /dev/null 2>&1 &
  sleep 8
fi

S="npx agent-browser --session xreal"
$S connect 9222 > /dev/null
$S open "https://x.com/i/bookmarks" > /dev/null
sleep 4

OUT="$HERE/bookmarks.jsonl"; : > "$OUT"
EXTRACT=$(cat "$HERE/extract.js")
stale=0; LAST=""
for i in $(seq 1 "${1:-60}"); do
  $S eval "$EXTRACT" 2>/dev/null | tail -1 | python3 -c "
import sys,json
raw=sys.stdin.read().strip()
try:
    s=json.loads(raw) if raw.startswith('\"') else raw
    for t in json.loads(s if isinstance(s,str) else raw): print(json.dumps(t,ensure_ascii=False))
except Exception: pass" >> "$OUT"
  python3 - "$OUT" <<'PY'
import json,sys
p=sys.argv[1]; seen=set(); rows=[]
for line in open(p,encoding='utf-8'):
    line=line.strip()
    if not line: continue
    try: o=json.loads(line)
    except: continue
    if o['id'] in seen: continue
    seen.add(o['id']); rows.append(o)
open(p,'w',encoding='utf-8').write(''.join(json.dumps(o,ensure_ascii=False)+'\n' for o in rows))
PY
  n=$(wc -l < "$OUT" | tr -d ' ')
  echo "scroll $i → $n únicos"
  [ "$n" = "$LAST" ] && stale=$((stale+1)) || stale=0
  LAST=$n
  [ $stale -ge 4 ] && { echo "(fin)"; break; }
  $S eval 'window.scrollTo(0, document.body.scrollHeight); "ok"' > /dev/null 2>&1; sleep 3
done
echo "TOTAL: $(wc -l < "$OUT" | tr -d ' ') → $OUT"
