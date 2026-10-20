# 从 Mac 或 Windows 部署到 BWG

当前选择是 BWG VPS 原生运行不蒜子 v2.8.8 和独立 Redis，通过 systemd 启动和恢复服务，复用已有 Nginx。Mac 或 Windows 只负责 SSH 上传并执行安装，不承担网站或统计服务的运行，不需要 Docker、Python、WSL 或 Tailscale，也无需持续开机。

完整的任务部署包另附经过校验的 Linux amd64 程序、Apache 2.0 许可证、42 篇文章的原始计数备份和证书联系设置。仓库中的源码目录本身不是完整部署包，不应直接运行。

## Mac 执行

在 Mac 下载并完整解压任务提供的 `stile-page-views-deploy.zip` 到下载目录，然后执行：

```sh
bash ~/Downloads/stile-page-views-deploy/deploy-from-mac.sh --install
```

脚本固定核对 `BWG` 是本次授权的主机、用户名和端口，使用已经信任的服务器 SSH 身份，不关闭主机密钥校验。

## Windows 执行

使用 Windows 10/11 的 PowerShell 和 OpenSSH 客户端。先在 PowerShell 中确认这台 Windows 电脑能登录 VPS：

```powershell
ssh -p 2912 Borne@199.168.136.75
```

首次连接时核对服务器主机指纹；可与已信任的 Mac 连接看到的指纹核对。使用 Windows 上已有的 SSH 密钥或服务器允许的登录方式，不要把私钥发送到聊天。如果提示找不到 `ssh`，在 Windows 设置的“可选功能”中安装“OpenSSH 客户端”。登录成功后输入 `exit` 返回本地 PowerShell。

下载包含 `deploy-from-windows.ps1` 的 `stile-page-views-deploy-windows.zip`，在 PowerShell 解压到“下载”目录并执行：

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\stile-page-views-deploy-windows.zip" -DestinationPath "$env:USERPROFILE\Downloads" -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\stile-page-views-deploy\deploy-from-windows.ps1" -Action install -Direct
```

`-Direct` 固定连接本次 VPS 的主机、用户和 SSH 2912 端口，无需 Windows 配置 `BWG` 别名。Mac 的 SSH 配置和密钥不会自动出现在 Windows。如果 Windows 已有正确的 `BWG` 别名，也可省略 `-Direct`。脚本始终校验实际目标并保持 SSH 主机密钥校验。`-ExecutionPolicy Bypass` 只应用于这次 PowerShell 进程，不修改系统的执行策略；若组织策略禁止运行脚本，先处理该限制。

可将 `-Action install` 改为 `-Action check`、`-Action https` 或 `-Action report`，分别对应只检查、恢复 HTTPS 阶段和导出报告。不带 `-Action` 时默认只检查。只需普通 PowerShell，VPS 提示 sudo 时在终端输入 VPS 密码。

## 安装结果

出现 sudo 提示时，在当前终端输入 VPS 用户的密码。密码、SSH 私钥和 Redis 身份密钥均不需要发送到聊天。

首次运行会检查 Ubuntu 24.04 x86_64、资源、现有 Nginx、SSH、本机端口及是否存在冲突；安装系统 Redis 和 certbot；部署两个独立服务并导入计数；使用 `stats.stile.cc` 的仅 DNS A 记录申请证书；新增独立站点并通过 `nginx -t` 后平滑加载；最后从当前电脑只读验证公开 HTTPS。

提供部署包目录中的 `deployment-report.json` 和终端末尾的 HTTPS 响应，供网站切换前核对。安装脚本不会自行更改博客的线上接口；核对报告后需同步切换网站配置与备份来源。

## 中断与恢复

不带选项或使用 `--check` 时只检查服务器条件并输出报告，不安装软件或改动服务配置。其他入口为：

```sh
# 本机服务已安装，仅恢复证书及 Nginx 阶段
bash ~/Downloads/stile-page-views-deploy/deploy-from-mac.sh --https

