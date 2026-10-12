# 写作端（Obsidian / Typora）与 kramdown 之间的自动转换，省掉发布前的手工修改。
# 只作用于 _posts；代码块和行内代码不受影响。
module BlogTweaks
  FENCE = /\A\s*(```|~~~)/

  # 行内 $...$ -> kramdown 的 $$...$$（规则同 pandoc：开头后、结尾前不能是空格，结尾后不能紧跟数字）
  INLINE_MATH = /(?<![\\$])\$(?!\$)(?=\S)((?:\\.|[^$\\\n])+?)(?<=\S)(?<!\\)\$(?![$\d])/

  def self.convert_text(seg)
    seg = seg.gsub(INLINE_MATH) { "$$#{Regexp.last_match(1)}$$" }
    # 相对路径的站内图片 -> 绝对路径（文章网址带分类目录，相对路径在网页上会失效）
    seg.gsub(%r{(\]\(|src=")(?:\.\./)*(?:\./)?assets/}) { "#{Regexp.last_match(1)}/assets/" }
  end

  def self.convert(md)
    out = []
    in_fence = false
    in_math = false
    md.each_line do |line|
      if line =~ FENCE
        in_fence = !in_fence
        out << line
        next
      end
      if in_fence
        out << line
        next
      end
      if line.strip == "$$" # 独占一行的公式块定界符：kramdown 要求前后有空行
        if in_math
          out << line << "\n"
        else
          out << "\n" unless out.empty? || out.last.strip.empty?
          out << line
        end
        in_math = !in_math
        next
      end
      if in_math
        out << line
        next
      end
      # 行内代码 `...` 原样保留
      out << line.split(/(`+[^`]*`+)/).map.with_index { |seg, i| i.odd? ? seg : convert_text(seg) }.join
    end
    out.join
  end
end

# 所有文章读入之后、渲染之前转换正文。摘要在读入时就已生成，所以要按转换后的正文重建，
# 否则首页摘要里的公式和图片不会被转换。
Jekyll::Hooks.register :site, :post_read do |site|
  site.posts.docs.each do |post|
    converted = BlogTweaks.convert(post.content)
    next if converted == post.content

    post.content = converted
    post.data["excerpt"] = Jekyll::Excerpt.new(post) if post.data["excerpt"].is_a?(Jekyll::Excerpt)
  end
end

# 只让 Pagefind 索引文章正文（不索引首页、归档页）
Jekyll::Hooks.register :posts, :post_render do |post|
  post.output = post.output.sub(%(<article class="page), %(<article data-pagefind-body class="page))
end
