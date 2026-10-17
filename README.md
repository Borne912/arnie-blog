# STiLE · 拾籍而上

个人博客 <https://stile.cc> 的源码。Jekyll + [Minimal Mistakes](https://mmistakes.github.io/minimal-mistakes/) 主题，推送到 `main` 后由 GitHub Actions 自动构建并发布到 GitHub Pages，本地不需要安装 Ruby。

## 发一篇文章

### 一次性设置（每台电脑做一次）

1. 用 Obsidian 打开本仓库文件夹作为 vault。仓库里的 `.obsidian/app.json` 已经设好：新笔记放在 `_posts/`，粘贴的图片存到 `assets/images/posts/`，链接用标准 Markdown 相对路径。
2. 安装社区插件 **Templater**，在它的设置里：
   - *Template folder location* 设为 `_templates`；
   - 打开 *Trigger Templater on new file creation*（这个开关只保存在本机，每台电脑都要开一次）；
   - 启用 *Folder templates*（不是 *File regex templates*），添加一条：`_posts` → `_templates/新文章.md`。
3. 安装社区插件 **Obsidian Git**：给 *Commit-and-sync* 设一个快捷键。

### 日常

1. 在 `_posts` 里新建笔记，输入标题。文件名、日期、front matter 会自动生成，文章默认是草稿（`published: false`），推送后不会出现在网站上。
   注意：仓库是公开的，草稿全文和其中粘贴的图片推送后在 GitHub 上任何人都能看到，图片也会随网站一起部署。不想公开的稿子先别同步。
2. 直接写。截图直接粘贴；公式照 Obsidian 的写法：行内 `$...$`，独立公式用独占一行的 `$$` 包起来。构建时会自动转换成网站需要的格式。
3. 写完后插入模板 `_templates/发布.md`：发布时间改成现在、去掉草稿标记、文件名日期改成今天。
4. 按 *Commit-and-sync*。1～2 分钟后文章出现在 stile.cc，构建失败会收到 GitHub 的邮件。

### 写作约定

- **摘要**：第一段之后的 `<!--more-->` 之前的内容会显示在首页。
- **分类**：`categories` 决定文章网址（`/分类/标题/`），文章发布后不要再改分类或文件名，否则旧链接和评论会失效。
- **日期**：`date` 必须带时区（`+0800`），否则会被当成 UTC。
- **头图**：默认使用统一的头图。个别文章想换，就在 front matter 里写（其他头图选项沿用默认值）：

  ```yaml
  header:
    overlay_image: /assets/images/posts/...
  ```

- **代码**：代码请放进围栏代码块（上下各一行三个反引号），代码块里的 `$` 不会被当成公式；不要用 4 个空格缩进的写法。
- **文章互链**：在 Obsidian 里直接插入指向另一篇文章的链接即可（`[文字](2023-02-23-xxx.md)`），构建时会换成文章网址。
- **front matter 写错**（比如缩进、引号不配对）时构建会直接失败并发邮件，网站保持上一版，改正后重新推送即可。

### 同步到公众号

文章发布到网站后，任选一种方式：

- Obsidian 插件 **NoteToMP**：一键发到公众号草稿箱（需要插件会员；插件的 `data.json` 已被 `.gitignore` 排除，不会把 AppSecret 提交上来）。
- [md.doocs.org](https://md.doocs.org)：粘贴 Markdown，先把图片路径里的 `../assets/` 替换成 `https://stile.cc/assets/`，排版后复制到公众号编辑器。

## 维护

- **依赖升级**：Dependabot 每月自动开升级 PR，PR 上的构建通过后直接合并即可。
- **Ruby 版本**：`.ruby-version` 写的是 `3.4`，CI 会自动使用最新的 3.4.x；大约 2028 年 3.4 停止维护前再升级一次。
- **站内搜索**：由 Pagefind 在 CI 里生成（`pagefind.yml`），搜索出问题不会阻塞发布。
- **暗色模式**：跟随系统设置（`assets/css/main-dark.scss`）；样式调整写在 `_sass/custom.scss`，字体等主题变量写在 `_sass/_vars.scss`，不要复制主题文件。
- **浏览量**：使用支持按文章查询的 [soxft/busuanzi](https://github.com/soxft/busuanzi) 接口，文章详情、首页、分类、标签、年份归档和相关文章都会在日期、阅读时长旁显示「N 次浏览」，全站页脚显示「网站总访问量：N 次」。总访问量累计 PV（重复访问、刷新也计数，不是独立访客数）；每次打开页面只增加一次，文章页的文章计数和全站计数共用一次请求，列表里的文章只读查询。总量沿用服务已记录的计数，非文章页面从本次功能上线起开始计入。开发环境不统计，服务异常时隐藏浏览量。`_config.yml` 的 `page_views: false` 全站关闭；页面 front matter 中的同名选项使该页面只查询、不新增计数。展示模板在 `_includes/page__meta.html` 和 `_includes/footer/custom.html`，升级主题时留意上游元信息模板的变化。
- **数据保存**：实时计数保存在 `page_views_api` 所指服务的 Redis 中，重新构建或部署博客不会清零。切换时选择从零开始，新服务与[原版不蒜子](https://busuanzi.ibruce.info/)不共享数据；切换不会删除旧服务的数据。公共服务的数据保留与故障恢复由运营方决定，不能保证永久保存。清空 `page_views_api` 可恢复原版服务，但原版只支持文章详情页显示。
- **计数备份**：GitHub Actions 的 `Back up article page views` 在北京时间每天 04:17 及网站部署成功后，用只读请求将所有已发表文章的计数及网站总访问量（`site_pv`）保存到本仓库 `page-views-backups` 分支的 `page-views.json`。每次备份形成独立提交，历史版本可下载。查询失败、响应无效或计数下降时任务报错，保留上一份成功备份。备份可用于迁移或导入自建服务，不会自动写回公共服务；最近一次成功备份后的新增访问仍可能丢失。可在 Actions 手动运行备份；公共仓库长期无活动时，GitHub 可能停用定时任务，需要重新启用。更换网站域名时，还需更新备份工作流中的清单地址。

## 本地预览（可选）

需要 Ruby 3.4：

```sh
bundle install
bundle exec jekyll serve
```

然后打开 <http://localhost:4000>。本地预览没有搜索索引，也不显示评论和浏览量。
