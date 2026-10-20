# 自建文章浏览量服务

当前采用已有的 BWG VPS 承载服务，Cloudflare 管理 `stats.stile.cc` 的 DNS、HTTPS 代理和必要的流量规则。网站正文继续由 GitHub Pages 提供。统计接口为 `https://stats.stile.cc/api`；2026-10-20 已通过 Windows 的 BWG SSH 连接安装，42 篇原始计数及全站 PV 82 校验通过，HTTPS 证书与自动续期已配置。首次验证时 Cloudflare 为仅 DNS，开启代理前另核对 Full (strict) 与 API 绕过缓存。

**本次使用原生 systemd 部署包**：从 Mac 的 `BWG` 连接或 Windows PowerShell 上传并运行，不蒜子与独立 Redis 运行于 VPS，复用现有 Nginx；不需要 VPS Docker 或 Tailscale。执行、报告和失败恢复见 [native/README.md](native/README.md)。下文保留其他主机和 Docker 方案的手动参考，不是本次部署包的执行顺序。

| 部署位置 | 连接方式 | 运行条件 |
| --- | --- | --- |
| BWG VPS（推荐） | Cloudflare 代理 → 已有 Nginx → 统计服务 → Redis | VPS 保持运行；检查主要读者地区的实际访问延迟 |
| BWG VPS + Tunnel | Cloudflare Tunnel → VPS 本地统计服务 → Redis | 不需要开放统计服务的公网端口；需要常驻 cloudflared |
| Mac mini + Tunnel | Cloudflare Tunnel → Mac 本地统计服务 → Redis | Mac、容器运行时、家中网络及 cloudflared 均需持续运行；防止休眠，登录后恢复服务 |

Tunnel 提供入站连接，不负责保存浏览量，也不能在主机断电、休眠或网络中断时继续计数。M4 的计算性能足够，主要区别在运行环境。正式选择前，核对 VPS 系统、可用内存、现有反向代理及网络表现。

已核对固定镜像的清单：本次使用的 `busuanzi:v2.8.8` 只有 Linux amd64 镜像，适合 x86_64 VPS。M4 需要自行构建 ARM64 镜像，或在支持兼容运行的 Docker Desktop 中叠加 `compose.mac.yaml`，例如 `docker compose -f compose.yaml -f compose.mac.yaml up -d --wait`。本次测试运行于 Linux amd64，尚未在 M4 实机验证，不把性能测试或兼容性视为已完成。

## 当前 VPS 与流量预算

用户提供的系统为 Ubuntu 24.04.5 LTS / x86_64，约 1 GiB 内存、549 MiB 可用，已有 Nginx 1.24.0，没有 Docker，且同机运行 VPN。本次复用 Nginx，增加 Redis 和统计服务两个原生 systemd 服务，各设 128 MiB 内存上限；系统与现有应用不包含在这两个上限内。

本地 Linux amd64 隔离验证已通过 Nginx 1.24 的 HTTPS、CORS、ACME 路径、42 篇原始计数导入、重复导入保护和容器重建恢复。一次验证后的容器内存采样约为统计服务 4.6 MiB、Redis 4.0 MiB；这不包含 Docker 守护进程，不作为 VPS 实际峰值或容量保证。

VPS 仅处理计数 API，文章、图片、主题文件仍由 GitHub Pages 提供。按一次页面访问合计 50–200 KB 双向流量做规划估算：每月 1 万次页面访问约 0.5–2 GB，10 万次约 5–20 GB。文章列表会查询多篇计数，长归档页开销更大；浏览器缓存可减少重复查询。这是预算，不是实测或流量上限，不包含异常请求。首次安装软件和镜像还有一次性下载流量。1 TB 额度是否够用，仍需结合 VPN 的实际用量。

Nginx 访问日志记录请求和响应的应用层字节数，不记录访客 IP；这些字节不包含完整的 TLS/TCP 开销，也不代表 VPS 的计费流量。总量以 BWG 面板为准。

安装和启动 Docker 前先只读检查 VPN 类型、转发和 NAT 规则，并保留现有防火墙配置。Docker 的默认桥接网络会配置转发/NAT，不应在未核对 VPN 路由时直接启动。若现有 VPN 依赖的转发规则会冲突，调整部署方式后再实施；不要清空防火墙或更换现有 Nginx 主配置。

