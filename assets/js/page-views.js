// soxft/busuanzi: GET 只读查询；POST 仅用于当前文章的一次浏览。
(() => {
  const endpoint = document.currentScript.dataset.api;
  const articles = new Map();

  document.querySelectorAll('[data-page-views-url]').forEach((element) => {
    if (element.dataset.pageViewsLoaded) return;
    element.dataset.pageViewsLoaded = 'true';

    const url = new URL(element.dataset.pageViewsUrl);
    url.search = '';
    url.hash = '';
    if (url.origin !== window.location.origin) return;

    if (!articles.has(url.href)) {
      articles.set(url.href, { url: url.href, increment: false, elements: [] });
    }
    const article = articles.get(url.href);
    article.elements.push(element);
    article.increment ||= element.hasAttribute('data-page-views-increment');
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
      const count = result.data?.page_pv;
      if (result.success !== true || !Number.isSafeInteger(count) || count < 0) return;

      article.elements.forEach((element) => {
        element.querySelector('[data-page-views-value]').textContent = count.toLocaleString('zh-CN');
        element.style.display = 'inline';
      });
    } catch {
      // 网络异常、超时或返回数据无效时保持隐藏，不把失败显示成 0 次浏览。
    } finally {
      clearTimeout(timeout);
    }
  }

  // 归档页可能列出很多文章，限制并发；同一篇文章在一页中只请求一次。
  const queue = [...articles.values()];
  const workers = Math.min(3, queue.length);
  async function work() {
    while (queue.length) await load(queue.shift());
  }
  for (let i = 0; i < workers; i++) work();
})();
