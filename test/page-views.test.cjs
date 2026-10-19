const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const code = fs.readFileSync(path.join(__dirname, '../assets/js/page-views.js'), 'utf8');
const API = 'https://stats.example.test/api';
const ORIGIN = 'https://stile.cc';
const FIRST = `${ORIGIN}/first/`;
const SECOND = `${ORIGIN}/second/`;
const SNAPSHOT = `${ORIGIN}/assets/data/page-views-snapshot.json`;
const STORAGE = `stile:page-views:v1:${API}`;

function element(url, { site = false, baseline = 54, increment = false } = {}) {
  const dataset = site ? { siteViewsUrl: url, siteViewsBaseline: String(baseline) } : { pageViewsUrl: url, pageViewsBaseline: String(baseline) };
  if (increment) dataset[site ? 'siteViewsIncrement' : 'pageViewsIncrement'] = '';
  const value = { textContent: '' };
  const unit = { hidden: false };
  const style = { display: 'none', removeProperty(key) { delete this[key]; } };
  return {
    dataset, style, value, unit,
    hasAttribute(name) { return Object.hasOwn(dataset, name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())); },
    querySelector(selector) { return selector === '[data-views-unit]' ? unit : value; }
  };
}

const success = (page = 7, site = 123) => ({
  ok: true, status: 200, headers: { get() { return null; } },
  async json() { return { success: true, data: { page_pv: page, site_pv: site } }; }
});
const failure = (status = 503, retryAfter = null) => ({ ok: false, status, headers: { get() { return retryAfter; } } });

async function run({ elements = [element(FIRST)], respond = () => success(), snapshot, cache, storageFails = false, snapshotDelay = 0 } = {}) {
  const requests = [], delays = [];
  const values = new Map(cache ? [[STORAGE, typeof cache === 'string' ? cache : JSON.stringify(cache)]] : []);
  const script = { dataset: { api: API, ...(snapshot ? { snapshot: SNAPSHOT } : {}) } };
  const sandbox = {
    URL, AbortController,
    document: { currentScript: script, querySelectorAll() { return elements; } },
    window: { location: { origin: ORIGIN, href: FIRST }, localStorage: {
      getItem(key) { if (storageFails) throw new Error('storage denied'); return values.get(key) ?? null; },
      setItem(key, value) { if (storageFails) throw new Error('storage full'); values.set(key, value); }
    } },
    setTimeout(callback, delay) { delays.push(delay); return setTimeout(callback, delay >= 5000 ? 30 : 0); },
    clearTimeout,
    async fetch(url, options = {}) {
      const call = { url: String(url), method: options.method ?? 'GET', referer: options.headers?.['x-bsz-referer'], options };
      requests.push(call);
      if (call.url === SNAPSHOT) {
        if (snapshotDelay) await new Promise(resolve => setTimeout(resolve, snapshotDelay));
        return { ok: true, async json() { return snapshot; } };
      }
      return respond(call, requests.filter(request => request.url === API).length);
    }
  };
  const context = vm.createContext(sandbox);
  const rerun = () => vm.runInContext(code, context);
  await rerun();
  return { elements, requests, delays, values, rerun, api: requests.filter(request => request.url === API) };
}

test('failed article requests keep the saved count visible while other articles update', async () => {
  const first = element(FIRST), second = element(SECOND, { baseline: 96 });
  const result = await run({ elements: [first, second], respond: call => call.referer === FIRST ? failure() : success(2), snapshot: {
    api: API, site: ORIGIN, saved_at: '2026-10-18T00:00:00Z', site_pv: 54, counts: { [FIRST]: 3, [SECOND]: 1 }
  } });
  assert.equal(first.value.textContent, '≥57');
  assert.equal(first.dataset.viewsState, 'cached');
  assert.equal(second.value.textContent, '98');
  assert.ok(result.api.filter(call => call.referer === FIRST).length <= 3);
  assert.equal(first.style.display, undefined);
});

test('a lost POST response is recovered with GET and never increments twice', async () => {
  const article = element(FIRST, { increment: true });
  const footer = element(FIRST, { site: true, baseline: 4453, increment: true });
  const result = await run({ elements: [article, footer], respond(call) {
    if (call.method === 'POST') throw new Error('response lost after server counted');
    return success();
  } });
  assert.deepEqual(result.api.map(call => call.method), ['POST', 'GET']);
  assert.equal(article.value.textContent, '61');
  assert.equal(footer.value.textContent, '4,576');
});

