"""Extract the requested public reference for analysis, never for runtime import."""
import argparse
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorImpactReferenceV7_20261114/Reference'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=float, default=472)
    parser.add_argument('--end', type=float, default=484)
    parser.add_argument('--step', type=float, default=1)
    parser.add_argument('--crop',type=int,nargs=4)
    args = parser.parse_args()
    cap = cv2.VideoCapture(str(OUT / 'reference-analysis-only.mp4'))
    if not cap.isOpened():
        raise RuntimeError('Reference download is not complete')
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = round((args.end - args.start) / args.step) + 1
    row_height=(min(360,args.crop[3]) if args.crop else 360)+24
    sheet = Image.new('RGB', (1280, ((count + 1) // 2) * row_height), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i in range(count):
        t = args.start + i * args.step
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f'Missing video frame at {t}')
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if args.crop:
            x,y,w,h=args.crop
            img=img.crop((x,y,x+w,y+h))
        img.save(OUT / (('meteor-' if args.crop else '')+f'frame-{t:07.3f}.png'))
        img.thumbnail((640, 360))
        x, y = i % 2 * 640, i // 2 * row_height
        sheet.paste(img, (x, y + 24))
        draw.text((x + 8, y + 5), f'{t:.3f} s / frame {round(t * fps)}', fill='white')
    cap.release()
    path = OUT / f'frames-{args.start:g}-{args.end:g}.jpg'
    sheet.save(path, quality=92)
    print(str(path), flush=True)
    print(f'fps={fps}', flush=True)


if __name__ == '__main__':
    main()
