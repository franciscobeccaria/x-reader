# x-reader

Una skill para leer tus propios bookmarks de X con un agente, usando tu sesión
real de Chrome.

X no tiene API de bookmarks. La vía es un Chrome real manejado por CDP sobre
una copia de tu perfil, porque Chrome se niega a abrir el puerto de debug sobre
el perfil de usuario. Eso, más la extracción que convierte una lista scrapeada
en algo que podés buscar: métricas, imágenes, frames de video, transcripciones
y hilos del autor.

## Instalar

```bash
git clone git@github.com:franciscobeccaria/x-reader.git
cp -r x-reader/skills/x-reader ~/.claude/skills/
```

O como plugin, apuntando tu marketplace a este repo.

## Usar

Pedíselo al agente en lenguaje natural: "leé mis bookmarks de X",
"qué guardé esta semana", "buscá en mis bookmarks lo de browser agents".

Los scripts también corren solos:

```bash
cd ~/.claude/skills/x-reader/scripts
./run.sh 60                    # scrapea la lista
./enrich.py 2026-09-14         # métricas y media por tweet
./video.py                     # videos y frames
./search.py agent browser      # buscar
```

`SKILL.md` tiene el flujo completo y las trampas; `references/pipeline.md` el
detalle técnico.

## Requisitos

- macOS con Chrome
- `npm i -g agent-browser && agent-browser install`
- `brew install yt-dlp ffmpeg` (video), `brew install whisper-cpp` (audio)

## Cuidado

Esto maneja un navegador con tu sesión activa. La copia del perfil y el
`cookies.txt` llevan credenciales reales, y el puerto 9222 le da control total
del browser a cualquier proceso local. Al terminar:

```bash
pkill -f "chrome-copy"; rm -f .x-cookies.txt
```

El `.gitignore` excluye credenciales y datos scrapeados. No los commitees.
