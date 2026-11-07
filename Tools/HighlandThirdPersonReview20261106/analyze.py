"""Quantify captured motion discontinuities and build annotated review sheets."""
from pathlib import Path
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image, ImageDraw

ROOT = Path(sys.argv[1]) if len(sys.argv)>1 else Path('D:/FPS3D/FPSGAME/Saved/HighlandThirdPersonReview20261106/native-v3')
results = []
for kind in ['Jason', 'Kaitlin']:
    meta = json.loads((ROOT/kind/'mesh.json').read_text(encoding='utf-8-sig'))
    names, parents = meta['names'], meta['parents']
    for motion_file in (ROOT/kind).glob('*/motion.json'):
        folder = motion_file.parent
        motion = json.loads(motion_file.read_text(encoding='utf-8-sig'))
        poses = np.fromfile(folder/'poses.bin', np.float32).reshape(-1, len(names), 10)
        hands = poses[:, [names.index('hand_r'), names.index('hand_l')]]
        expected = hands[:, 0, :3] + Rotation.from_quat(hands[:, 0, 3:7]).apply(np.array(motion['left_grip'][:3]))
        errors = np.linalg.norm(hands[:, 1, :3]-expected, axis=1)
        # Sweep fixtures first jump to a held generic heavy-landing pose. Report
        # that setup separately from the newly authored Highland action itself.
        active = [i for i, f in enumerate(motion['frames']) if f['selected'].endswith(('HighlandBreakSweep', 'HighlandBreakSweepReady', 'HighlandRidgeThrust'))]
        core = [i for i, f in enumerate(motion['frames']) if f['selected'].endswith('HighlandBreakSweep') and f['progress'] > .2 and f['progress'] < .8]
        row = dict(body=kind, case=folder.name, finite=bool(np.isfinite(poses).all()),
                   post_process=any(f['post_process_instance'] for f in motion['frames']),
                   max_grip_distance_error_cm=float(errors.max()),
                   highland_grip_error_cm=float(errors[active].max()) if active else None,
                   sweep_core_grip_error_cm=float(errors[core].max()) if core else None)
        for side in ['l', 'r']:
            h, e, s = [names.index(n+'_'+side) for n in ['hand', 'lowerarm', 'upperarm']]
            local = Rotation.from_quat(poses[:, e, 3:7]).inv()*Rotation.from_quat(poses[:, h, 3:7])
            steps = np.rad2deg((local[:-1].inv()*local[1:]).magnitude())
            i = int(steps.argmax())
            a, b = poses[:, s, :3]-poses[:, e, :3], poses[:, h, :3]-poses[:, e, :3]
            angle = np.rad2deg(np.arccos(np.clip((a*b).sum(1)/(np.linalg.norm(a, axis=1)*np.linalg.norm(b, axis=1)), -1, 1)))
            row[side] = dict(max_wrist_local_step_degrees=float(steps[i]), step_time=motion['frames'][i+1]['time'],
                             elbow_angle_range=[float(angle.min()), float(angle.max())])
            active_steps = [i-1 for i in active if i>0 and i-1 in active]
            row[side]['highland_wrist_step_degrees'] = float(steps[active_steps].max()) if active_steps else None
        results.append(row)
        for directory in folder.glob('render-*'):
            files = sorted(directory.glob('*-front.png'))
            if not files:
                continue
            width, height, columns = 320, 348, 5
            sheet = Image.new('RGB', (columns*width, ((len(files)+columns-1)//columns)*height+34), (22, 26, 32))
            d = ImageDraw.Draw(sheet)
            d.text((10, 8), f'{kind} / {folder.name} / {directory.name} | native graph + mesh skin, 30 Hz', fill='white')
            for index, f in enumerate(files):
                frame = int(f.stem.split('-')[0]); info = motion['frames'][frame]
                x, y = index % columns*width, index//columns*height+34
                sheet.paste(Image.open(f).resize((width, width)), (x, y))
                d.text((x+5, y+width+3), f'{info["time"]:.3f}s  {info["variant"]}', fill='white')
            sheet.save(directory/'sheet.png')
(ROOT/'metrics.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
