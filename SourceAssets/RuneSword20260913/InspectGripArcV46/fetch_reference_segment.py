"""Fetch the reference video's 1:30-1:32 segment and cut it into frames.

Local research only, same rule the earlier reference study followed: the video
and its frames stay on this machine and are never redistributed or imported.
"""
import json, sys
from pathlib import Path
import requests

P = Path(__file__).parent
OUT = P.parent / 'VideoReferenceStudy20260915' / 'Overhead90_92'
OUT.mkdir(parents=True, exist_ok=True)
VIDEO = OUT / 'reference_video.mp4'
BVID = 'BV1hCJFzQEyR'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0 Safari/537.36')
HEADERS = {'User-Agent': UA, 'Referer': 'https://www.bilibili.com/'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get_json(url, params=None):
    response = SESSION.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


view = get_json('https://api.bilibili.com/x/web-interface/view', {'bvid': BVID})
if view.get('code') != 0:
    print('view failed:', view)
    sys.exit(1)
data = view['data']
cid = data['cid']
print('title      :', data['title'])
print('duration   :', data['duration'], 's')
print('cid        :', cid)

play = get_json('https://api.bilibili.com/x/player/playurl',
                {'bvid': BVID, 'cid': cid, 'qn': 32, 'fnval': 1, 'fnver': 0,
                 'fourk': 0, 'platform': 'html5'})
if play.get('code') != 0:
    print('playurl failed:', play)
    sys.exit(1)
durl = play['data'].get('durl') or []
if not durl:
    print('no durl; dash keys:', list(play['data'].keys()))
    sys.exit(1)
url = durl[0]['url']
print('stream size:', durl[0].get('size'), 'url host:', url.split('/')[2])

(OUT / 'source.json').write_text(json.dumps({
    'bvid': BVID,
    'title': data['title'],
    'cid': cid,
    'duration_seconds': data['duration'],
    'requested_seconds': [90, 92],
    'note': 'Local research frames only; not redistributed or imported.',
}, ensure_ascii=False, indent=2), encoding='utf-8')

if not VIDEO.exists() or VIDEO.stat().st_size < 1024:
    print('downloading to', VIDEO)
    with SESSION.get(url, headers=HEADERS, stream=True, timeout=120) as stream:
        stream.raise_for_status()
        with VIDEO.open('wb') as handle:
            for chunk in stream.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
print('video bytes:', VIDEO.stat().st_size)

import cv2
capture = cv2.VideoCapture(str(VIDEO))
fps = capture.get(cv2.CAP_PROP_FPS)
count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
print('video %dx%d %.3f fps, %d frames (%.1f s)'
      % (width, height, fps, count, count / max(fps, 1e-6)))

start, end = 89.6, 92.2
frames = []
index = int(round(start * fps))
capture.set(cv2.CAP_PROP_POS_FRAMES, index)
while True:
    ok, frame = capture.read()
    if not ok:
        break
    seconds = index / fps
    if seconds > end:
        break
    name = 'f%03d_%.4f.png' % (len(frames), seconds)
    cv2.imwrite(str(OUT / name), frame)
    frames.append((name, seconds))
    index += 1
capture.release()
print('saved %d frames from %.1f s to %.1f s' % (len(frames), start, end))
print('FETCH_REFERENCE_SEGMENT_DONE')
