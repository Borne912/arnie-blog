"""Install the pinned page-view service on the authorized Ubuntu VPS.

Executed by the user through their local SSH client. No remote shell,
credentials, tunnel, Docker daemon, or firewall configuration is created here.
"""

import concurrent.futures
from datetime import datetime, timezone
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import platform
import pwd
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener, urlopen


PACKAGE = Path(__file__).resolve().parent
INSTALL = Path('/opt/stile-page-views')
DATA = Path('/var/lib/stile-page-views')
SETTINGS = Path('/etc/stile-page-views')
NGINX = Path('/etc/nginx/conf.d/stile-page-views.conf')
WEBROOT = Path('/var/www/stile-stats-acme')
UNIT_NAMES = ('stile-page-views-redis.service', 'stile-page-views.service')
BINARY_SHA256 = 'e135ee6f2f0ffcd7aeda1c79464fc364fe869ece2d85259951b76d1bb7d901b0'
PRIVATE = build_opener(ProxyHandler({}))  # Only used with literal loopback URLs.


def run(args, capture=True, timeout=60, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=capture, timeout=timeout, **kwargs)


def active(name):
    return subprocess.run(['systemctl', 'is-active', '--quiet', name], capture_output=True).returncode == 0


def atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content.encode() if isinstance(content, str) else content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def settings():
    value = json.loads((PACKAGE / 'deploy-settings.json').read_text())
    if value.get('domain') != 'stats.stile.cc' or value.get('site') != 'https://stile.cc' or value.get('expected_ipv4') != '199.168.136.75':
        raise ValueError('Deployment settings differ from the authorized site/server')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value.get('email', '')):
        raise ValueError('A certificate contact email is required')
    return value


def verify_package():
    manifest = json.loads((PACKAGE / 'payload-sha256.json').read_text())
    required = {'app/busuanzi', 'app/config.yaml', 'native/redis.conf', 'prepare_page_views_seed.py', 'nginx.conf', 'nginx-http-bootstrap.conf', 'page-views.json', 'deploy-settings.json'}
    if not required.issubset(manifest):
        raise ValueError('Incomplete deployment package')
    for relative, expected in manifest.items():
        path = PACKAGE / relative
        if not path.resolve().is_relative_to(PACKAGE) or not path.is_file() or path.is_symlink():
            raise ValueError('Invalid package path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Package checksum failed: ' + relative)
    if manifest['app/busuanzi'] != BINARY_SHA256:
        raise ValueError('Unexpected statistics binary')


