(() => {
  const footer = document.querySelector('[data-site-runtime]');
  if (!footer) return;
  const launchedAt = Date.parse(footer.dataset.launchedAt);
  if (!Number.isFinite(launchedAt)) return;

  const value = footer.querySelector('[data-site-runtime-value]');
  const row = footer.querySelector('[data-site-runtime-row]');
  const pad = (number) => String(number).padStart(2, '0');

  function update() {
    const elapsed = Math.max(0, Math.floor((Date.now() - launchedAt) / 1000));
    const days = Math.floor(elapsed / 86400);
    const hours = Math.floor((elapsed % 86400) / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;
    value.textContent = `${days.toLocaleString('zh-CN')} 天 ${pad(hours)} 时 ${pad(minutes)} 分 ${pad(seconds)} 秒`;
    row.hidden = false;
  }

  update();
  // 每次根据当前时间重新计算，标签页休眠后也不会积累计时误差。
  setInterval(update, 1000);
})();
