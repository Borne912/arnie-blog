// 原始计数与历史基数分开保存；POST 只发送一次，失败后的补查均为只读 GET。
(() => {
  const script = document.currentScript;
  const endpoint = script.dataset.api;
  const storageKey = `stile:page-views:v1:${endpoint}`;
  const articles = new Map();
  const targets = [];
  const records = new Map();
  let stored = {};
  try {
    const value = JSON.parse(window.localStorage.getItem(storageKey));
    if (value && typeof value === 'object' && !Array.isArray(value)) stored = value;
  } catch { /* 隐私模式或存储不可用时，仍可使用本站快照。 */ }

  const validCount = (value) => Number.isSafeInteger(value) && value >= 0;
  const recordKey = (metric, url) => metric === 'site_pv' ? 'site' : `page:${url}`;
  const pause = (delay) => new Promise((resolve) => setTimeout(resolve, delay));

  function remember(key, value, at) {
    if (!validCount(value) || !Number.isFinite(at)) return;
    const previous = records.get(key);
    if (previous && (previous.value > value || (previous.value === value && previous.at >= at))) return;
    const record = { value, at };
    records.set(key, record);
    stored[key] = record;
  }

  function persist() {
    try { window.localStorage.setItem(storageKey, JSON.stringify(stored)); } catch { /* 缓存失败不影响显示。 */ }
  }

  function display(target, live = false) {
    const record = records.get(target.key);
    if (!live && target.live && record?.value === target.liveValue) return;
    const total = target.baseline + (record?.value ?? 0);
    const known = Number.isSafeInteger(total) && (record || target.baseline > 0);
    const value = target.element.querySelector(target.selector);
    const unit = target.element.querySelector('[data-views-unit]');
    if (!value) return;
    target.live = live;
    target.element.dataset.viewsState = known ? (live ? 'live' : 'cached') : 'unavailable';
    value.textContent = known ? `${live ? '' : '≥'}${total.toLocaleString('zh-CN')}` : (target.failed ? '暂不可用' : '统计中');
    if (unit) unit.hidden = !known;
    if (live) {
      target.liveValue = record?.value;
      target.element.title = '已更新浏览量';
    } else if (known) {
      const at = record?.at ? `（${new Date(record.at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}，北京时间）` : '';
      target.element.title = `最近记录${at}；实际浏览量不低于此值`;
    } else {
      target.element.title = target.failed ? '暂时无法获取浏览量，请稍后再试' : '正在获取浏览量';
    }
    target.element.style.removeProperty('display');
  }

  document.querySelectorAll('[data-page-views-url], [data-site-views-url]').forEach((element) => {
    if (element.dataset.pageViewsLoaded) return;
    const isSite = element.hasAttribute('data-site-views-url');
    let url;
    try { url = new URL(isSite ? element.dataset.siteViewsUrl : element.dataset.pageViewsUrl); } catch { return; }
    url.search = '';
    url.hash = '';
    if (url.origin !== window.location.origin) return;
    element.dataset.pageViewsLoaded = 'true';
    if (!articles.has(url.href)) articles.set(url.href, { url: url.href, increment: false, targets: [] });
    const article = articles.get(url.href);
    const metric = isSite ? 'site_pv' : 'page_pv';
    const baseline = Number((isSite ? element.dataset.siteViewsBaseline : element.dataset.pageViewsBaseline) ?? 0);
    const target = {
      element, metric, key: recordKey(metric, url.href),
      baseline: validCount(baseline) ? baseline : 0,
      selector: isSite ? '[data-site-views-value]' : '[data-page-views-value]'
    };
    const cached = stored[target.key];
    if (cached) remember(target.key, cached.value, cached.at);
    article.targets.push(target);
    targets.push(target);
    article.increment ||= element.hasAttribute(isSite ? 'data-site-views-increment' : 'data-page-views-increment');
    display(target);
  });

  async function loadSnapshot() {
    if (!script.dataset.snapshot || !targets.length) return;
    const url = new URL(script.dataset.snapshot, window.location.href);
    if (url.origin !== window.location.origin) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(url.href, { signal: controller.signal, credentials: 'omit', cache: 'force-cache' });
      if (!response.ok) return;
      const snapshot = await response.json();
      if (snapshot.api !== endpoint || snapshot.site !== window.location.origin) return;
      const at = Date.parse(snapshot.saved_at);
      if (!Number.isFinite(at)) return;
      targets.forEach((target) => {
        const value = target.metric === 'site_pv' ? snapshot.site_pv : snapshot.counts?.[target.key.slice(5)];
        remember(target.key, value, at);
        display(target);
      });
      persist();
    } catch { /* 保留历史基数及本机最近成功记录。 */ } finally { clearTimeout(timeout); }
  }

  let nextRequestAt = 0;
  let failures = 0;
  let unavailable = false;

  async function requestCounts(article, method) {
    const startAt = Math.max(Date.now(), nextRequestAt);
    nextRequestAt = startAt + 300;
    if (startAt > Date.now()) await pause(startAt - Date.now());
    if (unavailable) return { retry: false };
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(endpoint, {
        method, headers: { 'x-bsz-referer': article.url },
        credentials: 'omit', cache: 'no-store', signal: controller.signal
      });
      if (!response.ok) {
        const header = response.headers.get('Retry-After');
        const delay = header ? (Number.isFinite(Number(header)) ? Number(header) * 1000 : Date.parse(header) - Date.now()) : 0;
        const retry = [408, 429, 500, 502, 503, 504].includes(response.status) && !(delay > 5000);
        return { retry, delay: Number.isFinite(delay) ? Math.max(0, delay) : 0 };
      }
      const result = await response.json();
      if (result.success !== true) return { retry: true };
      const data = result.data;
      for (const metric of ['site_pv', 'page_pv']) {
        if (validCount(data?.[metric])) remember(recordKey(metric, article.url), data[metric], Date.now());
      }
      targets.forEach((target) => {
        if (target.metric !== 'site_pv' && !article.targets.includes(target)) return;
        const value = data?.[target.metric];
        if (validCount(value)) display(target, records.get(target.key)?.value === value);
      });
      persist();
      return { ok: article.targets.every((target) => validCount(data?.[target.metric])), retry: true };
    } catch {
      return { retry: true };
    } finally { clearTimeout(timeout); }
  }

  function markUnavailable(article) {
    article.targets.forEach((target) => { target.failed = true; display(target); });
  }

  async function load(article) {
    // 列表中的只读数值缓存一分钟，重复刷新不再为每篇文章重复查询。
    if (!article.increment && article.targets.every((target) => {
      const record = records.get(target.key);
      return record && Date.now() >= record.at && Date.now() - record.at < 60000;
    })) return;
    for (let attempt = 0; attempt < 3 && !unavailable; attempt++) {
      const result = await requestCounts(article, article.increment && attempt === 0 ? 'POST' : 'GET');
      if (result.ok) { failures = 0; return; }
      failures += 1;
      if (failures >= 6) unavailable = true;
      if (!result.retry || unavailable || attempt === 2) break;
      await pause(Math.max(result.delay ?? 0, 400 * (3 ** attempt) + Math.random() * 200));
    }
    markUnavailable(article);
  }

  const snapshot = loadSnapshot();
  const queue = [...articles.values()].sort((a, b) => Number(b.increment) - Number(a.increment));
  async function work() {
    while (queue.length) {
      if (unavailable) { queue.splice(0).forEach(markUnavailable); return; }
      await load(queue.shift());
    }
  }
  return Promise.all([snapshot, ...Array.from({ length: Math.min(2, queue.length) }, work)]);
})();
