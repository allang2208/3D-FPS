"""Compare the same 75-degree camera in the previous and current bakes at 60 fps."""
import json
from pathlib import Path
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent / 'Review'
W, H = 480, 270


def main():
    report = json.loads((HERE / 'opening-report.json').read_text())
    previous = cv2.VideoCapture(str(HERE / 'Before' / 'ChainSlash_comparison.mp4'))
    current = cv2.VideoCapture(str(REVIEW / 'ChainSlash_comparison.mp4'))
    frames = (report['after']['Standard']['frames'] + 1) // 2
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
    target = HERE / 'shoulder-before-after.mp4'
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-loglevel', 'error', '-y',
               '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1440x304',
               '-r', '60', '-i', '-', '-an', '-c:v', 'libx264', '-crf', '17',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        try:
            for i in range(frames):
                old_ok, old = previous.read()
                new_ok, new = current.read()
                if not (old_ok and new_ok):
                    raise ValueError(f'Missing comparison frame {i}')
                header = Image.new('RGB', (3 * W, 34), (26, 33, 40))
                draw = ImageDraw.Draw(header)
                labels = ('修正前 · 标准柄', '修正后 · 标准柄', '修正后 · 长柄')
                for j, label in enumerate(labels):
                    draw.text((j * W + 12, 4), label, font=font, fill='white')
                draw.text((3 * W - 112, 4), f'{i / 60:0.3f} s', font=font, fill='#c4d0d0')
                panes = np.hstack((old[-H:, W:2 * W], new[-H:, W:2 * W], new[-H:, 2 * W:]))
                encoder.stdin.write(np.vstack((np.asarray(header)[:, :, ::-1], panes)).tobytes())
        finally:
            previous.release()
            current.release()
            encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Video encode failed')


if __name__ == '__main__':
    main()
