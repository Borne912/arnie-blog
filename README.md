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
- **搜索标题与摘要**：`_includes/seo.html` 基于 Minimal Mistakes 4.28.1，使用 `seo_title` 自定义浏览器及搜索结果中的标题，`description` 自定义摘要；缺省摘要从正文提取并限制为 150 个字符。首页分页、标签和分类页分别生成摘要，避免重复使用站点简介。正文标题和链接仍由原有 `title` 和 permalink 决定。升级主题时对照上游 SEO 模板检查其余标签的变化。发布流程用 `_scripts/check_seo.py` 检查所有站点地图页面的规范链接、标题和摘要唯一性，以及本项目的长度目标（标题 15–80、摘要 60–150 字符）；这些是维护标准，不代表搜索引擎的排名规则。短标题可另填更具体的 `seo_title`，代码示例较多的文章可手写 `description`。
- **站点地图与 Bing**：[站点地图](https://stile.cc/sitemap.xml)由 `jekyll-sitemap` 生成，[robots.txt](https://stile.cc/robots.txt)自动声明其地址。若 Bing 后台还未登记，可在 Sitemaps 中提交 `https://stile.cc/sitemap.xml`；现有 Windsor.ai 的 Bing 连接仅提供报表读取，不能操作后台登记。站点修复后，后台建议需等待重新抓取或扫描才会更新。
- **IndexNow 自动通知**：`indexnow-key.txt` 是随网站发布的所有权验证文件。`.github/workflows/indexnow.yml` 在主分支的网站部署成功后，先读取线上站点地图并核对线上验证文件，再将当前规范网址批量通知 Bing 的 IndexNow 接口；可在 Actions 手动运行 `Notify Bing with IndexNow`。提交失败会使该独立任务报错，网站部署不受影响。日志的 HTTP 200 表示已接收，202 表示已接收且所有权验证待处理，均不保证收录或排名。更换域名时同时更新通知工作流中的地址。
- **暗色模式**：跟随系统设置（`assets/css/main-dark.scss`）；样式调整写在 `_sass/custom.scss`，字体等主题变量写在 `_sass/_vars.scss`，不要复制主题文件。
- **上线日期与运行时长**：`_config.yml` 的 `site_launched_at` 按首篇已发布文章《使用MySQL的常规操作》的发布时间设为 `2021-11-21T16:46:00+08:00`。页脚显示北京时间的上线日期、时刻及累计「天、时、分、秒」，每秒自动更新。该值独立于构建和部署时间，重新发布不会重置；修改时保留时区，留空则隐藏。不依赖访问量服务，本地预览也可以查看。运行时长表示距上线时间的累计时长，不是可用性监测结果。
- **浏览量**：使用支持按文章查询的 [soxft/busuanzi](https://github.com/soxft/busuanzi) 接口，文章详情、首页、分类、标签、年份归档和相关文章都会在日期、阅读时长旁显示「N 次浏览」，全站页脚显示「网站总访问量：N 次」。显示值为固定历史基数加接口的实时计数。总访问量累计 PV（重复访问、刷新也计数，不是独立访客数）；每次打开页面只增加一次，文章页的文章计数和全站计数共用一次请求，列表里的文章只读查询。非文章页面的实时计数从全站计数功能上线起开始计入。开发环境不统计，服务异常时隐藏浏览量。`_config.yml` 的 `page_views: false` 全站关闭；页面 front matter 中的同名选项使该页面只查询、不新增计数。展示模板在 `_includes/page__meta.html` 和 `_includes/footer/custom.html`，升级主题时留意上游元信息模板的变化。
- **历史浏览量恢复**：`_data/page_views_history.json` 固定保存从 GA4 属性 `482655594`（统计 ID `G-9VN8L46JLC`）读取的 `screen_page_views`，包含来源、时区、导出时间及网址对应计数。范围为北京时间 `2025-03-20 00:00` 至 `2026-10-16 22:35` 之前；共恢复全站 **4,453** 次，其中 **2,418** 次准确对应全部 **42** 篇现有文章。GA4 每日汇总和按页面汇总已核对一致；编码和未编码的同一路径合并，无法对应文章的页面仅计入全站总量。新服务于 `2026-10-16 22:35:16` 完成部署，历史范围停在该分钟开始，避免与实时计数重叠；这不代表自首篇文章发布起的完整流量，也不补估新服务尚未统计的非文章页面。Bing 网站管理员工具的点击和曝光不作为 PV 累加。历史值仅在显示时加一次，不写入公共计数服务，重新构建、刷新或重复备份不会重复导入。扩展历史范围前必须核对来源、日期与实时计数的边界。
- **数据保存**：实时计数保存在 `page_views_api` 所指服务的 Redis 中，重新构建或部署博客不会清零。切换时选择从零开始，新服务与[原版不蒜子](https://busuanzi.ibruce.info/)不共享数据；切换不会删除旧服务的数据。公共服务的数据保留与故障恢复由运营方决定，不能保证永久保存。清空 `page_views_api` 可恢复原版服务，但原版只支持文章详情页显示。
- **计数备份**：GitHub Actions 的 `Back up article page views` 在北京时间每天 04:17 及网站部署成功后，用只读请求将所有已发表文章的计数及网站总访问量保存到本仓库 `page-views-backups` 分支的 `page-views.json`。版本 3 中 `site_pv` 和 `counts` 保留接口原始实时计数，`history` 保存固定历史基数及来源；显示总量为两部分相加，迁移时只加一次。历史基数也保存在主分支，能独立恢复。每次备份形成独立提交，历史版本可下载。查询失败、响应无效、计数下降或历史基数意外缺失时任务报错，保留上一份成功备份。备份可用于迁移或导入自建服务，不会自动写回公共服务；最近一次成功备份后的新增访问仍可能丢失。可在 Actions 手动运行备份；公共仓库长期无活动时，GitHub 可能停用定时任务，需要重新启用。更换网站域名时，还需更新备份工作流中的清单地址。

## 本地预览（可选）

需要 Ruby 3.4：

```sh
bundle install
bundle exec jekyll serve
```

然后打开 <http://localhost:4000>。本地预览没有搜索索引，也不显示评论和浏览量。