用户提供的当前监听快照确认：公网 TCP 80/443 为 Nginx，TCP 8443 为 Xray，UDP 39847/53306 为 V2Ray；本机 TCP 8964 为 V2Ray、9443 为 Nginx，SSH 为 TCP 2912。这只能证明进程和监听地址，不能证明防火墙放行或 Nginx 的 HTTP/stream 路由。尤其存在本机 9443 时，应先核对 443 是否用于 TLS/SNI 分流；不要直接在 HTTP 配置中新增同端口监听、停止现有进程或更改 VPN 入口。

用户随后提供的过滤输出包含 `listen 443 ssl http2;` 和 `listen 127.0.0.1:9443 ssl http2;`，可按现有 Nginx 的 HTTP HTTPS 入口继续准备，优先新增独立 `server_name stats.stile.cc`。这次执行的过滤表达式在配置块分支丢失了两个 `*`，不能根据没显示 http/stream 块就断定不存在其他分流；无需重复依靠这条过滤确认入口，接入后直接核对现有虚拟主机、default_server、证书、代理和完整配置测试，再决定加载位置。新增虚拟主机不抢占默认站点，不套用全站 Cloudflare-only 防火墙规则，以免影响同机 VPN。

可通过已有的 Mac SSH 连接执行以下只读过滤，初步查看 Nginx 的 http/stream、监听及 ssl_preread 指令；它不输出代理路径、证书内容或完整配置。若看到 stream/ssl_preread，再单独核对实际分流关系；没有匹配行不代表检查通过，也不能取代部署前的 `nginx -t`。

```sh
ssh -t BWG "sudo nginx -T 2>&1 | awk '/^[[:space:]]*(http|stream)[[:space:]]*[{]/ || /^[[:space:]]*(listen|ssl_preread)[[:space:]]/'"
```

## 可选：从云环境经 Tailscale 管理

当前云环境没有可用的 VPN/TCP 设置入口，用户也未找到该入口，因此已改为从 Mac 的现有 BWG 连接部署。用户已保存受限 Tailnet 策略，但无需为本次部署继续执行以下旧接入脚本。以下仅作为以后具备云端配置条件时的管理通道参考。

