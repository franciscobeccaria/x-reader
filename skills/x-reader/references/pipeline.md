# Pipeline reference

Every bug below cost real debugging time. Read the relevant section before
changing a script, or you will rediscover it.

## Setup

```bash
npm i -g agent-browser && agent-browser install   # the browser driver
brew install yt-dlp ffmpeg                        # video
brew install whisper-cpp                          # transcription (optional)
```

The whisper binary is called **`whisper-cli`**, not `whisper-cpp`. Brew does
not download models; get one separately:

```bash
mkdir -p ~/tools && curl -L -o ~/tools/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

`large-v3-turbo` (1.5 GB) is the right size for mixed Spanish and English.
Export `GGML_METAL_PATH_RESOURCES` before running or it falls back to a much
slower path on Apple Silicon — `transcribe.py` sets it for you.

If the system Python is externally managed (PEP 668), `pip install` fails.
Use a venv: `python3 -m venv .venv && .venv/bin/pip install yt-dlp`.

## Cookies for yt-dlp

`--cookies-from-browser chrome` does not work: Chrome 127+ ties the cookie
encryption key to the browser process. Export from the live session instead:

```bash
npx agent-browser --session x --json cookies get
```

**The `--json` flag is mandatory.** Without it the command prints plain
`name=value` text that cannot be parsed. Write the result as a Netscape
`cookies.txt` with LF line endings (CRLF causes HTTP 400), `chmod 600` it, and
pass it as `yt-dlp --cookies`.

Cookies expire in days to weeks. When yt-dlp starts failing, re-export before
debugging anything else. If the extractor breaks after an X change, run
`brew upgrade yt-dlp` first.

## Extraction bugs

**32 likes read as 32,000,000.** The like button's `aria-label` says "32 Me
gusta" and a regex looking for a K/M suffix takes the M of "Me" as millions.
Read the `[role="group"]` container's `aria-label` instead, which carries every
metric in one clean string:

```
"1 respuesta, 32 Me gusta, 12 elementos guardados, 5220 reproducciones"
```

Note those words are **locale-dependent**. The parser matches the Spanish set;
add English (`replies`, `likes`, `bookmarks`, `views`) if the UI renders in
another language.

**`scroll` does not move x.com.** Neither `agent-browser scroll down N` nor
`press End` changes `scrollY`. This works:

```bash
agent-browser eval 'window.scrollTo(0, document.body.scrollHeight)'
```

**X virtualizes the list.** The DOM never holds more than ~14 `<article>`
elements no matter how far you scroll. A naive scrape gets 14 of 219. You have
to accumulate and dedupe by tweet id while scrolling — `run.sh` does this.

**Bash mangles the JSON.** Enriching from a bash loop failed on 87% of tweets
even though the same `eval` worked fine standalone: interpolating the result
into a Python heredoc destroys the quoting. Rewritten with Python
`subprocess.run` (list args, no shell), it went from 9/70 to 70/70. Keep the
enricher in Python.

**Scene detection returns zero frames** on UI videos, because the transitions
are too soft for `select='gt(scene,0.25)'`. Use a fixed interval (`fps=1/3`).

**Enrichment degrades mid-run.** A long pass will start returning empty pages
somewhere after the 20th tweet. Two options: restart the tab every 20-30 pages,
or run the pass several times and merge by id, keeping the most complete
record:

```python
score = lambda r: ('likes' in r) * 10 + len(r.get('images') or []) * 5
```

Merging three partial runs produced 70/70 metrics and 28 photos — better than
any single run.

## Screenshots of a tweet

`agent-browser screenshot` has **no `--selector` flag**. Passing one creates a
file literally named `--selector`. To capture just the tweet, screenshot the
page and crop to the element's box:

```python
box = eval("document.querySelector('article').getBoundingClientRect()")
# multiply by window.devicePixelRatio, then:
sips -c <h> <w> --cropOffset <y> <x> page.png --out tweet.png
```

Hide `[data-testid=sidebarColumn]` and `header[role=banner]` first so the crop
holds only the post. `scripts/shots.py` does all of this; give it a file of
`<url> <name>` lines.

Note X may render the tweet **translated** into the viewer's language. If you
need the original wording, click "Mostrar original" / "Show original" before
capturing, or take the text from the JSONL instead.

## Data shape

`bookmarks.jsonl` — one object per bookmark:

```
id, author, url, date, text, order
```

After `enrich.py`, each gains:

```
likes, reposts, replies, bookmarks_count, views,
images[], video_thumbs[], has_video, card_url, links[], thread_size
```

**`date` is the tweet's publication date, not when you saved it.** X does not
expose the save date in the DOM. The only proxy is `order`, the position in the
list, since X sorts by save date descending.

`images` holds real photos and `video_thumbs` holds video posters — they were
one field originally and that made "18 bookmarks with images" mean "18 video
thumbnails and zero photos". Keep them apart.

## Threads

Opening a tweet's own page loads the replies without any extra work. The
extractor separates three kinds:

- `is_root` — the bookmarked tweet
- `is_author_self_thread` — the same author continuing (usually where the
  link or the payoff lives)
- `is_reply` — someone else

Following only the author's chain is normally enough; third-party replies
branch effectively without end. X sometimes renders the same post twice, so the
chain is deduped by id **and** by text.

## Useful metrics

Two derived numbers earned their place:

- **likes ÷ views** separates resonance from reach. A post with 5k views and
  4% engagement says more about your own taste than one with 2M views and 0.5%.
- **`bookmarks_count`** (how many *other* people saved it) is a good signal for
  "reference material" as opposed to entertainment.
