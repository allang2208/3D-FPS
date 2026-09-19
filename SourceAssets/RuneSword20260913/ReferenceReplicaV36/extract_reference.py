"""Extract the user-requested 76-78 second interval, preserving native frames."""
import json
import subprocess
import urllib.request
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).parent / 'Reference'
P.mkdir(parents=True, exist_ok=True)
URL = 'https://www.bilibili.com/video/BV1hCJFzQEyR/'
API = 'https://api.bilibili.com/x/player/playurl?bvid=BV1hCJFzQEyR&cid=30048845968&qn=80&fnval=16&fourk=0'
req = urllib.request.Request(API, headers={'User-Agent': 'Mozilla/5.0', 'Referer': URL})
response = json.load(urllib.request.urlopen(req, timeout=30))
if response['code'] != 0:
    raise RuntimeError(f'Video source unavailable: {response["code"]}')
video = max((v for v in response['data']['dash']['video'] if v['codecs'].startswith('avc1')),
            key=lambda v: (v['height'], v['bandwidth']))
start, duration = 75.8, 2.4
with (P/'extraction.log').open('w', encoding='utf-8') as log:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-hide_banner',
                    '-headers', 'Referer: '+URL+'\r\nUser-Agent: Mozilla/5.0\r\n',
                    '-ss', str(start), '-i', video.get('baseUrl') or video['base_url'],
                    '-t', str(duration), '-an', '-fps_mode', 'passthrough',
                    str(P/'source_%03d.png')], stdout=log, stderr=subprocess.STDOUT, check=True)
fps = float(video['frameRate'])
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
records = []
for i, path in enumerate(sorted(P.glob('source_*.png'))):
    stamp = start+i/fps
    records.append({'index': i, 'seconds': round(stamp, 9), 'file': path.name,
                    'requested': 76 <= stamp <= 78})
for first in range(0, len(records), 9):
    # All source frames; a consistent crop preserves wrist, palm and hilt proportions.
    sheet = Image.new('RGB', (1350, 1554), '#161d26')
    for j, row in enumerate(records[first:first+9]):
        frame = Image.open(P/row['file']).convert('RGB')
        w, h = frame.size
        crop = frame.crop((int(w*.58), int(h*.11), w, h))
        crop.thumbnail((444, 480), Image.Resampling.LANCZOS)
        x, y = (j%3)*450, (j//3)*518
        sheet.paste(crop, (x+(444-crop.width)//2, y))
        ImageDraw.Draw(sheet).text((x+8, y+486), f'{row["seconds"]:.4f} s  F{row["index"]:02d}', font=font, fill='white')
    sheet.save(P/f'frames_{first//9+1:02d}.jpg', quality=95)
(P/'source.json').write_text(json.dumps({
    'url': URL, 'cid': 30048845968, 'requested_seconds': [76, 78],
    'extracted_seconds': [start, start+duration], 'fps': fps,
    'width': video['width'], 'height': video['height'],
    'native_frames': True, 'records': records,
    'scope': 'Local reference study only. No original-game assets or animation tracks imported.'
}, indent=2), encoding='utf-8')
print('REFERENCE_NATIVE_FRAMES', len(records), video['width'], video['height'], fps, flush=True)
