# 写作端（Obsidian / Typora）与 kramdown 之间的自动转换，省掉发布前的手工修改。
# 只作用于 _posts；围栏代码块和行内代码不受影响。
module BlogTweaks
  FENCE = /\A\s{0,3}(`{3,}|~{3,})/

  # 行内 $...$ -> kramdown 的 $$...$$（规则同 pandoc：开头后、结尾前不能是空格，结尾后不能紧跟数字）
  INLINE_MATH = /(?<![\\$])\$(?!\$)(?=\S)((?:\\.|[^$\\\n])+?)(?<=\S)(?<!\\)\$(?![$\d])/

  # Obsidian 插入的文章互链：[文字](2023-02-23-标题.md) 或 [文字](2023-02-23-标题.md#小标题)
  POST_LINK = %r{\]\((?:\./)?(\d{4}-\d{2}-\d{2}-[^)\s#]+?\.md)(#[^)\s]*)?\)}

  def self.convert_text(seg, links)
    seg = seg.gsub(INLINE_MATH) { "$$#{Regexp.last_match(1)}$$" }
    # 相对路径的站内图片 -> 绝对路径（文章网址带分类目录，相对路径在网页上会失效）
    seg = seg.gsub(%r{(\]\(|src=")(?:\.\./)*(?:\./)?assets/}) { "#{Regexp.last_match(1)}/assets/" }
    seg.gsub(POST_LINK) do
      m = Regexp.last_match
      name = m[1].gsub(/%(\h\h)/) { Regexp.last_match(1).hex.chr }.force_encoding("UTF-8")
      url = links[name]
      url ? "](#{url}#{m[2]})" : m[0]
    end
  end

  def self.convert(md, links = {}, track_math: true)
    out = []
    fence = nil
    in_math = false
    md.each_line do |line|
      if fence # 围栏代码块内原样保留，直到同种字符、长度不短于开头的结束行
        out << line
        fence = nil if line.strip.match?(/\A#{Regexp.escape(fence[0])}{#{fence.size},}\z/)
        next
      end
      if (m = line.match(FENCE))
        fence = m[1]
        out << line
        next
      end
      if track_math # $$ 公式块：kramdown 要求前后有空行，块内不做转换
        s = line.strip
        if in_math
          out << line
          if s.end_with?("$$")
            out << "\n"
            in_math = false
          end
          next
        elsif s.start_with?("$$") && s.scan("$$").size.odd?
          out << "\n" unless out.empty? || out.last.strip.empty?
          out << line
          in_math = true
          next
        end
      end
      # 行内代码 `...` 原样保留
      out << line.split(/(`+[^`]*`+)/).map.with_index { |seg, i| i.odd? ? seg : convert_text(seg, links) }.join
    end
    # 公式块没有闭合时，退回到不识别公式块的方式，至少保证后面的图片路径和行内公式被转换
    return convert(md, links, track_math: false) if in_math

    out.join
  end
end

# 所有文章读入之后、渲染之前转换正文。摘要在读入时就已生成，所以要按转换后的正文重建，
# 否则首页摘要里的公式和图片不会被转换。
Jekyll::Hooks.register :site, :post_read do |site|
  links = site.posts.docs.to_h { |doc| [File.basename(doc.path), doc.url] }
  site.posts.docs.each do |post|
    converted = BlogTweaks.convert(post.content, links)
    next if converted == post.content

    post.content = converted
    post.data["excerpt"] = Jekyll::Excerpt.new(post) if post.data["excerpt"].is_a?(Jekyll::Excerpt)
  end
end

# 只让 Pagefind 索引文章正文（不索引首页、归档页）
Jekyll::Hooks.register :posts, :post_render do |post|
  post.output = post.output.sub(%(<article class="page), %(<article data-pagefind-body class="page))
end