def seed_module():
    spec = importlib.util.spec_from_file_location('stile_seed', PACKAGE / 'prepare_page_views_seed.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_snapshot(value):
    seed_module().command(value, 'https://stile.cc')
    return value


def managed():
    marker = INSTALL / 'managed.json'
    if marker.exists():
        if json.loads(marker.read_text()).get('deployment') != 'native-v1':
            raise ValueError('An unrelated deployment already uses the install directory')
        return True
    if INSTALL.exists() and any(INSTALL.iterdir()):
        raise ValueError('Existing unrecognized install directory; refusing to overwrite')
    return False


def names_in_nginx(text):
    without_comments = '\n'.join(line.split('#', 1)[0] for line in text.splitlines())
    return {name.lower() for declaration in re.findall(r'\bserver_name\s+([^;]+);', without_comments) for name in declaration.split()}


def preflight():
    if os.geteuid() != 0:
        raise ValueError('Run through sudo on the VPS')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"') != 'ubuntu' or release.get('VERSION_ID', '').strip('"') != '24.04' or platform.machine() != 'x86_64':
        raise ValueError('This package requires Ubuntu 24.04 x86_64')
    for command in ('systemctl', 'nginx', 'ip', 'apt-get', 'useradd', 'ss', 'pgrep', 'dpkg-query'):
        if shutil.which(command) is None:
            raise ValueError('Required command is missing: ' + command)
    own = managed()
    for username in ('stile-stats', 'stile-redis'):
        try:
            pwd.getpwnam(username)
        except KeyError:
            continue
        if not own:
            raise ValueError('A service account already exists: ' + username)
    if not active('nginx'):
        raise ValueError('Existing nginx service is not running')
    config = run(['nginx', '-T']).stdout
    if not own and ('stats.stile.cc' in names_in_nginx(config) or NGINX.exists()):
        raise ValueError('A statistics virtual host already exists; refusing to overwrite it')
    if not re.search(r'\binclude\s+/etc/nginx/conf[.]d/[*][.]conf\s*;', config):
        raise ValueError('Expected nginx conf.d include is missing; manual adaptation is needed')
    if not re.search(r'\blisten\s+(?:0[.]0[.]0[.]0:)?443\s+[^;]*\bssl\b[^;]*;', config):
        raise ValueError('No existing nginx HTTPS listener on 443 was found')
    if not own:
        for path in (SETTINGS, DATA):
            if path.exists():
                raise ValueError('An unrecognized service data/config path exists: ' + str(path))
        for name in UNIT_NAMES:
            if Path('/etc/systemd/system', name).exists():
                raise ValueError('An existing systemd unit would be overwritten: ' + name)
        for port in (18080, 16379):
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', port))
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(memory['MemAvailable'].split()[0]) * 1024
    free_disk = shutil.disk_usage('/').free
    if not own and (available < 180 * 1024**2 or free_disk < 256 * 1024**2):
        raise ValueError('Insufficient available memory or disk for this installation')
    with socket.create_connection(('127.0.0.1', 2912), timeout=3) as connection:
        if not connection.recv(256).startswith(b'SSH-'):
            raise ValueError('Expected OpenSSH service on TCP 2912 is unavailable')
    return {'os': 'Ubuntu 24.04', 'architecture': platform.machine(), 'available_memory_mib': available // 1024**2, 'free_disk_mib': free_disk // 1024**2, 'existing_nginx': True, 'managed_installation': own}


def network_snapshot():
    result = {'dns_sha256': hashlib.sha256(Path('/etc/resolv.conf').read_bytes()).hexdigest()}
    keys = ('dst', 'gateway', 'dev', 'metric', 'table', 'prefsrc', 'protocol')
    for family in ('-4', '-6'):
        rows = json.loads(run(['ip', '-j', family, 'route', 'show', 'default']).stdout)
        result[family] = sorted(({key: row[key] for key in keys if key in row} for row in rows), key=lambda row: json.dumps(row, sort_keys=True))
    for program in ('xray', 'v2ray'):
        process = subprocess.run(['pgrep', '-x', program], capture_output=True, text=True)
        result[program] = sorted(process.stdout.split())
    return result


def api(reference, method='GET', endpoint='http://127.0.0.1:18080/api'):
    if not endpoint.startswith('http://127.0.0.1:18080/'):
        raise ValueError('Local API checks must use the literal loopback endpoint')
    request = Request(endpoint, headers={'x-bsz-referer': reference}, method=method)
    with PRIVATE.open(request, timeout=8) as response:
        value = json.load(response)
    data = value.get('data') or {}
    if value.get('success') is not True or any(type(data.get(key)) is not int or data[key] < 0 for key in ('site_pv', 'page_pv')):
        raise ValueError('Invalid statistics API response')
    return data


def refresh_snapshot(previous):
    """Try current raw counts without ever discarding a complete known snapshot."""
    endpoint = previous['api']
    if endpoint != 'https://busuanzi.9420.ltd/api':
        return previous
    urls = iter(previous['counts'])
    results = []

    def read(reference):
        with urlopen(Request(endpoint, headers={'x-bsz-referer': reference, 'Cache-Control': 'no-cache'}), timeout=8) as response:
            value = json.load(response)
        data = value.get('data') or {}
        if value.get('success') is not True or any(type(data.get(key)) is not int or data[key] < 0 for key in ('site_pv', 'page_pv')):
            raise ValueError('Invalid old-provider response')
        if data['page_pv'] < previous['counts'][reference] or data['site_pv'] < previous['site_pv']:
            raise ValueError('Old-provider counter decreased')
        return reference, data

    print('尝试只读更新迁移计数；失败时保留随包的完整备份。', flush=True)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(read, url) for url in (next(urls, None), next(urls, None)) if url}
            while pending:
                complete, pending = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in complete:
                    results.append(future.result())
                    following = next(urls, None)
                    if following:
                        pending.add(pool.submit(read, following))
        candidate = dict(previous, saved_at=datetime.now(timezone.utc).isoformat(), site_pv=max(data['site_pv'] for _, data in results), counts={url: data['page_pv'] for url, data in results})
        checked_snapshot(candidate)
        return candidate
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        print('公共接口未提供完整的新记录，继续使用备份时间：' + previous['saved_at'], flush=True)
        return previous


def wait_api():
    for _ in range(25):
        try:
            return api('https://stile.cc/')
        except (OSError, ValueError):
            time.sleep(0.4)
    raise ValueError('The new local statistics API did not become healthy')


def verify_counts(source):
    current = {}
    site_pv = 0
    for url, expected in source['counts'].items():
        data = api(url)
        if data['page_pv'] < expected or data['site_pv'] < source['site_pv']:
            raise ValueError('Imported counts are below the source snapshot')
        current[url] = data['page_pv']
        site_pv = max(site_pv, data['site_pv'])
    before = api('https://stile.cc/')['site_pv']
    qa_url = 'https://stile-native-qa.invalid/deployment-check/'
    qa_before = api(qa_url)
    api(qa_url, 'POST')  # Separate site namespace; does not add a real website visit.
    qa_after = api(qa_url)
    if qa_after['site_pv'] != qa_before['site_pv'] + 1 or qa_after['page_pv'] != qa_before['page_pv'] + 1:
        raise ValueError('The isolated write/read verification failed')
    if api('https://stile.cc/')['site_pv'] != before:
        raise ValueError('The production site changed during isolated write verification')
    return {'version': 3, 'saved_at': datetime.now(timezone.utc).isoformat(), 'api': 'https://stats.stile.cc/api', 'site': 'https://stile.cc', 'site_pv': site_pv, 'counts': current}


def service_user(name):
    try:
        return pwd.getpwnam(name)
    except KeyError:
        run(['useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', name])
        return pwd.getpwnam(name)


def install(source):
    fresh = not managed()
    before = network_snapshot()
    default_redis_existed = subprocess.run(['dpkg-query', '-W', '-f=${Status}', 'redis-server'], capture_output=True, text=True).stdout.strip() == 'install ok installed'
    print('安装系统 Redis 和证书工具；保留现有 Nginx。', flush=True)
    environment = dict(os.environ, NEEDRESTART_MODE='l', DEBIAN_FRONTEND='noninteractive')
    run(['apt-get', 'update'], capture=False, timeout=600, env=environment)
    run(['apt-get', '--no-upgrade', '--no-remove', '--no-install-recommends', '-o', 'Dpkg::Options::=--force-confold', 'install', '-y', 'redis-server', 'redis-tools', 'certbot'], capture=False, timeout=600, env=environment)
    if not default_redis_existed:
        run(['systemctl', 'disable', '--now', 'redis-server.service'])
    if fresh:
        INSTALL.mkdir(parents=True, exist_ok=True)
        atomic(INSTALL / 'managed.json', json.dumps({'deployment': 'native-v1', 'binary_sha256': BINARY_SHA256}))
    service_user('stile-stats')
    redis_account = service_user('stile-redis')
    DATA.mkdir(mode=0o755, exist_ok=True)
    INSTALL.chmod(0o755)
    DATA.chmod(0o755)
    redis_data = DATA / 'redis'
    redis_data.mkdir(mode=0o700, exist_ok=True)
    os.chown(redis_data, redis_account.pw_uid, redis_account.pw_gid)
    for component in ('app', 'native'):
        source_tree = PACKAGE / component
        destination_tree = INSTALL / component
        destination_tree.mkdir(mode=0o755, exist_ok=True)
        destination_tree.chmod(0o755)
        for source_file in source_tree.rglob('*'):
            destination_file = destination_tree / source_file.relative_to(source_tree)
            if source_file.is_dir():
                destination_file.mkdir(mode=0o755, exist_ok=True)
                destination_file.chmod(0o755)
            else:
                mode = 0o755 if source_file.name == 'busuanzi' or source_file.suffix == '.sh' else 0o644
                # Replacing the inode also works while the pinned binary is running.
                atomic(destination_file, source_file.read_bytes(), mode)
    SETTINGS.mkdir(mode=0o700, exist_ok=True)
    secret_file = SETTINGS / 'service.env'
    if not secret_file.exists():
        atomic(secret_file, 'BSZ_SECRET=' + secrets.token_urlsafe(48) + '\n')
    for name in UNIT_NAMES:
        atomic(Path('/etc/systemd/system') / name, (PACKAGE / 'native' / name).read_bytes(), 0o644)
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', '--now', UNIT_NAMES[0]])
    for _ in range(25):
        if subprocess.run(['redis-cli', '-h', '127.0.0.1', '-p', '16379', 'ping'], capture_output=True, text=True).stdout.strip() == 'PONG':
            break
        time.sleep(0.4)
    else:
        raise ValueError('The dedicated Redis did not become ready')
    imported = INSTALL / 'seed-source.json'
    if not imported.exists():
        source = refresh_snapshot(source)
        module = seed_module()
        payload = module.encode_resp(module.command(source, 'https://stile.cc'))
        result = subprocess.run(['redis-cli', '-h', '127.0.0.1', '-p', '16379', '--pipe'], input=payload, capture_output=True, timeout=20)
        if result.returncode != 0 or b'errors: 0,' not in result.stdout:
            raise ValueError('Raw-count import refused; existing counters were not reset')
        atomic(imported, json.dumps(source, ensure_ascii=False, indent=2))
    else:
        source = checked_snapshot(json.loads(imported.read_text()))
    run(['systemctl', 'enable', '--now', UNIT_NAMES[1]])
    wait_api()
    result = verify_counts(source)
    if network_snapshot() != before:
        for name in reversed(UNIT_NAMES):
            run(['systemctl', 'stop', name])
        raise ValueError('Original DNS/default routes or proxy processes changed; new services stopped for review')
    print('本机计数服务、42 篇计数导入及独立站点写入验证通过。', flush=True)
    return result


def nginx_restore(previous):
    if previous is None:
        NGINX.unlink(missing_ok=True)
    else:
        atomic(NGINX, previous, 0o644)
    run(['nginx', '-t'])
    run(['systemctl', 'reload', 'nginx'])


def nginx_apply(content):
    previous = NGINX.read_bytes() if NGINX.exists() else None
    atomic(NGINX, content, 0o644)
    try:
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
    except BaseException:
        nginx_restore(previous)
        raise


def local_https(method='GET', path='/api', headers=None):
    context = ssl.create_default_context()
    connection = http.client.HTTPSConnection('stats.stile.cc', context=context, timeout=10)
    connection.sock = context.wrap_socket(socket.create_connection(('127.0.0.1', 443), timeout=5), server_hostname='stats.stile.cc')
    try:
        connection.request(method, path, headers=headers or {'x-bsz-referer': 'https://stile.cc/', 'Origin': 'https://stile.cc'})
        response = connection.getresponse()
        return response.status, response.getheaders(), response.read()
    finally:
        connection.close()


def https(config):
    if not managed() or not all(active(name) for name in UNIT_NAMES):
        raise ValueError('Install and verify the local services first')
    certificate = Path('/etc/letsencrypt/live/stats.stile.cc/fullchain.pem')
    if not certificate.exists():
        addresses = {item[4][0] for item in socket.getaddrinfo(config['domain'], 80, socket.AF_INET, socket.SOCK_STREAM)}
        if addresses != {config['expected_ipv4']}:
            raise ValueError('DNS A record must point only to the VPS before first certificate issuance')
        try:
            ipv6 = socket.getaddrinfo(config['domain'], 80, socket.AF_INET6, socket.SOCK_STREAM)
        except socket.gaierror:
            ipv6 = []
        if ipv6:
            raise ValueError('Unexpected AAAA record; this deployment publishes only IPv4')
    previous = NGINX.read_bytes() if NGINX.exists() else None
    try:
        WEBROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
        if not certificate.exists():
            nginx_apply((PACKAGE / 'nginx-http-bootstrap.conf').read_bytes())
            run(['certbot', 'certonly', '--non-interactive', '--webroot', '-w', str(WEBROOT), '-d', config['domain'], '--cert-name', config['domain'], '--agree-tos', '--email', config['email'], '--keep-until-expiring'], capture=False, timeout=300)
        nginx_apply((PACKAGE / 'nginx.conf').read_bytes())
        for attempt in range(15):
            try:
                status, headers, body = local_https()
                if status == 200:
                    break
            except (OSError, http.client.HTTPException):
                if attempt == 14:
                    raise
            time.sleep(0.2)
        else:
            raise ValueError('The new nginx HTTPS virtual host did not become ready')
        data = json.loads(body)
        normalized_headers = [(name.lower(), value) for name, value in headers]
        if status != 200 or data.get('success') is not True or [value for name, value in normalized_headers if name == 'access-control-allow-origin'] != ['https://stile.cc']:
            raise ValueError('Verified HTTPS/CORS check failed')
        if dict(normalized_headers).get('cache-control') != 'no-store':
            raise ValueError('Statistics responses must not be cached')
        status, _, _ = local_https('OPTIONS', headers={'Origin': 'https://stile.cc', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'x-bsz-referer'})
        if status != 204:
            raise ValueError('CORS preflight failed')
        for method, request_headers, expected in (
            ('GET', {'Origin': 'https://example.invalid', 'x-bsz-referer': 'https://stile.cc/'}, 403),
            ('GET', {'Origin': 'https://stile.cc', 'x-bsz-referer': 'https://example.invalid/'}, 400),
            ('DELETE', {'Origin': 'https://stile.cc', 'x-bsz-referer': 'https://stile.cc/'}, 405),
        ):
            if local_https(method, headers=request_headers)[0] != expected:
                raise ValueError('HTTPS request filtering verification failed')
        atomic(Path('/etc/letsencrypt/renewal-hooks/deploy/stile-page-views'), (PACKAGE / 'native/certbot-reload.sh').read_bytes(), 0o755)
        run(['systemctl', 'enable', '--now', 'certbot.timer'])
    except BaseException:
        nginx_restore(previous)
        raise
    print('HTTPS 证书、CORS、不缓存及请求限制检查通过。', flush=True)


def report(action, check, snapshot=None, success=True, error=None):
    value = {'version': 1, 'action': action, 'success': success, 'time': datetime.now(timezone.utc).isoformat(), 'check': check, 'error': error, 'api': 'https://stats.stile.cc/api'}
    if snapshot is not None:
        value['raw_snapshot'] = snapshot
    source = INSTALL / 'seed-source.json'
    if source.exists():
        previous = json.loads(source.read_text())
        value['imported_source'] = {'api': previous['api'], 'saved_at': previous['saved_at'], 'site_pv': previous['site_pv']}
    target = PACKAGE / 'deployment-report.json'
    atomic(target, json.dumps(value, ensure_ascii=False, indent=2))
    user = os.environ.get('SUDO_USER')
    if user == 'Borne':
        account = pwd.getpwnam(user)
        os.chown(target, account.pw_uid, account.pw_gid)
    print('STILE_DEPLOY_REPORT ' + json.dumps({key: data for key, data in value.items() if key != 'raw_snapshot'}, ensure_ascii=False), flush=True)


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else 'check'
    if action not in ('check', 'install', 'https', 'report'):
        raise ValueError('Unknown action')
    verify_package()
    config = settings()
    source = checked_snapshot(json.loads((PACKAGE / 'page-views.json').read_text()))
    check = preflight()
    snapshot = None
    try:
        if action == 'install':
            snapshot = install(source)
            https(config)
        elif action == 'https':
            https(config)
            snapshot = verify_counts(checked_snapshot(json.loads((INSTALL / 'seed-source.json').read_text())))
        elif action == 'report':
            snapshot = verify_counts(checked_snapshot(json.loads((INSTALL / 'seed-source.json').read_text())))
        report(action, check, snapshot)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report(action, check, snapshot, success=False, error=str(error))
        raise


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('停止：' + str(error), file=sys.stderr)
        sys.exit(1)
