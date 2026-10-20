#!/usr/bin/env bash
# 已保存隔离策略后的首次安装与接入入口；在 VPS 上通过 sudo 运行。
set -euo pipefail
[[ "$EUID" -eq 0 ]] || { printf '请通过 sudo 运行。\n' >&2; exit 1; }
[[ $# -eq 0 ]] || { printf '此首次接入入口不接收参数。\n' >&2; exit 64; }
stile_bundle_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$stile_bundle_dir/setup-tailnet.sh" --install
bash "$stile_bundle_dir/join-tailnet.sh" --join
