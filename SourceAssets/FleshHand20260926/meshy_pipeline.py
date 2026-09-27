"""Task-scoped Meshy production client. Keys and signed URLs never enter records."""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests

ROOT = Path(__file__).resolve().parent
SETTINGS = json.loads((ROOT / 'meshy_settings.json').read_text(encoding='utf-8-sig'))
API = SETTINGS['api_base']
OUT = ROOT / 'Meshy'


def key_from_environment():
    key = os.environ.get('MESHY_API_KEY', '').strip()
    if key:
        return key
    if sys.platform == 'win32':
        import winreg
        for hive, subkey in [
            (winreg.HKEY_CURRENT_USER, 'Environment'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
        ]:
            try:
                with winreg.OpenKey(hive, subkey) as handle:
                    key = str(winreg.QueryValueEx(handle, 'MESHY_API_KEY')[0]).strip()
                if key:
                    return key
            except FileNotFoundError:
                pass
    raise RuntimeError('MESHY_API_KEY is unavailable in process/User/Machine environment.')


def safe(value):
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    if isinstance(value, str):
        if value.startswith('data:'):
            return '[input bytes omitted; see request input paths]'
        if value.startswith(('https://', 'http://')):
            parts = urlsplit(value)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        value = re.sub(r'\?[^\s\)\]\"\x27]+', '?[query-redacted]', value)
        return re.sub(r'msy_[A-Za-z0-9_-]+', '[redacted]', value)
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(safe(value), ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def session():
    client = requests.Session()
    client.trust_env = False
    client.proxies.update({'https': SETTINGS['proxy'], 'http': SETTINGS['proxy']})
    return client


def api(method, endpoint, payload=None):
    try:
        with session() as client:
            response = client.request(method, API + endpoint, json=payload,
                                      headers={'Authorization': 'Bearer ' + key_from_environment()}, timeout=(20, 180))
    except requests.exceptions.ConnectionError:
        if method != 'GET':
            raise
        # Read-only continuation through Windows TLS when OpenSSL is reset.
        # The bearer header is supplied through stdin, never command arguments.
        header = json.dumps('Authorization: Bearer ' + key_from_environment())
        args = ['curl.exe', '--silent', '--show-error', '--fail', '--location',
                '--config', '-', '--proxy', SETTINGS['proxy'],
                '--connect-timeout', '20', '--max-time', '60', API + endpoint]
        result = subprocess.run(args, input='header = ' + header + '\n',
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode in (28, 35, 56):
            args[args.index('--proxy') + 1] = SETTINGS['proxy'].replace('http://', 'socks5h://')
            result = subprocess.run(args, input='header = ' + header + '\n',
                                    capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode in (28, 35, 56):
            args[args.index('--proxy') + 1] = ''
            args.extend(['--noproxy', '*'])
            result = subprocess.run(args, input='header = ' + header + '\n',
                                    capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode:
            raise RuntimeError(f'Meshy status download failed: {safe(result.stderr)}')
        return json.loads(result.stdout)
    if not response.ok:
        raise RuntimeError(f'Meshy HTTP {response.status_code}: {safe(response.text[:800])}')
    return response.json()


def balance(label):
    value = api('GET', '/v1/balance')
    write_json(OUT / f'balance_{label}.json', value)
    print(json.dumps({'balance': value}, ensure_ascii=False), flush=True)
    return value


def data_uri(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def submit(name):
    folder = OUT / name
    receipt = folder / 'task.json'
    request_path = folder / 'request.json'
    if receipt.exists():
        print(json.dumps({'reused': name, **json.loads(receipt.read_text())}), flush=True)
        return
    if request_path.exists():
        raise RuntimeError(f'{name} has a pending submission record without a task id. Recover the existing task before submitting again.')
    config = SETTINGS['assets'][name]
    inputs = [ROOT / p for p in config['images']]
    endpoint = SETTINGS['endpoint']
    payload = {**SETTINGS['common'], **config['options'], 'image_urls': [data_uri(p) for p in inputs]}
    balance('before_' + name)
    write_json(request_path, {'endpoint': endpoint,
                             'parameters': payload,
                             'input_files': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]})
    result = api('POST', endpoint, payload)
    task = {'asset': name, 'task_id': result['result'], 'endpoint': endpoint}
    write_json(receipt, task)
    print(json.dumps({'submitted': task}), flush=True)


def asset_urls(value, trail=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from asset_urls(v, trail + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from asset_urls(v, trail + (str(i),))
    elif isinstance(value, str) and value.startswith('https://'):
        yield trail, value


def download_result(folder, result):
    manifest = []
    allowed = {k: result[k] for k in ('thumbnail_url', 'thumbnail_urls', 'alpha_thumbnail_url', 'model_urls', 'texture_urls', 'result') if k in result}
    # The local DNS currently returns unrelated addresses for assets.meshy.ai.
    # Resolve this download host with DoH, then retain its TLS name through
    # curl --resolve and local-DNS SOCKS. No OS/proxy settings are modified.
    dns_args = ['curl.exe', '--silent', '--show-error', '--fail',
                '--proxy', SETTINGS['proxy'], '--connect-timeout', '10',
                '--max-time', '30',
                'https://dns.google/resolve?name=assets.meshy.ai&type=A']
    dns_result = subprocess.run(dns_args, capture_output=True, text=True,
                                encoding='utf-8', errors='replace')
    cdn_addresses = []
    if dns_result.returncode == 0:
        cdn_addresses = [item['data'] for item in json.loads(dns_result.stdout).get('Answer', [])
                         if item.get('type') == 1]
    with session() as client:
        for trail, url in asset_urls(allowed):
            # Retain the service filenames so OBJ/MTL texture references resolve.
            filename = Path(urlsplit(url).path).name or ('_'.join(trail) + '.bin')
            path = folder / 'downloads' / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                part = path.with_suffix(path.suffix + '.part')
                # The CDN intermittently closes Python/OpenSSL handshakes on
                # this workstation; use the native curl TLS stack for files.
                transfer_args = [
                    'curl.exe', '--silent', '--show-error', '--fail', '--location',
                    '--http1.1', '--tlsv1.2', '--tls-max', '1.2',
                    '--proxy', SETTINGS['proxy'], '--connect-timeout', '20',
                    '--max-time', '600', '--retry', '0',
                    '--output', str(part), url,
                ]
                if urlsplit(url).hostname == 'assets.meshy.ai' and cdn_addresses:
                    transfer_args[transfer_args.index('--proxy') + 1] = SETTINGS['proxy'].replace('http://', 'socks5://')
                    transfer_args.extend(['--resolve', 'assets.meshy.ai:443:' + ','.join(cdn_addresses)])
                transfer = subprocess.run(transfer_args, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if transfer.returncode in (18, 28, 35, 52, 56):
                    # Same local mixed proxy, remote DNS through SOCKS instead
                    # of HTTP CONNECT. No system proxy settings are changed.
                    alternate_args = transfer_args.copy()
                    index = alternate_args.index('--proxy') + 1
                    alternate_args[index] = SETTINGS['proxy'].replace('http://', 'socks5h://')
                    transfer = subprocess.run(alternate_args, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if transfer.returncode in (18, 28, 35, 52, 56):
                    direct_args = transfer_args.copy()
                    direct_args[direct_args.index('--proxy') + 1] = ''
                    direct_args.extend(['--noproxy', '*'])
                    transfer = subprocess.run(direct_args, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if transfer.returncode:
                    failure={'file':filename,'returncode':transfer.returncode,'error':safe(transfer.stderr)}
                    write_json(folder/'download_error.json',failure)
                    print(json.dumps(failure,ensure_ascii=False),flush=True)
                    raise RuntimeError('Asset download failed; sanitized details recorded.')
                part.replace(path)
                print(json.dumps({'downloaded_file':filename,'bytes':path.stat().st_size}),flush=True)
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            manifest.append({'file': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                             'sha256': digest, 'source': safe(url)})
    write_json(folder / 'downloads.json', manifest)
    return len(manifest)


def poll(name, download=True):
    folder = OUT / name
    task = json.loads((folder / 'task.json').read_text(encoding='utf-8'))
    result = api('GET', task['endpoint'] + '/' + task['task_id'])
    write_json(folder / 'response.json', result)
    state = {'asset': name, 'id': task['task_id'], 'status': result['status'], 'progress': result.get('progress')}
    if result['status'] == 'SUCCEEDED' and download:
        state['downloaded'] = download_result(folder, result)
        state['credits'] = result.get('consumed_credits')
    elif result['status'] in ('FAILED', 'CANCELED'):
        state['error'] = safe(result.get('task_error'))
    print(json.dumps(state, ensure_ascii=False), flush=True)
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['balance', 'submit', 'poll', 'watch'])
    args = parser.parse_args()
    if args.command == 'balance':
        balance('current')
    elif args.command == 'submit':
        submit('candidate01')
    elif args.command == 'poll':
        poll('candidate01')
    else:
        while True:
            state = poll('candidate01')
            if state['status'] in ('SUCCEEDED', 'FAILED', 'CANCELED'):
                balance('after_candidate01')
                break
            time.sleep(30)
