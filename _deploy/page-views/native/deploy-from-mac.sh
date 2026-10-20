#!/usr/bin/env bash
# 在已有、已信任的 BWG SSH 配置的 Mac 上运行。Mac 不运行统计服务。
set -euo pipefail
stile_mode="${1:---check}"
case "$stile_mode" in
  --check) stile_action=check ;;
  --install) stile_action=install ;;
  --https) stile_action=https ;;
  --report) stile_action=report ;;
  *) printf 'Usage: bash deploy-from-mac.sh [--check|--install|--https|--report]\n' >&2; exit 64 ;;
esac
[[ $# -le 1 ]] || exit 64
stile_bundle_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$stile_bundle_dir/server.py" && -f "$stile_bundle_dir/deploy-settings.json" ]] || {
  printf '请先完整解压部署包，再运行此脚本。\n' >&2; exit 1;
}
stile_ssh_config="$(ssh -G BWG)"
if ! printf '%s\n' "$stile_ssh_config" | awk '
  $1 == "hostname" { host=$2 }
  $1 == "user" { user=$2 }
  $1 == "port" { port=$2 }
  END { exit !(host == "199.168.136.75" && user == "Borne" && port == "2912") }
'; then
  printf 'BWG 别名与已授权的服务器不符，已停止。\n' >&2; exit 1
fi
ssh -o StrictHostKeyChecking=yes BWG 'install -d -m 0700 ~/stile-page-views-package'
scp -q -r -o StrictHostKeyChecking=yes "$stile_bundle_dir/." BWG:stile-page-views-package/
stile_result=0
ssh -t -o StrictHostKeyChecking=yes BWG "sudo python3 ~/stile-page-views-package/server.py $stile_action" || stile_result=$?
if scp -q -o StrictHostKeyChecking=yes BWG:stile-page-views-package/deployment-report.json "$stile_bundle_dir/deployment-report.json"; then
  printf '\n部署报告：%s/deployment-report.json\n' "$stile_bundle_dir"
fi
if [[ "$stile_result" -ne 0 ]]; then
  printf '部署尚未完成，请保留上方错误和已取得的报告；不要切换网站接口。\n' >&2
  exit "$stile_result"
fi
if [[ "$stile_action" == install || "$stile_action" == https ]]; then
  printf '\n从 Mac 验证公开 HTTPS 统计接口（只读）：\n'
  curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 \
    -H 'x-bsz-referer: https://stile.cc/' -H 'Origin: https://stile.cc' \
    https://stats.stile.cc/api
  printf '\n部署报告已保存为部署包目录中的 deployment-report.json；请提供该文件和上述 HTTPS 响应，供网站切换前核对。\n'
fi
