#!/usr/bin/env python3
"""Busca en los bookmarks scrapeados.  Uso: ./search.py agent browser"""
import json,re,sys,os
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'bookmarks.jsonl')
if not os.path.exists(p):
    print(f"No hay {p}.\nCorré primero:  ./run.sh 60"); sys.exit(1)
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
if len(sys.argv)<2:
    print(f"{len(rows)} bookmarks. Uso: ./search.py <término> [término…]"); sys.exit()
pat=re.compile('|'.join(re.escape(t) for t in sys.argv[1:]),re.I)
hits=[r for r in rows if pat.search(r['text']) or pat.search(r['author'])]
print(f"{len(hits)} de {len(rows)}\n")
for r in hits:
    print(f"@{r['author']}  {(r.get('date') or '')[:10]}")
    print(f"  {r['text'][:160]}")
    print(f"  {r['url']}\n")
