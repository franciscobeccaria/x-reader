(() => {
  const parseNum = (s) => {
    if (!s) return 0;
    s = s.replace(/\./g,'').replace(/,/g,'.');
    const m = s.match(/^([\d.]+)\s*([KMkm])?$/);
    if (!m) return 0;
    let v = parseFloat(m[1]);
    if (m[2] && m[2].toLowerCase()==='k') v*=1000;
    if (m[2] && m[2].toLowerCase()==='m') v*=1000000;
    return Math.round(v);
  };
  const rootId = (location.pathname.match(/status\/(\d+)/)||[])[1];
  const rootAuthor = (location.pathname.match(/^\/([^\/]+)\/status/)||[])[1];
  const out = [];
  document.querySelectorAll('article').forEach((a, idx) => {
    const links = [...a.querySelectorAll('a[href*="/status/"]')];
    let id = null, author = null;
    for (const l of links) {
      const m = l.getAttribute('href').match(/^\/([^\/]+)\/status\/(\d+)/);
      if (m) { author = m[1]; id = m[2]; break; }
    }
    const txtEl = a.querySelector('[data-testid="tweetText"]');
    const time  = a.querySelector('time');
    const grp   = a.querySelector('[role="group"]');
    const gl    = grp ? (grp.getAttribute('aria-label')||'') : '';
    const pick = (words) => {
      for (const w of words) {
        const m = gl.match(new RegExp('([\\d.,]+(?:\\s*[KMkm])?)\\s+' + w, 'i'));
        if (m) return parseNum(m[1].replace(/\s+/g,''));
      }
      return 0;
    };
    const photos = [...a.querySelectorAll('[data-testid="tweetPhoto"] img, img[src*="/media/"]')]
      .map(i=>i.src).filter(s=>s && !s.includes('profile_images') && !s.includes('emoji'));
    // "Respondiendo a @x" indica que es reply
    const replyingTo = /respondiendo a|replying to/i.test(a.innerText.slice(0,200));
    out.push({
      pos: idx,
      id, author,
      is_root: id === rootId,
      is_author_self_thread: author === rootAuthor && id !== rootId,
      is_reply: replyingTo,
      date: time ? time.getAttribute('datetime') : null,
      text: txtEl ? txtEl.innerText.replace(/\s+/g,' ').trim() : '',
      images: [...new Set(photos)],
      has_video: !!a.querySelector('[data-testid="videoPlayer"], [data-testid="videoComponent"], video'),
      likes: pick(['Me gusta','likes?']),
      replies: pick(['respuestas?','replies','reply']),
      reposts: pick(['reposts?','retweets?']),
      views: pick(['reproducciones','views','visualizaciones'])
    });
  });
  return JSON.stringify({root: rootId, root_author: rootAuthor, count: out.length, posts: out});
})()
