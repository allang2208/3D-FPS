"""Package measured reports and unmodified source/runtime renders for review."""
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

O = Path(__file__).resolve().parent
PROJECT = O.parents[1]
D = O / 'Delivery'
D.mkdir(exist_ok=True)
FONT = 'C:/Windows/Fonts/msyh.ttc'
FFMPEG = PROJECT / 'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
FAMILIES = [('m4', 'canted'), ('akm', 'canted'), ('akm', 'vertical'), ('akm', 'prism'), ('akm', 'angled')]
NAMES = {'canted': '45° 侧倾握把', 'vertical': '垂直握把', 'prism': '棱镜阻手器', 'angled': '共振前握把'}

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def save(p, data):
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def shot(weapon, grip, name):
    return PROJECT / f'Saved/ForegripAudit/{weapon}-{grip}-accepted/{name}.png'

def board(name, cells, columns=2, width=600):
    height = 470
    canvas = Image.new('RGB', (columns * width, ((len(cells) + columns - 1) // columns) * height), '#10171d')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 22)
    for i, (label, path) in enumerate(cells):
        x, y = i % columns * width, i // columns * height
        draw.text((x + 14, y + 8), label, font=font, fill='#e7f2f5')
        im = Image.open(path).convert('RGB')
        im.thumbnail((width, height - 42))
        canvas.paste(im, (x + (width - im.width) // 2, y + 42 + (height - 42 - im.height) // 2))
    canvas.save(D / name)

board('M4_AKM_Canted.png', [
    (f'{w.upper()} · 45° · {label}', shot(w, 'canted', view))
    for view, label in [('grasp_front', '手背 / 并指'), ('wrist_review', '腕肘支撑')]
    for w in ['m4', 'akm']])
board('AKM_Grips.png', [(f'AKM · {NAMES[v]}', shot('akm', v, 'grasp_closeup')) for v in NAMES])
board('M4_Before_After.png', [
    (label, O / file) for label, file in [
        ('M4 45° · 修改前 · 原模型渲染', 'before_palm.png'),
        ('M4 45° · 修改后 · 原模型渲染', 'exact_final_palm.png'),
        ('M4 45° · 修改前 · 整臂', 'before_arm.png'),
        ('M4 45° · 修改后 · 整臂', 'exact_final_arm.png')]])

runtime = {}
for w, v in FAMILIES:
    run = f'{w}-{v}-accepted'
    log = (O / f'runtime-{run}.log').read_text(encoding='utf-8', errors='replace')
    assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
    runtime[run] = {'passed_checks': len(re.findall(r'FOREGRIP_AUDIT: PASS', log)), 'failures': 0}
    stamps = {}
    for timestamp, frame in re.findall(r'\[([\d.\-:]+)\]\[\s*\d+\].*Tracing Screenshot "([^"]+)"', log):
        stamps[frame] = dt.datetime.strptime(timestamp, '%Y.%m.%d-%H.%M.%S:%f').timestamp()
    frames = [(shot(w, v, n), 1.1) for n in ['idle', 'grasp_closeup', 'wrist_review', 'ads']]
    review = []
    for clip in ['standard_normal', 'standard_empty', 'drum_normal', 'drum_empty']:
        paths = sorted(shot(w, v, 'idle').parent.glob(clip + '_*.png'))
        assert paths
        for i, path in enumerate(paths):
            duration = stamps[paths[i+1].stem] - stamps[path.stem] if i+1 < len(paths) else .12
            assert 0 < duration < 2, (run, path.name, duration)
            frames.append((path, duration))
        frames.append((shot(w, v, {'standard_normal':'returned_6', 'standard_empty':'returned_8', 'drum_normal':'returned_10', 'drum_empty':'returned_12'}[clip]), .6))
        for j in [0, int((len(paths)-1)*.15), int((len(paths)-1)*.7), len(paths)-1]:
            review.append((f'{w.upper()} {v} · {clip} · {paths[j].stem.rsplit("_", 1)[1]}', paths[j]))
    board(f'{w}_{v}_ReloadReview.jpg', review, columns=4, width=440)
    concat = D / f'{w}_{v}.ffconcat'
    concat.write_text('ffconcat version 1.0\n' + ''.join(f"file '{p.as_posix()}'\nduration {duration:.6f}\n" for p, duration in frames) + f"file '{frames[-1][0].as_posix()}'\n", encoding='utf-8')
    subprocess.run([str(FFMPEG), '-v', 'error', '-y', '-safe', '0', '-i', str(concat), '-r', '30', '-c:v', 'libx264', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(D / f'{w}_{v}.mp4')], check=True)
for v in ['canted', 'vertical']:
    run = f'akm-{v}-ui-accepted'
    log = (O / f'runtime-{run}.log').read_text(encoding='utf-8', errors='replace')
    match = re.search(r'CANTED_UI_AUDIT COMPLETE checks=(\d+) failures=0', log)
    assert match and 'CANTED_UI_AUDIT FAIL' not in log
    runtime[run] = {'passed_checks': int(match[1]), 'failures': 0}

geometry = {}
for w, v in FAMILIES:
    g = read(O / w / v / 'geometry.json')
    geometry[f'{w}/{v}'] = {'samples': len(g), 'finger_grip_intersection_samples': sum(bool(r['crossing_hand_triangles']) for r in g.values()), 'finger_self_intersection_samples': sum(bool(r['self']) for r in g.values())}
    assert not geometry[f'{w}/{v}']['finger_grip_intersection_samples']
source_contacts = read(O / 'preserved_source_contacts.json')
assert not any(x['new_only_times'] for x in source_contacts.values())
assets = read(O / 'asset_validation.json')
assert len(assets) == 45 and all(x['passed'] for x in assets.values())
pose = read(O / 'pose_reference_validation.json')
compression_metrics = {k: max(x[k] for x in assets.values()) for k in ['compression_position_cm', 'compression_rotation_deg', 'preserved_nonleft_cm', 'preserved_reload_contact_cm']}
acceptance = {
    'date': '2026-09-11', 'scope': 'M4 canted refinement; four AKM grip families and M4 attachment stat parity',
    'native_build': {'module_suffix': '2026096228', 'result': 'Succeeded'},
    'runtime': runtime, 'geometry': geometry,
    'inherited_finger_self_intersection_sample_times': sum(x['sampled_contact_times'] for x in source_contacts.values()),
    'new_only_self_intersection_sample_times': 0,
    'geometry_scope': 'Sampled actual skinned finger surfaces against grip meshes plus inter-finger surfaces; not all arm/gun surfaces or continuous time.',
    'animation_assets_passed': len(assets), 'compression_maxima': compression_metrics,
    'source_to_runtime_idle_pair_distance_error_cm': {k: v['True<AnimDataEvalType.COMPRESSED: 2>']['maximum_pair_distance_error_cm'] for k,v in pose.items()},
    'formal_animation_paths': list(assets),
    'formal_new_static_paths': ['/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_' + n for n in ['canted_CompactMount', 'vertical', 'angled']],
    'editable_families': [str((O / w / v / f'{w.upper()}_{v}_Family_Editable.blend').relative_to(O)) for w,v in FAMILIES],
    'commandlet_environment': 'Import/readback scripts passed. Commandlet process exit 1 includes preexisting GameFeatureData AssetManager configuration and HTTP 8000 contention. Fresh runtime processes exited 0.',
    'preview': 'Actual UE screenshots; video frame durations recovered from screenshot log timestamps; silent visual evidence, no new audio synchronization claim.',
    'user_visual_acceptance': 'Awaiting user review of this iteration; implementation and scoped automated/visual verification complete.'
}
save(O / 'acceptance.json', acceptance)
manifest = []
for w,v in FAMILIES:
    folder = O / w / v
    for p in sorted(folder.iterdir()):
        if p.suffix in ['.blend', '.fbx'] and (p.name.startswith('A_') or p.name.endswith('Family_Editable.blend')):
            manifest.append({'path':str(p.relative_to(O)), 'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
save(O / 'delivery_manifest.json', manifest)
print('GRIP_DELIVERY_PASS', len(assets), sum(v['samples'] for v in geometry.values()), sum(v['passed_checks'] for v in runtime.values()), flush=True)
