"""Compose real runtime frames and sampled movement data; does not generate game art."""
import argparse
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

args = argparse.ArgumentParser()
args.add_argument('run')
opt = args.parse_args()
root = Path(__file__).resolve().parents[2]
folder = root / 'Saved' / 'MonsterStairs' / opt.run
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
species = [('nurse', '护士'), ('handbrain', '手脑'), ('maggot', '毒蛆')]
sequences = [(kind, name, sorted(folder.glob(f'{kind}_nav_stairs_up_*.png'))) for kind, name in species]
assert all(seq for _, _, seq in sequences)
frames = []
for index in range(110):
    canvas = Image.new('RGB', (672, 844), '#111c29')
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 10), '三种怪物 · 自动上楼梯（实机原速）', font=font, fill='#edf3fc')
    for row, (kind, name, sequence) in enumerate(sequences):
        top = 48 + row * 260
        draw.text((16, top), name + '  |  20 cm × 6', font=small, fill='#8bd8ef')
        source = Image.open(sequence[min(index, len(sequence)-1)]).convert('RGB')
        source = source.crop((0, 110, 960, 450)).resize((672, 238), Image.Resampling.LANCZOS)
        canvas.paste(source, (0, top+22))
    frames.append(canvas)
palette = frames[50].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
gif_frames[0].save(folder/'stairs-preview.gif', save_all=True, append_images=gif_frames[1:], duration=100, loop=0, optimize=True)
contact = Image.new('RGB', (1008, 422), '#111c29')
for column, index in enumerate((20, 50, 80)):
    contact.paste(frames[index].resize((336, 422), Image.Resampling.LANCZOS), (column*336, 0))
contact.save(folder/'preview-contact.png')

with (folder/'trajectory.csv').open(encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
for ax, (kind, _) in zip(axes, species):
    data = [r for r in rows if r['species']==kind and r['case']=='step40']
    dt = float(data[0]['dt'])
    times = [int(r['frame'])*dt for r in data]
    cap0, mesh0 = float(data[0]['capsule_z']), float(data[0]['mesh_z'])
    ax.plot(times, [float(r['capsule_z'])-cap0 for r in data], color='#89939e', label='Capsule (native swept step)', linewidth=1.3)
    ax.plot(times, [float(r['mesh_z'])-mesh0 for r in data], color='#008bb5', label='Visible mesh (linear compensation)', linewidth=1.6)
    ax.set_ylabel(f'{kind}\nheight change (cm)')
    ax.grid(alpha=.2)
axes[0].legend(loc='lower right')
axes[0].set_title('40 cm obstacle: measured capsule and visible mesh positions')
axes[-1].set_xlabel('Simulation time (s)')
fig.tight_layout()
fig.savefig(folder/'trajectory.png', dpi=160)
print(folder/'stairs-preview.gif')
print(folder/'trajectory.png')
