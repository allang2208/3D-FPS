"""Acquire only the user-selected reference interval for local sound editing."""
from pathlib import Path
import hashlib
import json
import subprocess
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
raw = (HERE / 'download-info.json').read_bytes()
info = json.loads(raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'))
formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
chosen = max(formats, key=lambda f: (f.get('abr') or 0, int(f.get('format_id') or 0)))
headers = {**info.get('http_headers', {}), **chosen.get('http_headers', {})}
headers['Referer'] = 'https://www.bilibili.com/video/BV1jGdDBkEkc/'
out = HERE / 'reference_32_49.wav'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y',
                '-headers', ''.join(f'{k}: {v}\r\n' for k, v in headers.items()),
                '-ss', '32', '-i', chosen['url'], '-t', '17', '-vn',
                '-ar', '48000', '-ac', '2', '-c:a', 'pcm_f32le', str(out)], check=True)
source = {
    'url': info['webpage_url'], 'id': info['id'], 'title': info['title'],
    'uploader': info.get('uploader'), 'reference_interval_seconds': [32, 49],
    'format_id': chosen['format_id'], 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'rights': 'User-requested local video SFX excerpts. No asset redistribution license supplied; not CC0.',
    'purpose': 'Short draw/release samples for the requested local bow replacement.',
}
(HERE / 'source.json').write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'audio': str(out), 'interval': [32, 49], 'bytes': out.stat().st_size}))
