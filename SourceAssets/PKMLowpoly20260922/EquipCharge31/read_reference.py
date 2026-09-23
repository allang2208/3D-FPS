"""Decode only the supplied video's equip and empty-reload contact windows."""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

O = Path(__file__).parent
R = O.parent
ffmpeg = R.parent / 'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
movie = R / 'References/PKM_UserReloadReference.mp4'
for name, times in [('equip', [i * .2 for i in range(21)]),
                    ('charge', [23.4 + i * .15 for i in range(21)])]:
    sheet = Image.new('RGB', (1600, 7 * 320), '#202328')
    draw = ImageDraw.Draw(sheet)
    for i, time in enumerate(times):
        frame = O / f'{name}_{i:02}.jpg'
        subprocess.run([str(ffmpeg), '-v', 'error', '-y', '-ss', str(time), '-i', str(movie),
                        '-frames:v', '1', '-vf', 'scale=528:-1', str(frame)], check=True)
        im = Image.open(frame)
        x, y = i % 3 * 533, i // 3 * 320
        sheet.paste(im, (x, y))
        draw.text((x + 8, y + 298), f'{time:.2f}s', fill='white')
    sheet.save(O / f'{name}_reference.jpg', quality=85)
print('PKM31_REFERENCE_DECODED')
