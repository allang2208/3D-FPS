"""Assemble requested motion review previews; durations follow the sample clock."""
from pathlib import Path
import json
import sys
from PIL import Image, ImageDraw

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('D:/FPS3D/FPSGAME/Saved/HighlandThirdPersonReview20261106/native-v3')
out = root/'Previews'
out.mkdir(exist_ok=True)
for role in ['sweep', 'charged_thrust']:
    folder = root/'Jason'/('Standard_'+role)
    motion = json.loads((folder/'motion.json').read_text(encoding='utf-8-sig'))
    files = sorted((folder/'render-all').glob('*-front.png'))
    if len(files) != len(motion['frames']):
        raise RuntimeError(f'Incomplete render: {role}, {len(files)}')
    frames = []
    for f in files:
        frame_id = int(f.stem.split('-')[0])
        meta = motion['frames'][frame_id]
        sheet = Image.new('RGB', (960, 514), (22, 26, 32))
        sheet.paste(Image.open(f).resize((480, 480)), (0, 34))
        sheet.paste(Image.open(f.with_name(f.name.replace('front', 'back'))).resize((480, 480)), (480, 34))
        ImageDraw.Draw(sheet).text((12, 8), f'{role} | native third-person pose | {meta["time"]:.3f}s | {meta["variant"]}', fill='white')
        frames.append(sheet.quantize(colors=128))
    durations = [30 if i%3 != 2 else 40 for i in range(len(frames))]
    durations[-1] = 600
    frames[0].save(out/(role+'.gif'), save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=2)
print(out)
