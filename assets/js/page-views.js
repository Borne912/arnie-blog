// soxft/busuanzi: 每次打开页面只 POST 一次；列表中的其他文章用 GET 查询。
(() => {
  const endpoint = document.currentScript.dataset.api;
  const articles = new Map();

  document.querySelectorAll('[data-page-views-url], [data-site-views-url]').forEach((element) => {
    if (element.dataset.pageViewsLoaded) return;
    element.dataset.pageViewsLoaded = 'true';

    const isSite = element.hasAttribute('data-site-views-url');
    const url = new URL(isSite ? element.dataset.siteViewsUrl : element.dataset.pageViewsUrl);
    url.search = '';
    url.hash = '';
    if (url.origin !== window.location.origin) return;

    if (!articles.has(url.href)) {
      articles.set(url.href, { url: url.href, increment: false, targets: [] });
    }
    const article = articles.get(url.href);
    article.targets.push({
      element,
      metric: isSite ? 'site_pv' : 'page_pv',
      baseline: Number((isSite ? element.dataset.siteViewsBaseline : element.dataset.pageViewsBaseline) ?? 0),
      selector: isSite ? '[data-site-views-value]' : '[data-page-views-value]'
    });
    article.increment ||= element.hasAttribute(isSite ? 'data-site-views-increment' : 'data-page-views-increment');
  });

  async function load(article) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch(endpoint, {
        method: article.increment ? 'POST' : 'GET',
        headers: { 'x-bsz-referer': article.url },
        credentials: 'omit',
        cache: 'no-store',
        signal: controller.signal
      });
      if (!response.ok) return;
      const result = await response.json();
      if (result.success !== true) return;

      article.targets.forEach(({ element, metric, baseline, selector }) => {
        const count = result.data?.[metric];
        if (!Number.isSafeInteger(count) || count < 0) return;
        if (!Number.isSafeInteger(baseline) || baseline < 0) return;
        const total = baseline + count;
        if (!Number.isSafeInteger(total)) return;
        element.querySelector(selector).textContent = total.toLocaleString('zh-CN');
        element.style.removeProperty('display');
      });
    } catch {
      // 网络异常、超时或返回数据无效时保持隐藏，不把失败显示成 0 次浏览。
    } finally {
      clearTimeout(timeout);
    }
  }

  // 归档页可能列出很多文章，限制并发；同一篇文章在一页中只请求一次。
  const queue = [...articles.values()].sort((a, b) => Number(b.increment) - Number(a.increment));
  const workers = Math.min(3, queue.length);
  async function work() {
    while (queue.length) await load(queue.shift());
  }
  for (let i = 0; i < workers; i++) work();
})();
