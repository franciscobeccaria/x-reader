(() => {
  const a = document.querySelector('article');
  if (!a) return JSON.stringify({error: 'no article'});
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
  const grp = a.querySelector('[role="group"]');
  const gl = grp ? (grp.getAttribute('aria-label')||'') : '';
  const pick = (words) => {
    for (const w of words) {
      const m = gl.match(new RegExp('([\\d.,]+(?:\\s*[KMkm])?)\\s+' + w, 'i'));
      if (m) return parseNum(m[1].replace(/\s+/g,''));
    }
    return 0;
  };
  // imágenes: varias rutas porque X cambia el markup y a veces sirve sin <img>
  const photoUrls = new Set();
  // 1) el contenedor oficial de foto
  a.querySelectorAll('[data-testid="tweetPhoto"] img').forEach(i => i.src && photoUrls.add(i.src));
  // 2) cualquier img del CDN de media (excluye avatares y emojis)
  a.querySelectorAll('img').forEach(i => {
    const s = i.src || '';
    if (/pbs\.twimg\.com\/(media|amplify_video_thumb|ext_tw_video_thumb|tweet_video_thumb)\//.test(s)
        && !s.includes('profile_images') && !s.includes('emoji')) photoUrls.add(s);
  });
  // 3) background-image en divs (X lo usa en algunos layouts)
  a.querySelectorAll('[style*="background-image"]').forEach(d => {
    const m = (d.getAttribute('style')||'').match(/url\(["']?(https:[^"')]+)["']?\)/);
    if (m && m[1].includes('pbs.twimg.com') && !m[1].includes('profile_images')) photoUrls.add(m[1]);
  });
  // 4) <source srcset> dentro de <picture>
  a.querySelectorAll('source[srcset]').forEach(s => {
    const u = (s.getAttribute('srcset')||'').split(' ')[0];
    if (u && u.includes('pbs.twimg.com') && !u.includes('profile_images')) photoUrls.add(u);
  });
  // separar foto real de thumbnail de video
  const isThumb = (u) => /video_thumb/.test(u);
  const photos = [...photoUrls].filter(u => !isThumb(u));
  const videoThumbs = [...photoUrls].filter(isThumb);

  const card = a.querySelector('[data-testid="card.wrapper"] a[href^="http"]');
  const links = [...a.querySelectorAll('a[href^="http"]')].map(l=>l.href)
    .filter(h => !h.includes('/status/') && !h.includes('/hashtag/') && !h.includes('/i/'));
  // respuestas visibles en la página del tweet (el hilo)
  const arts = document.querySelectorAll('article');
  return JSON.stringify({
    likes: pick(['Me gusta','likes?']),
    reposts: pick(['reposts?','retweets?']),
    replies: pick(['respuestas?','replies','reply']),
    bookmarks_count: pick(['elementos guardados','bookmarks?']),
    views: pick(['reproducciones','views','visualizaciones']),
    images: photos,
    video_thumbs: videoThumbs,
    has_video: !!a.querySelector('[data-testid="videoPlayer"], [data-testid="videoComponent"], video'),
    card_url: card ? card.href : null,
    links: [...new Set(links)].slice(0,5),
    thread_size: arts.length,
    full_text: (a.querySelector('[data-testid="tweetText"]')||{innerText:''}).innerText.replace(/\s+/g,' ').trim()
  });
})()