若从本任务的云环境部署，需先完成 Tailscale 管理通道接入。先核对现有 Tailnet 访问策略，再安排设备加入；不能假定私人账号下的设备已经相互隔离。新建 Tailnet 默认允许设备互访，且用户态模式可能将获准的入站 TCP 连接转发到同端口的本机服务，原本只监听 `127.0.0.1` 的 Xray 管理面板或计数 API 也需要访问策略保护。[默认规则](https://tailscale.com/docs/reference/examples/acls)、[官方项目关于用户态转发的说明](https://github.com/tailscale/tailscale/issues/7848)。

访问策略应使用独立的服务器和部署环境身份（例如标签），仅允许指定管理设备/部署环境连接 VPS 的 `tcp:2912`，并限制这两个新设备主动访问个人电脑、NAS 和其他私网设备。所有已有的宽泛规则都需一并核对；新增窄规则不能收紧已有的允许规则。策略变更应保留原有设备之间确有需要的访问，并在入网后验证允许和拒绝的端口。继续使用原有 OpenSSH 密钥认证，不启用 Tailscale SSH，不接受 DNS 和子网路由，不启用出口节点或公网分享。临时部署身份在任务结束后撤销。

Tailnet 现状已由用户提供的策略和截图核对：无标签设备、无出口节点；3 台 OpenWRT 共发布 6 条路由，全部位于 Approved，无 Awaiting Approval 项。实际账号和路由配置保存在本任务工作目录的接入文件中，不写入公开博客仓库。

最终策略应保留用户身份设备和这 6 条已批准路由之间原有的访问权限（包括原策略允许的子网互访），单独增加 `tag:stile-deploy` → `tag:stile-vps` 的 TCP 2912。两个新标签不属于原有用户/路由集合，不能主动访问个人设备或已批准子网。实际子网互通仍取决于 OpenWRT 现有路由、SNAT 和防火墙，不通过本次策略替它启用新的转发功能。

`tailscale-policy.personal-only.example.json` 只是没有子网用途时的通用示例，**不适用于此 Tailnet 的完整替换**。本任务使用独立的实际策略文件及与用户原策略等价的恢复文件，均保存在仓库外。实际策略保留原有用户设备的 Tailscale SSH 规则；VPS 继续使用原 OpenSSH 2912 和密钥认证，保持 Tailscale SSH 关闭。没有额外允许个人设备通过 Tailnet 连接 VPS，Mac 的原 `BWG` 公网 SSH 仍由原服务器配置控制。

实际策略附带后台测试，检查原用户仍有各路由的访问权限，同时两个新标签无法访问原用户设备、6 条路由中的代表地址或其他已观察到的 VPS 服务端口。代表地址用于权限断言，不代表已对相应主机服务做连通测试。测试中的 UDP 服务端口来自现有快照，不假定永久固定。本地完成 JSON 和策略范围核对后，仍需后台接受策略及全部测试，再核对实际连接。

应用时先另存当前后台完整策略，再在 Access controls 的 JSON 编辑器中用实际策略文件**完整替换**旧内容，不能把它追加到旧的全部互通规则后。后台校验或测试不通过时保留原策略，核对错误后修正；不要删除隔离断言来绕过失败。应用后验证原有常用子网访问，再安排新节点入网。[子网授权与路由批准的区别](https://tailscale.com/docs/features/subnet-routers#add-access-rules-for-the-advertised-subnet-routes)。

VPS 必须在首次入网时使用 `tag:stile-vps`，云端必须以 `tag:stile-deploy` 身份入网。不能先将云端当作普通用户设备加入个人 Tailnet 再补标签，因为它会暂时继承个人设备互通权限。两个节点都只使用各自的专用标签；标签权限取并集，不能额外附加有广泛权限的标签。若云环境的配置流程不能提供受限标签身份，应先解决该配置条件，不按普通用户身份入网。[标签身份说明](https://tailscale.com/docs/features/tags)、[选择器说明](https://tailscale.com/docs/reference/targets-and-selectors)。

`setup-tailnet.sh` 仅提供 Ubuntu 24.04 / x86_64 的首次安装，**不会登录或加入网络**：先只读检查本机 SSH 2912 端口和已有 Tailscale 状态，在首次启动前预设用户态模式，不修改 SSH/Xray/Nginx 配置，安装后核对默认路由及 DNS。仅用于未安装、未配置 Tailscale 的主机；检测到已有配置即停止，不覆盖它。关闭 DNS、路由和 Tailscale SSH 并不能代替访问策略。

将脚本保存到已能连接 `BWG` 的 Mac 下载目录，然后执行：

```sh
scp ~/Downloads/setup-tailnet.sh BWG:/tmp/setup-tailnet.sh
ssh -t BWG 'sudo bash /tmp/setup-tailnet.sh --install'
```

安装脚本不登录。用户已确认实际策略在后台保存成功。将 `join-tailnet.sh` 同样保存到 Mac 下载目录，通过原有 SSH 连接上传并运行；它只接受新登录或已有的单一 `tag:stile-vps` 身份，不覆盖其他登录。

```sh
scp ~/Downloads/join-tailnet.sh BWG:/tmp/join-tailnet.sh
ssh -t BWG 'sudo bash /tmp/join-tailnet.sh --join'
```

在浏览器打开接入脚本显示的链接，使用已保存策略的账号授权。脚本固定使用 `--advertise-tags=tag:stile-vps --accept-dns=false --accept-routes=false --ssh=false --netfilter-mode=off`，核对实际标签、私网 IPv4、默认路由、DNS 和本机 SSH；本次新登录失败或核对失败会停止 Tailscale，不恢复或覆盖其他服务的配置。若已有同标签连接，则只核对，不重新登录或变更其参数。输出中只需提供 VPS 私网 IPv4 和服务器 SSH 公钥。

取得 VPS 的实际 `100.x` 私网地址后，云环境侧还须为它配置 `/32` TCP 授权；该环境授权覆盖该 IP 的所有端口，**不能代替 Tailnet 中仅允许 TCP 2912 的规则**。账号密钥只填在环境配置界面，不发送到聊天。TCP 授权变更需创建使用新配置的环境，再核对状态并准备 SSH 用户公钥授权。用户公钥授权安排在环境配置稳定之后，以免替换环境丢失临时私钥。

安装脚本已通过 Bash 语法、ShellCheck、拒绝错误系统的检查，并用隔离的 dpkg 测试验证首次安装保留预设的用户态配置。接入脚本已通过 Bash/ShellCheck，以及无外网临时容器中 8 项模拟检查：只读模式、正常接入、同标签已接入、其他身份拒绝、登录失败、额外标签拒绝、DNS 变化、默认路由变化。模拟不代表真实 VPS 或 Tailnet 的连通性已经验证。

`run-tailnet-setup.sh` 将首次安装与接入顺序执行，安装失败时不会继续登录。提供给用户的接入包仅包含这三个脚本与使用说明，不含 SSH 私钥、实际 Tailnet 策略或授权密钥；已解压到 Mac 下载目录时，可执行：

```sh
scp -r ~/Downloads/stile-bwg-tailnet BWG:~/
ssh -t BWG 'sudo bash ~/stile-bwg-tailnet/run-tailnet-setup.sh'
```

上述首次接入入口检测到已有安装就停止，不自动覆盖。如果安装已成功但浏览器登录失败，保留输出，核对服务状态后单独运行接入脚本，不盲目重装。尚未在真实 VPS 执行。官方依据：[Ubuntu 安装源](https://pkgs.tailscale.com/stable/#ubuntu-noble)、[用户态模式](https://tailscale.com/docs/concepts/userspace-networking)。

## 可选：Docker 手动部署

以下仅适用于选择 Docker 方式的其他部署，不与本次原生安装同时执行。Linux VPS 需要 Docker Engine、Compose v2；迁移文件可在有 Python 3 的电脑上生成。镜像已固定摘要，升级时需重新验证。Redis 只连接容器内部网络；统计服务只向宿主机 `127.0.0.1:18080` 监听，未直接开放到公网。

完成 VPN/防火墙核查后，Ubuntu 24.04 可从系统仓库安装所需组件（已有的 Nginx 保留）：

```sh
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 certbot
sudo systemctl enable --now docker
sudo docker compose version
```

下文 Docker 命令需要 root 或相应权限；不通过将 Docker socket 开放给所有用户来解决权限问题。

复制本目录到 VPS 的独立目录，例如 `/opt/stile-page-views`。在该目录生成仅本机可读的 `.env`，已有文件时命令会拒绝覆盖：

```sh
python3 - <<'PY'
import os
from pathlib import Path
import secrets

fd = os.open('.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as output:
    output.write('STATS_DOMAIN=stats.stile.cc\nSTATS_LOCAL_PORT=18080\n')
    output.write('BSZ_SECRET=' + secrets.token_urlsafe(32) + '\n')
PY
docker compose config --quiet
```

`.env` 含密钥，不要提交到 Git 或粘贴到聊天。需要更换域名或本机端口时修改该文件；CORS 和请求域名目前限定为网站 `https://stile.cc`。

## 导入现有计数

迁移安排在业务低峰期。先用原接口获取尽可能新的完整只读备份；查询失败时保留最近成功备份并明确其时间。最近成功备份之后的计数不能凭空补齐。

1. 保留 `_data/page_views_history.json`，其中的 Google 历史基数继续由前端添加。
2. 只启动新的 Redis，保持新的统计服务尚未接收浏览量。
3. 由备份文件生成导入指令。脚本只导出顶层原始 `site_pv` / `counts`，不会把 `history` 再加一次。

在仓库所在电脑生成文件（`page-views.json` 取自 `page-views-backups` 分支的最近成功备份）：

```sh
python3 _scripts/prepare_page_views_seed.py \
  --snapshot page-views.json --site https://stile.cc --output seed.resp
```

将 `seed.resp` 复制到 VPS 的部署目录，再执行：

```sh
docker compose up -d --wait redis
docker compose exec -T redis redis-cli --pipe < seed.resp
docker compose up -d --wait busuanzi
curl --fail --silent --show-error \
  -H 'x-bsz-referer: https://stile.cc/' http://127.0.0.1:18080/api
```

导入使用原子 Lua 指令：目标为空时初始化；数据完全一致时重复运行不修改；目标已有不同计数时拒绝导入。不会将生产计数重置为备份值。务必检查 `redis-cli --pipe` 的退出状态和输出中的 `errors: 0`。

迁移前后使用文章的真实中文路径校验读数。UV 并未备份，不导入或估算历史 UV。本网站只展示 PV。

## HTTPS 与 Cloudflare

### 当前主机：复用 Nginx 1.24

为 `stats.stile.cc` 添加指向 VPS 的 A 记录，首次签发证书时设为“仅 DNS”。安装前检查不存在同名的 Nginx 站点，也不存在占用本机 18080 的其他服务，并确认 80/443 当前由 Nginx 监听。若 443 被 VPN 直接占用，不增加 Nginx 的 443 监听，也不挪动 VPN 端口；改用 Tunnel 接本机入口。以下步骤仅适用于 Nginx 已负责 80/443 的情况，只新增站点，不停止 Nginx，也不启用 Compose 的 `https` profile。

```sh
sudo install -d -m 0755 /var/www/stile-stats-acme
sudo install -m 0644 nginx-http-bootstrap.conf /etc/nginx/sites-available/stile-stats
sudo ln -s /etc/nginx/sites-available/stile-stats /etc/nginx/sites-enabled/stile-stats
sudo nginx -t && sudo systemctl reload nginx
```

这份首次签发配置只提供 ACME 验证文件。确认该域名 HTTP 验证路径可达后签发证书，联系邮箱使用站点维护者的邮箱：

```sh
sudo certbot certonly --webroot -w /var/www/stile-stats-acme \
  -d stats.stile.cc --cert-name stats.stile.cc --agree-tos --email YOUR_EMAIL
```

证书签发成功、统计服务及原始计数验证通过后，将本目录的 `nginx.conf` 安装为该站点配置，再验证并平滑加载：

```sh
sudo install -m 0644 nginx.conf /etc/nginx/sites-available/stile-stats
sudo nginx -t && sudo systemctl reload nginx
```

配置默认只监听 IPv4。只有 VPS 的 IPv6、AAAA 记录和 Nginx IPv6 监听都实际可用，才发布 AAAA。TLS 使用真实证书，不用 Flexible 模式。

验证 HTTPS 后再开启 Cloudflare 代理，使用 **Full (strict)**；对 `stats.stile.cc/api` 设置绕过缓存，避免全站“缓存所有内容”规则覆盖该接口，也不为公开统计 API 设置登录页或交互式挑战。Nginx 单独处理预检，限制来源和文章域名，隐藏上游的重复 CORS 头并禁止自动重发写入请求。

启用并检查 `certbot.timer`。为证书续期配置 deploy hook，内容为 `nginx -t && systemctl reload nginx`，以便平滑加载续期证书；执行 hook 前保留原有站点的续期设置。

### 其他没有反向代理的主机

仅当主机的 80/443 端口空闲且没有现成入口时，才使用附带的 Caddy：

1. 为 `stats.stile.cc` 添加指向 VPS 的 A 记录；只有实际配置 IPv6 才添加 AAAA。初次签发证书时先设为“仅 DNS”，保证 80/443 可达。
2. 启动 `docker compose --profile https up -d --wait`，检查 Caddy 日志和 HTTPS 证书。
3. 确认源站 HTTPS 正常后开启 Cloudflare 代理，SSL/TLS 模式用 **Full (strict)**。
4. 对 `stats.stile.cc/api` 设置绕过缓存，避免“缓存所有内容”的全站规则覆盖统计接口。该接口供所有访客使用，不应套用需要登录的 Cloudflare Access 页面或交互式挑战。
5. Caddy 只转发 `GET` / `POST /api`、必要的预检及健康检查；读数响应设置 `Cache-Control: no-store`，只接受本网站的文章地址。

如果使用其他已有反向代理，保持现有入口，由它反代 `127.0.0.1:18080`，不启用 `https` profile；复用附带配置的不缓存、CORS 和路由限制。不要为了部署统计服务停止已有网站。

如果使用 Tunnel，也不启用 `https` profile。宿主机上运行的 cloudflared 可连接 `http://127.0.0.1:18080`，将公开主机名设置为 `stats.stile.cc`；若 cloudflared 在容器内运行，需接入同一 Docker 网络并使用 `http://busuanzi:8080`，不能使用容器自己的 `localhost`。在 Cloudflare 配置只公开统计接口及不缓存规则；隧道凭据放在服务器配置中。

## 验证后切换

先从 VPS、日常使用的手机网络及其他可用网络测试只读请求、CORS 预检和延迟；随后在新服务测试一次 POST，确认只增加一次。测试产生的计数必须使用独立测试站点，或明确记录测试对线上计数的影响。

新服务验证通过后，同步切换 `_config.yml` 的 `page_views_api`、发布用回退快照的 `api` 字段和备份分支中的新服务快照。快照必须匹配新接口，仍只含原始计数；历史基数不变。网站构建会从备份分支加载快照，因此只修改主分支快照不足以完成切换。切换后核对文章、页脚、故障回退和下一次 GitHub 备份，再观察旧接口切换期间的增量，避免遗漏或重复添加。

## 保存与恢复

Redis 的 AOF 每秒同步到独立 Docker 数据卷，正常重启或重建容器不会清空数据；主机突然断电仍可能丢失最近约一秒的写入。不要使用 `docker compose down -v`，该参数会删除数据卷。

继续保留现有 GitHub 每日只读备份，避免只在 VPS 同一块磁盘保存副本。GitHub 备份必须检查是否成功；失败不会更新上次有效记录。需要完整 Redis 备份时可执行：

```sh
docker compose exec -T redis redis-cli --rdb /data/manual-backup.rdb
docker compose cp redis:/data/manual-backup.rdb ./manual-backup.rdb
```

将备份传到其他设备保存；`manual-backup.rdb` 包含 Redis 全部数据。需要重建时优先使用经过验证的最新备份恢复到新的空实例，再进行读数校验，不在接收请求的实例上直接覆盖数据。
