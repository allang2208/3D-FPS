"""Read the user's reload reference and convert the supplied shot to PCM WAV."""
import json
import subprocess
import wave
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
VIDEO = PROJECT / 'Saved/Ash12ReloadRef/ref.mp4'
AUDIO = Path('D:/FPS3D/资产/音效/ash-12-fire.mp3')
cap = cv2.VideoCapture(str(VIDEO))
fps = cap.get(cv2.CAP_PROP_FPS)
times = (6.4, 6.8, 7.43, 7.77, 8.20, 8.40)
tiles = []
for t in times:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError('Reference read failed at ' + str(t))
    frame = cv2.resize(frame, (600, 338))
    cv2.putText(frame, f'{t:.2f}s', (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                .8, (0, 255, 255), 2, cv2.LINE_AA)
    tiles.append(frame)
sheet = np.vstack([np.hstack(tiles[i:i+2]) for i in range(0, len(tiles), 2)])
cv2.imwrite(str(HERE / 'reference-camera.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
cap.release()

# Decode the supplied one-shot without stretching or normalising its envelope.
wav = HERE / 'S_ASH12_Fire.wav'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y',
                '-i', str(AUDIO), '-vn', '-ar', '48000', '-c:a', 'pcm_s16le',
                str(wav)], check=True)
with wave.open(str(wav), 'rb') as w:
    details = {'source': str(AUDIO), 'wav': str(wav),
               'duration_seconds': w.getnframes() / w.getframerate(),
               'sample_rate': w.getframerate(), 'channels': w.getnchannels(),
               'sample_bytes': w.getsampwidth()}
(HERE / 'source.json').write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(details, ensure_ascii=False))
