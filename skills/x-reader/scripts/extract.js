(() => {
  const out = [];
  document.querySelectorAll('article').forEach((a, idx) => {
    const link = a.querySelector('a[href*="/status/"]');
    if (!link) return;
    const m = link.getAttribute('href').match(/\/([^\/]+)\/status\/(\d+)/);
    if (!m) return;
    const txt  = a.querySelector('[data-testid="tweetText"]');
    const time = a.querySelector('time');

    // imágenes (excluye avatares y emojis)
    const _u = new Set();
    a.querySelectorAll('[data-testid="tweetPhoto"] img, img').forEach(i => {
      const s = i.src || '';
      if (/pbs\.twimg\.com\/(media|amplify_video_thumb|ext_tw_video_thumb|tweet_video_thumb)\//.test(s)
          && !s.includes('profile_images') && !s.includes('emoji')) _u.add(s);
    });
    const photos = [..._u].filter(u => !/video_thumb/.test(u));

    // video / gif
    const video = !!a.querySelector('[data-testid="videoPlayer"], [data-testid="videoComponent"], video');
    const gif   = !!a.querySelector('[data-testid="placementTracking"] video');

    // card de link externo
    const card     = a.querySelector('[data-testid="card.wrapper"]');
    const cardLink = card ? card.querySelector('a[href^="http"]') : null;

    // links externos en el texto
    const links = [...a.querySelectorAll('a[href^="http"]')]
      .map(l => l.href)
      .filter(h => !h.includes('/status/') && !h.includes('/hashtag/') && !h.match(/x\.com\/[^\/]+$/));

    // métricas: el aria-label del [role=group] las trae todas juntas y limpias
    const parseNum = (s) => {
      if (!s) return 0;
      s = s.replace(/\./g, '').replace(/,/g, '.');
      const mm = s.match(/^([\d.]+)\s*([KMkm])?$/);
      if (!mm) return 0;
      let v = parseFloat(mm[1]);
      if (mm[2] && mm[2].toLowerCase() === 'k') v *= 1000;
      if (mm[2] && mm[2].toLowerCase() === 'm') v *= 1000000;
      return Math.round(v);
    };
    const grp = a.querySelector('[role="group"]');
    const gl = grp ? (grp.getAttribute('aria-label') || '') : '';
    const pick = (words) => {
      for (const w of words) {
        const re = new RegExp('([\\d.,]+(?:\\s*[KMkm])?)\\s+' + w, 'i');
        const mm = gl.match(re);
        if (mm) return parseNum(mm[1].replace(/\s+/g, ''));
      }
      return 0;
    };

    const socialCtx = a.querySelector('[data-testid="socialContext"]');

    out.push({
      order: idx,
      id: m[2],
      author: m[1],
      url: 'https://x.com/' + m[1] + '/status/' + m[2],
      date: time ? time.getAttribute('datetime') : null,
      text: txt ? txt.innerText.replace(/\s+/g,' ').trim().slice(0,600) : '',
      images: [...new Set(photos)],
      has_video: video || gif,
      card_url: cardLink ? cardLink.href : null,
      links: [...new Set(links)].slice(0,5),
      replies: pick(['respuestas?','replies','reply']),
      reposts: pick(['reposts?','retweets?']),
      likes: pick(['Me gusta','likes?']),
      bookmarks_count: pick(['elementos guardados','bookmarks?']),
      views: pick(['reproducciones','views']),
      is_thread: !!socialCtx || /mostrar más|show more|hilo|thread/i.test(a.innerText)
    });
  });
  return JSON.stringify(out);
})()
