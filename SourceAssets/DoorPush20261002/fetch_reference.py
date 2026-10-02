"""Read the supplied public reference into local low-resolution study frames.

No credentials, browser profile or engine access. Signed stream URLs remain
in memory. The original video is never published or stored in this project.
"""
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw
import yt_dlp

P = Path(__file__).resolve().parent
REF = P / 'References'
REF.mkdir(parents=True, exist_ok=True)
URL = 'https://www.bilibili.com/video/BV17HSbBvE3M/'
with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True, 'socket_timeout': 15}) as reader:
    info = reader.extract_info(URL, download=False)
stream = next(f for f in info['formats'] if f['format_id'] == '30016')
headers = ''.join(f'{key}: {value}\r\n' for key, value in stream.get('http_headers', info.get('http_headers', {})).items())
times = list(range(0, 25, 2))
frames = []
for age in times:
    output = REF / f'frame-{age:02d}s.jpg'
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
               '-y', '-headers', headers, '-ss', str(age), '-i', stream['url'],
               '-frames:v', '1', '-q:v', '4', str(output)]
    result = subprocess.run(command, capture_output=True, timeout=35)
    if result.returncode == 0 and output.exists():
        frames.append((age, output))
    else:
        print('REFERENCE_FRAME_UNAVAILABLE', age, result.stderr.decode('utf-8', 'replace')[-350:], flush=True)
    print('REFERENCE_FRAME', age, output.exists(), flush=True)
sheet = Image.new('RGB', (640 * 3, 392 * 5), '#222222')
draw = ImageDraw.Draw(sheet)
for i, (age, path) in enumerate(frames):
    picture = Image.open(path).convert('RGB')
    x, y = (i % 3) * 640, (i // 3) * 392
    sheet.paste(picture, (x, y + 30))
    draw.text((x + 8, y + 7), f'BV17HSbBvE3M / {age:.3f} s', fill='white')
sheet.save(REF / 'overview.jpg', quality=86)
metadata = dict(reference_url=URL, video_id=info['id'], title=info['title'],
                duration_seconds=info['duration'], format_id=stream['format_id'],
                resolution=[stream['width'], stream['height']],
                public_access=True, credentials_used=False, original_video_saved=False,
                original_video_published=False, study_frame_seconds=[t for t, p in frames],
                imagery_viewed_by_author=False, runtime_tested=False)
(REF / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('REFERENCE_METADATA_SAVED', len(frames), flush=True)
