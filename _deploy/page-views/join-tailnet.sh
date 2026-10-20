#!/usr/bin/env bash
# 在 VPS 上运行；要求已保存隔离策略，且 setup-tailnet.sh 已完成用户态安装。
# --check 只读检查；--join 才进行浏览器登录。不会在云执行环境安装 Tailscale。
set -euo pipefail

stile_mode="${1:---check}"
case "$stile_mode" in
  --check|--join) ;;
  *) printf 'Usage: bash join-tailnet.sh [--check|--join]\n' >&2; exit 64 ;;
esac
[[ $# -le 1 ]] || exit 64
stile_fail() { printf '停止：%s\n' "$*" >&2; exit 1; }
[[ "$EUID" -eq 0 ]] || stile_fail '请通过 sudo 运行，以便核对服务和保存网络快照。'
for stile_command in tailscale python3 ip systemctl cmp mktemp; do
  command -v "$stile_command" >/dev/null || stile_fail "缺少 $stile_command，请先完成首次安装。"
done
[[ -r /etc/ssh/ssh_host_ed25519_key.pub ]] || stile_fail '未找到服务器 SSH 公钥。'
systemctl is-active --quiet tailscaled || stile_fail 'tailscaled 未运行；请先核对安装状态。'
stile_daemon_pid="$(systemctl show tailscaled --property=MainPID --value)"
python3 - "$stile_daemon_pid" <<'PY'
from pathlib import Path
import sys
pid = int(sys.argv[1])
if pid <= 0 or b'--tun=userspace-networking' not in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0'):
    raise SystemExit('拒绝接入：tailscaled 未使用预设的用户态模式。')
PY
stile_join_action="$(python3 - <<'PY'
import json, socket, subprocess
result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
try:
    status = json.loads(result.stdout)
except (ValueError, TypeError):
    raise SystemExit('无法读取 Tailscale 状态；不更改已有身份。')
state = status.get('BackendState')
if state in ('NoState', 'NeedsLogin'):
    action = 'join'
elif state == 'Running' and (status.get('Self') or {}).get('Tags') == ['tag:stile-vps']:
    action = 'verify'
else:
    raise SystemExit('检测到已有身份或未就绪状态；不覆盖，请核对当前 Tailscale 配置。')
with socket.create_connection(('127.0.0.1', 2912), timeout=3) as conn:
    if not conn.recv(256).startswith(b'SSH-'):
        raise SystemExit('本机 TCP 2912 不是 SSH 服务。')
print(action)
PY
)"
printf '检查通过：用户态 Tailscale、本机 SSH 2912，身份状态可用于本次接入。\n'
[[ "$stile_mode" == --join ]] || { printf '只读检查结束。接入命令：sudo bash join-tailnet.sh --join\n'; exit 0; }

umask 077
stile_backup_dir="$(mktemp -d /var/backups/stile-tailnet-join.XXXXXX)"
cat /etc/resolv.conf > "$stile_backup_dir/resolv.conf.before"
stile_snapshot_routes() {
  python3 - "$1" <<'PY'
import json, subprocess, sys
from pathlib import Path
keys = ('dst', 'gateway', 'dev', 'metric', 'table', 'prefsrc', 'protocol')
routes = {}
for family in ('-4', '-6'):
    rows = json.loads(subprocess.check_output(['ip', '-j', family, 'route', 'show', 'default']))
    routes[family] = sorted(({k: r[k] for k in keys if k in r} for r in rows), key=lambda r: json.dumps(r, sort_keys=True))
Path(sys.argv[1]).write_text(json.dumps(routes, sort_keys=True))
PY
}
stile_snapshot_routes "$stile_backup_dir/default-routes.before.json"

stile_join_started=0
stile_cleanup() {
  local stile_exit_code=$?
  if [[ "$stile_exit_code" -ne 0 && "$stile_join_started" -eq 1 ]]; then
    systemctl stop tailscaled || true
    printf '本次接入未通过核对，已停止 Tailscale；网络快照：%s\n' "$stile_backup_dir" >&2
  fi
}
trap stile_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ "$stile_join_action" == join ]]; then
  printf '\n请在浏览器打开随后显示的链接，使用已保存隔离策略的 Tailscale 账号登录。\n'
  stile_join_started=1
  tailscale up --hostname=bwg-stile --advertise-tags=tag:stile-vps \
    --accept-dns=false --accept-routes=false --ssh=false --netfilter-mode=off --timeout=5m
fi

python3 - <<'PY'
import ipaddress, json, socket, subprocess
result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
try:
    status = json.loads(result.stdout)
except (ValueError, TypeError):
    raise SystemExit('无法读取登录后的 Tailscale 状态。')
node = status.get('Self') or {}
if status.get('BackendState') != 'Running' or node.get('Tags') != ['tag:stile-vps']:
    raise SystemExit('身份核对失败：必须且只能具有 tag:stile-vps，且处于 Running 状态。')
addresses = [ipaddress.ip_address(value) for value in (node.get('TailscaleIPs') or status.get('TailscaleIPs') or [])]
v4 = [addr for addr in addresses if addr.version == 4 and addr in ipaddress.ip_network('100.64.0.0/10')]
if len(v4) != 1:
    raise SystemExit('未取得唯一的 Tailscale IPv4 地址。')
with socket.create_connection(('127.0.0.1', 2912), timeout=3) as conn:
    if not conn.recv(256).startswith(b'SSH-'):
        raise SystemExit('接入后本机 SSH 2912 检查失败。')
print('VPS Tailscale IPv4: ' + str(v4[0]))
print('VPS tag: tag:stile-vps')
PY
cmp -s /etc/resolv.conf "$stile_backup_dir/resolv.conf.before" || stile_fail 'DNS 文件发生变化。'
stile_snapshot_routes "$stile_backup_dir/default-routes.after.json"
cmp -s "$stile_backup_dir/default-routes.before.json" "$stile_backup_dir/default-routes.after.json" ||
  stile_fail '默认路由发生变化。'
printf '默认路由、DNS 和本机 SSH 2912 核对通过。服务器 SSH 公钥：\n'
cat /etc/ssh/ssh_host_ed25519_key.pub
printf '服务器端接入完成；云环境还需使用 tag:stile-deploy 并配置此 IPv4 的 /32 TCP 授权。\n'