test('timeout recovery also uses only read requests after the first POST', async () => {
  const result = await run({ elements: [element(FIRST, { increment: true })], respond(call) {
    if (call.method === 'POST') return new Promise((resolve, reject) => call.options.signal.addEventListener('abort', () => reject(new Error('timeout')), { once: true }));
    return success();
  } });
  assert.deepEqual(result.api.map(call => call.method), ['POST', 'GET']);
  assert.equal(result.elements[0].value.textContent, '61');
});

test('temporary failures retry within a limit and respect a short Retry-After', async () => {
  const result = await run({ respond: (call, attempt) => attempt < 3 ? failure(429, '1') : success() });
  assert.equal(result.api.length, 3);
  assert.ok(result.delays.includes(1000));
  assert.equal(result.elements[0].value.textContent, '61');
});

test('permanent errors and long rate limits retain the known count without immediate retries', async () => {
  for (const response of [failure(403), failure(429, '120')]) {
    const result = await run({ respond: () => response });
    assert.equal(result.api.length, 1);
    assert.equal(result.elements[0].value.textContent, '≥54');
  }
});

test('a full outage stops background requests across a long archive', async () => {
  const elements = Array.from({ length: 42 }, (_, index) => element(`${ORIGIN}/post-${index}/`, { baseline: 10 }));
  const result = await run({ elements, respond: () => failure() });
  assert.ok(result.api.length <= 8, result.api.length);
  assert.ok(elements.every(target => target.value.textContent === '≥10' && target.style.display === undefined));
});

test('fresh raw article cache avoids repeat reads but still counts the current page once', async () => {
  const article = element(FIRST);
  const footer = element(`${ORIGIN}/`, { site: true, baseline: 4453, increment: true });
  const result = await run({ elements: [article, footer], cache: { [`page:${FIRST}`]: { value: 6, at: Date.now() } } });
  assert.deepEqual(result.api.map(call => call.method), ['POST']);
  assert.equal(article.value.textContent, '≥60');
  assert.equal(footer.value.textContent, '4,576');
});

test('cached values contain no historical baseline and survive refresh without adding it twice', async () => {
  const first = await run();
  const saved = JSON.parse(first.values.get(STORAGE));
  assert.equal(saved[`page:${FIRST}`].value, 7);
  const second = await run({ cache: saved, respond() { throw new Error('fresh cache should avoid reading'); } });
  assert.equal(second.elements[0].value.textContent, '≥61');
  assert.equal(second.api.length, 0);
});

test('storage errors or invalid cached JSON do not prevent recovery from the site snapshot', async () => {
  for (const options of [{ storageFails: true }, { cache: 'not json' }]) {
    const result = await run({ ...options, respond: () => failure(), snapshot: {
      api: API, site: ORIGIN, saved_at: '2026-10-18T00:00:00Z', counts: { [FIRST]: 3 }
    } });
    assert.equal(result.elements[0].value.textContent, '≥57');
  }
});

test('a late old snapshot never overwrites a fresh live response or its status', async () => {
  const result = await run({ snapshotDelay: 5, snapshot: {
    api: API, site: ORIGIN, saved_at: '2026-10-18T00:00:00Z', counts: { [FIRST]: 3 }
  } });
  assert.equal(result.elements[0].value.textContent, '61');
  assert.equal(result.elements[0].dataset.viewsState, 'live');
});

test('unknown counts show an unavailable message after failure rather than a fabricated zero', async () => {
  const result = await run({ elements: [element(FIRST, { baseline: 0 })], respond: () => failure() });
  assert.equal(result.elements[0].value.textContent, '暂不可用');
  assert.equal(result.elements[0].unit.hidden, true);
  assert.equal(result.elements[0].style.display, undefined);
});

test('invalid API data or a foreign-provider snapshot cannot replace known records', async () => {
  const result = await run({ respond: () => success(-1, '123'), snapshot: {
    api: 'https://different.example.test/api', site: ORIGIN, saved_at: '2026-10-18T00:00:00Z', counts: { [FIRST]: 9000 }
  } });
  assert.equal(result.elements[0].value.textContent, '≥54');
  assert.equal(result.api.length, 3);
});

test('evaluating the script twice does not send a second POST', async () => {
  const result = await run({ elements: [element(FIRST, { increment: true })] });
  await result.rerun();
  assert.equal(result.requests.filter(call => call.method === 'POST').length, 1);
});
