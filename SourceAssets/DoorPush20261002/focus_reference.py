"""Keep only a two-second reference excerpt and contact study frames."""
import json
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
from PIL import Image, ImageDraw
import yt_dlp

P = Path(__file__).resolve().parent / 'References'
with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True, 'socket_timeout': 15}) as reader:
    info = reader.extract_info('https://www.bilibili.com/video/BV17HSbBvE3M/', download=False)
stream = next(f for f in info['formats'] if f['format_id'] == '30064')
headers = ''.join(f'{key}: {value}\r\n' for key, value in stream.get('http_headers', info.get('http_headers', {})).items())
start, duration = 12.4, 2.
excerpt = P / 'private-study-12.4-14.4.mp4'
command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y',
           '-headers', headers, '-ss', str(start), '-i', stream['url'], '-t', str(duration),
           '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', str(excerpt)]
result = subprocess.run(command, capture_output=True, timeout=40)
if result.returncode:
    raise RuntimeError(result.stderr.decode('utf-8', 'replace')[-700:])
video = cv2.VideoCapture(str(excerpt))
fps = video.get(cv2.CAP_PROP_FPS)
times = [12.6, 12.8, 13., 13.2, 13.4, 13.6, 13.8, 14.]
sheet = Image.new('RGB', (1280, 4 * 390), '#222222')
draw = ImageDraw.Draw(sheet)
for i, age in enumerate(times):
    video.set(cv2.CAP_PROP_POS_MSEC, (age - start) * 1000.)
    ok, frame = video.read()
    if not ok:
        continue
    output = P / f'contact-{age:.1f}s.jpg'
    cv2.imwrite(str(output), frame)
    picture = Image.open(output).convert('RGB')
    picture.thumbnail((640, 360))
    x, y = (i % 2) * 640, (i // 2) * 390
    sheet.paste(picture, (x, y + 30))
    draw.text((x + 8, y + 7), f'BV17HSbBvE3M / {age:.3f} s', fill='white')
sheet.save(P / 'contact-sequence.jpg', quality=88)
video.release()
metadata = json.loads((P / 'source.json').read_text(encoding='utf-8'))
metadata.update(excerpt_start_seconds=start, excerpt_duration_seconds=duration,
                excerpt_fps=fps, focused_frames_seconds=times,
                excerpt_usage='Private low-resolution motion study only; not redistributable project asset')
(P / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('FOCUSED_REFERENCE_SAVED', fps, start, duration, flush=True)