# 导出当前计数和检查报告
bash ~/Downloads/stile-page-views-deploy/deploy-from-mac.sh --report
```

`--report` 通过独立测试站点验证一次写入，不增加真实网站的访问量。首次安装同样这样验证；所有文章读数检查均为只读请求。

证书签发或 HTTPS 检查失败时，脚本恢复这次操作前的统计站点配置，保留已经成功导入的计数。重复执行 `--install` 会沿用导入检查点，保留安装后产生的新访问；不会用旧备份重置现有数据。首次导入也拒绝覆盖不一致的 Redis 计数。若报告说明现有服务、配置或资源冲突，请先核对错误，不要删除检查或清空数据重试。

## 服务与数据

| 项目 | 位置或设置 |
| --- | --- |
| 程序与配置 | `/opt/stile-page-views` |
| 原始导入检查点 | `/opt/stile-page-views/seed-source.json` |
| 统计服务 | `stile-page-views.service`，仅监听 `127.0.0.1:18080` |
| Redis 服务 | `stile-page-views-redis.service`，仅监听 `127.0.0.1:16379` |
| Redis AOF 数据 | `/var/lib/stile-page-views/redis` |
| 本机生成的身份密钥 | `/etc/stile-page-views/service.env`，仅 root 可读 |
| 新增 Nginx 配置 | `/etc/nginx/conf.d/stile-page-views.conf` |
| 证书及自动续期 | certbot 的 `stats.stile.cc` 证书、`certbot.timer` 与本站专用 reload hook |

两个服务各设 128 MiB 内存上限；这不包含系统和已有应用。Redis 配置 64 MiB 数据上限且禁止逐出计数键。脚本保留现有 Nginx 主配置、SSH、Xray/V2Ray 和网络配置，仅在自己的站点配置通过验证后平滑 reload Nginx。系统软件安装使用保留现有配置的非交互模式，将 needrestart 设为仅报告模式。

统计程序来自固定版本的上游镜像 `xcsoft/busuanzi:v2.8.8@sha256:2edf1ff096cd62ec641087a9cbc09fb88ecb4fa91e79c845526817220c351d01`，解出的静态 Linux amd64 程序 SHA-256 为 `e135ee6f2f0ffcd7aeda1c79464fc364fe869ece2d85259951b76d1bb7d901b0`。不在 VPS 上安装或启动 Docker。程序源码和许可证：[soxft/busuanzi v2.8.8](https://github.com/soxft/busuanzi/tree/v2.8.8)。部署包的 `payload-sha256.json` 用于检测缺失或损坏，不代替可信的下载来源。

## 迁移边界与备份

部署包只向 Redis 导入公共接口的原始 PV。Google 恢复的固定历史基数保留在博客中，继续显示时加一次，不导入 Redis；UV 不做历史补估。首次安装会尝试取得旧接口的新完整备份，失败时使用包内注明时间的完整备份。备份之后未记录的访问可能无法补回。

Redis AOF 每秒同步磁盘，正常服务重启保留计数；突然断电可能损失最近约一秒的写入，VPS 磁盘损坏仍会损失本机数据。完成网站接口和备份分支切换后，继续使用现有 GitHub 每日异地备份，并检查其成功状态。最近一次成功备份后的访问仍有丢失风险。

保持 Cloudflare 为仅 DNS，先完成源站 HTTPS 检查。通过后再开启代理，使用 Full (strict)，让 `/api` 绕过缓存，避免登录页或交互式挑战阻断访客统计。无需为部署启用 Tailscale，也无需执行旧的 Tailnet 接入脚本。

## 已完成的本地验证

在无外网 Ubuntu 24.04 容器中使用实际固定版本程序、Redis 7.0 和 Nginx 1.24，验证了 42 篇原始计数、独立测试站点写入、HTTPS/CORS/缓存策略、重复安装保留新增访问、AOF 重启恢复和原有配置保护。systemd 单元通过 `systemd-analyze verify`。测试使用受信任的测试证书，并模拟 apt、systemctl 和 certbot 命令；真实 VPS 的包安装、systemd 运行、Let's Encrypt 签发和公网连接仍需通过部署报告核对。

Windows 入口使用兼容 Windows PowerShell 5.1 的语法，已在 Linux 上通过 PowerShell 7.4 的 13 项行为模拟，覆盖含空格路径、四种操作、别名和直连、错误目标拒绝、上传失败、安装失败取回报告及 HTTPS 失败。未在真实 Windows 电脑执行。
