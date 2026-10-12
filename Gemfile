source "https://rubygems.org"

# 版本由提交进仓库的 Gemfile.lock 锁定，升级交给 Dependabot（.github/dependabot.yml）
gem "jekyll", "~> 4.4"
gem "minimal-mistakes-jekyll", "~> 4.28"

group :jekyll_plugins do
  gem "jekyll-archives", "~> 2.3"
end

# Windows 没有系统时区数据，_config.yml 里的 timezone 在 Windows 本地构建时需要这两个 gem
gem "tzinfo", ">= 1", "< 3", platforms: :windows
gem "tzinfo-data", platforms: :windows
