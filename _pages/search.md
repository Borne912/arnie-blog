---
title: "搜索"
seo_title: "站内文章搜索：查找技术教程与科研笔记"
description: "在 STiLE 博客中搜索已经发表的文章，通过关键词查找编程、软件工具、服务器配置、极化 SAR 遥感研究和阅读随笔。搜索结果提供正文片段，方便快速定位相关段落并打开原文查看完整内容。"
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
