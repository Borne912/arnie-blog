#!/usr/bin/env bash
# Ubuntu 24.04 x86_64 首次安装。安装后不登录、不加入 Tailnet。
# 入网前必须单独核对访问策略，用户态模式可能转发到本机监听的端口。
# 官方安装源：https://pkgs.tailscale.com/stable/#ubuntu-noble
# 用户态模式：https://tailscale.com/docs/concepts/userspace-networking
set -euo pipefail

stile_mode="${1:---check}"
case "$stile_mode" in
  --check|--install) ;;
  *) printf 'Usage: bash setup-tailnet.sh [--check|--install]\n' >&2; exit 64 ;;
esac
[[ $# -le 1 ]] || exit 64

stile_fail() { printf '停止：%s\n' "$*" >&2; exit 1; }
[[ -r /etc/os-release ]] || stile_fail '未找到系统版本信息。'
# shellcheck disable=SC1091
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] ||
  stile_fail '此脚本只适用于已确认的 Ubuntu 24.04 / x86_64 VPS。'
for stile_command in curl python3 ip systemctl apt-get dpkg-query cmp install mktemp; do
  command -v "$stile_command" >/dev/null || stile_fail "缺少命令 $stile_command；尚未修改系统。"
done
[[ -r /etc/ssh/ssh_host_ed25519_key.pub ]] || stile_fail '未找到可读取的服务器 Ed25519 公钥，请先核对 SSH 主机密钥。'

if command -v tailscale >/dev/null || command -v tailscaled >/dev/null ||
   [[ -e /etc/default/tailscaled || -e /var/lib/tailscale || -e /etc/apt/sources.list.d/tailscale.list || -e /usr/share/keyrings/tailscale-archive-keyring.gpg ]]; then
  stile_fail '检测到已有 Tailscale 程序或配置；不自动覆盖，请先核对现状。'
fi
systemctl show --property=Version --value >/dev/null || stile_fail '系统不是可用的 systemd 主机。'
python3 - <<'PY'
import socket
try:
    with socket.create_connection(('127.0.0.1', 2912), timeout=3) as conn:
        if not conn.recv(256).startswith(b'SSH-'):
            raise OSError('unexpected service banner')
except OSError as error:
    raise SystemExit('本机 127.0.0.1:2912 无法访问 SSH；尚未安装或修改网络：' + str(error))
PY
printf '检查通过：Ubuntu 24.04 x86_64，新的 Tailscale 安装，本机 SSH 2912 可达。\n'
[[ "$stile_mode" == --install ]] || { printf '只读检查结束。安装命令：sudo bash setup-tailnet.sh --install\n'; exit 0; }
[[ "$EUID" -eq 0 ]] || stile_fail '安装需要 sudo；尚未修改系统。'

umask 077
stile_backup_dir="$(mktemp -d /var/backups/stile-tailnet.XXXXXX)"
printf '本次接入前的记录保存在：%s\n' "$stile_backup_dir"
cat /etc/resolv.conf > "$stile_backup_dir/resolv.conf.before"
python3 - "$stile_backup_dir/default-routes.before.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
keys = ('dst', 'gateway', 'dev', 'metric', 'table', 'prefsrc', 'protocol')
routes = {}
for family in ('-4', '-6'):
    rows = json.loads(subprocess.check_output(['ip', '-j', family, 'route', 'show', 'default']))
    routes[family] = sorted(({k: r[k] for k in keys if k in r} for r in rows), key=lambda r: json.dumps(r, sort_keys=True))
Path(sys.argv[1]).write_text(json.dumps(routes, sort_keys=True))
PY
if command -v iptables-save >/dev/null; then iptables-save > "$stile_backup_dir/iptables.before"; fi
if command -v nft >/dev/null; then nft list ruleset > "$stile_backup_dir/nftables.before"; fi
systemctl list-units --type=service --state=running --no-pager > "$stile_backup_dir/services.before"

curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 \
  https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg \
  --output "$stile_backup_dir/tailscale-keyring.gpg"
[[ -s "$stile_backup_dir/tailscale-keyring.gpg" ]] || stile_fail '软件源密钥下载为空。'
install -d -m 0755 /usr/share/keyrings /etc/apt/sources.list.d
install -m 0644 "$stile_backup_dir/tailscale-keyring.gpg" /usr/share/keyrings/tailscale-archive-keyring.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/ubuntu noble main' \
  > "$stile_backup_dir/tailscale.list"
install -m 0644 "$stile_backup_dir/tailscale.list" /etc/apt/sources.list.d/tailscale.list

# 在安装包首次启动服务前预设用户态模式；dpkg 保留这份配置。
printf '%s\n' 'PORT="0"' 'FLAGS="--tun=userspace-networking"' > "$stile_backup_dir/tailscaled.default"
install -m 0644 "$stile_backup_dir/tailscaled.default" /etc/default/tailscaled
apt-get update
NEEDRESTART_MODE=l DEBIAN_FRONTEND=noninteractive apt-get --no-upgrade --no-remove --no-install-recommends \
  -o Dpkg::Options::=--force-confold install -y tailscale
if ! cmp -s /etc/default/tailscaled "$stile_backup_dir/tailscaled.default"; then
  systemctl stop tailscaled || true
  stile_fail '安装后启动配置与预设不符；已停止新服务，请核对。'
fi
systemctl enable --now tailscaled
stile_daemon_pid="$(systemctl show tailscaled --property=MainPID --value)"
if ! python3 - "$stile_daemon_pid" <<'PY'
from pathlib import Path
import sys
pid = int(sys.argv[1])
if pid <= 0 or b'--tun=userspace-networking' not in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0'):
    raise SystemExit('服务未以预设的用户态模式运行。')
PY
then
  systemctl stop tailscaled || true
  stile_fail '已停止新服务，未开始账号登录。'
fi

if ! cmp -s /etc/resolv.conf "$stile_backup_dir/resolv.conf.before"; then
  systemctl stop tailscaled || true
  stile_fail "检测到 DNS 文件变化，已停止新服务；请核对 $stile_backup_dir，未自动覆盖网络配置。"
fi
if ! python3 - "$stile_backup_dir/default-routes.before.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
keys = ('dst', 'gateway', 'dev', 'metric', 'table', 'prefsrc', 'protocol')
routes = {}
for family in ('-4', '-6'):
    rows = json.loads(subprocess.check_output(['ip', '-j', family, 'route', 'show', 'default']))
    routes[family] = sorted(({k: r[k] for k in keys if k in r} for r in rows), key=lambda r: json.dumps(r, sort_keys=True))
if routes != json.loads(Path(sys.argv[1]).read_text()):
    raise SystemExit('检测到默认路由变化。')
PY
then
  systemctl stop tailscaled || true
  stile_fail "已停止新服务；请核对 $stile_backup_dir，未自动恢复或覆盖路由。"
fi

printf '\n安装完成，尚未登录或加入任何 Tailnet。默认路由及 DNS 核对通过。\n'
printf '入网前先核对 Tailnet 访问策略：仅允许指定管理设备连接 VPS 的 TCP 2912，限制 VPS 和部署环境访问其他设备。\n'
printf '仅添加窄规则不能覆盖已有的宽规则；用户态模式还可能转发到本机监听的管理端口。\n'
printf '策略及设备身份核对完成后再单独安排入网。服务器 SSH 公钥（非私钥）：\n'
cat /etc/ssh/ssh_host_ed25519_key.pub
printf '\n未修改现有 SSH/Xray/Nginx 配置。后续入网仍使用 SSH 原端口 2912，保持 Tailscale SSH 关闭。\n'
