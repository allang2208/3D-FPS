"""Assemble real UE frames at recorded game speed. Adds an external caption bar only.
No retouching, synthetic frames, frame interpolation, exposure changes or removed grass.
"""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    rows = list(csv.DictReader((args.capture / 'frames.csv').open(encoding='utf-8-sig')))
    report = (args.capture / 'results.txt').read_text(encoding='utf-8-sig')
    start = float(re.search(r'PHASE 2 time=([\d.]+)', report)[1])
    contact = float(re.search(r'RELEASE last_contact=([\d.]+)', report)[1])
    timing = re.search(r'SETTINGS hold=([\d.]+) recover=([\d.]+)', report)
    # Historical v12 captures predate the SETTINGS record; retain their original timing.
    hold, recover = (float(timing[1]), float(timing[2])) if timing else (2.5, 3.5)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
    width, height, bar = 960, 540, 64
    phases = {2: '原始草地', 3: '实际行走压草', 4: '站立保压', 5: '继续行走，离开观察点', 6: '离开后恢复'}
    palette_sheet = Image.new('RGB', (256*4, 144*2+64), '#151a20')
    for slot in range(8):
        row = rows[min(len(rows)-1, slot*(len(rows)-1)//7)]
        with Image.open(args.capture / 'frames' / f"frame_{int(row['frame']):04d}.png") as image:
            palette_sheet.paste(image.convert('RGB').resize((256,144)), ((slot%4)*256,(slot//4)*144))
    d = ImageDraw.Draw(palette_sheet)
    d.text((12,290),'实机草地录制 0123456789',font=font,fill='#f0f3f7')
    palette = palette_sheet.quantize(colors=256)
    frames, durations, metadata = [], [], []
    for index, row in enumerate(rows):
        phase, timestamp = int(row['phase']), float(row['game_seconds'])
        with Image.open(args.capture / 'frames' / f"frame_{int(row['frame']):04d}.png") as source:
            canvas = Image.new('RGB',(width,height+bar),'#151a20')
            canvas.paste(source.convert('RGB').resize((width,height),Image.Resampling.LANCZOS),(0,bar))
        elapsed = float(row['phase_seconds'])
        label = f"{phases[phase]}  {elapsed:.1f} 秒"
        if phase == 6:
            age = timestamp+start-contact
            state = '低伏保持' if age<hold else ('平滑抬起' if age<hold+recover else '已到恢复时刻')
            label = f"离开接触 {age:.1f} 秒 · {state}"
        draw = ImageDraw.Draw(canvas)
        draw.text((14,6),label,font=font,fill='#f0f3f7')
        draw.text((14,36),'UE 实机连续帧 · 原速 · 固定观察机位 · 角色模型隐藏以观察草地',font=small,fill='#f0f3f7')
        draw.text((795,8),f't = {timestamp:04.1f}s',font=font,fill='#f0f3f7')
        frames.append(canvas.quantize(palette=palette,dither=Image.Dither.NONE))
        next_time = float(rows[index+1]['game_seconds']) if index+1<len(rows) else timestamp+.1
        durations.append(max(10,round((next_time-timestamp)*100)*10))
        metadata.append({'frame':int(row['frame']),'phase':phase,'game_seconds':timestamp})
    output = args.capture / 'grass_v12_full.gif'
    frames[0].save(output,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False,disposal=2)
    # A second, uninterrupted excerpt focuses on the end of standing and recovery.
    selection = [i for i,r in enumerate(rows) if int(r['phase'])>=5 or (int(r['phase'])==4 and float(r['phase_seconds'])>=8.5)]
    excerpt = args.capture / 'grass_v12_recovery.gif'
    frames[selection[0]].save(excerpt,save_all=True,append_images=[frames[i] for i in selection[1:]],
                             duration=[durations[i] for i in selection],loop=0,optimize=False,disposal=2)
    compact = []
    for kind in ('full', 'recovery'):
        result = args.capture / f'grass_v12_{kind}_compact.gif'
        filters = ('fps=6,scale=560:-1:flags=lanczos,split[a][b];'
                   '[a]palettegen=max_colors=128:stats_mode=diff[p];'
                   '[b][p]paletteuse=dither=none:diff_mode=rectangle')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-hide_banner', '-loglevel', 'error',
                        '-i', str(args.capture / f'grass_v12_{kind}.gif'), '-filter_complex', filters,
                        '-gifflags', '+transdiff', '-loop', '0', str(result)], check=True)
        compact.append(str(result))
    receipt = {'source_frames':len(frames),'game_duration_seconds':float(rows[-1]['game_seconds']),
               'gif_duration_seconds':sum(durations)/1000,'files':[str(output),str(excerpt)],
               'compact_gifs': compact, 'compact_encoding': '560px, 6fps, original speed, 128 colors',
               'scope':'Real render frames; resized and captioned, no retouching or interpolation'}
    (args.capture/'gif-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    main()
