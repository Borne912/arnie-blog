---
title: "搜索"
permalink: /search/
layout: single
author_profile: false
comments: false
share: false
---
<!-- 搜索索引由 GitHub Actions 在构建后用 Pagefind 生成（见 .github/workflows/jekyll.yml），本地 jekyll serve 时没有索引 -->
<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js"></script>
<div id="search"></div>
<script>
  window.addEventListener('DOMContentLoaded', function () {
    new PagefindUI({ element: "#search", showSubResults: true, showImages: false });
  });
</script>
