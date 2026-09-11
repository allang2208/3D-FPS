"""Assemble measured validation and actual UE captures, without altering their content."""
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

O = Path(__file__).resolve().parent
PROJECT = O.parents[1]
D = O / 'OpposedDelivery'
D.mkdir(exist_ok=True)
FAMILIES = [(w, 'vertical') for w in ['m4', 'akm']]
NAMES = {'vertical': '垂直握把', 'prism': '棱镜阻手器'}
FFMPEG = PROJECT / 'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def shot(w, v, name):
    return PROJECT / f'Saved/ForegripAudit/opposed-{w}-{v}/{name}.png'


def board(name, cells, columns=2, width=650):
    height = round(width * .76)
    canvas = Image.new('RGB', (columns * width, ((len(cells) + columns - 1) // columns) * height), '#10171d')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    for i, (label, path) in enumerate(cells):
        x, y = i % columns * width, i // columns * height
        draw.text((x + 14, y + 8), label, font=font, fill='#e7f2f5')
        im = Image.open(path).convert('RGB')
        im.thumbnail((width, height - 42))
        canvas.paste(im, (x + (width - im.width) // 2, y + 42 + (height - 42 - im.height) // 2))
    canvas.save(D / name)


board('M4_Player_Before_After.png', [
    ('修改前 · 玩家视点近景', PROJECT / 'Saved/ForegripAudit/front-before-m4-vertical/player_grasp_review.png'),
    ('已拒绝 · 拇指向前伸出', PROJECT / 'Saved/ForegripAudit/front-m4-vertical-final/player_grasp_review.png'),
    ('本轮 · 横向收拢对握', shot('m4', 'vertical', 'player_grasp_review'))], columns=3, width=600)
board('M4_AKM_Player_Views.png', [
    (f'{w.upper()} · {NAMES[v]} · 玩家视点', shot(w, v, 'player_grasp_review')) for w, v in FAMILIES])
board('M4_AKM_Wrist_Views.png', [
    (f'{w.upper()} · {NAMES[v]} · 腕肘', shot(w, v, 'wrist_review')) for w, v in FAMILIES])

runtime = {}
for w, v in FAMILIES:
    run = f'opposed-{w}-{v}'
    log = (O / f'runtime-{run}.log').read_text(encoding='utf-8', errors='replace')
    assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
    runtime[run] = {'passed_log_checks': len(re.findall(r'FOREGRIP_AUDIT: PASS', log)), 'failures': 0}
    stamps = {}
    for stamp, frame in re.findall(r'\[([\d.\-:]+)\]\[\s*\d+\].*Tracing Screenshot "([^"]+)"', log):
        stamps[frame] = dt.datetime.strptime(stamp, '%Y.%m.%d-%H.%M.%S:%f').timestamp()
    frames = [(shot(w, v, n), 1.1) for n in ['idle', 'player_grasp_review', 'grasp_closeup', 'wrist_review', 'ads']]
    review = []
    for clip in ['standard_normal', 'standard_empty', 'drum_normal', 'drum_empty']:
        # A repeated run can leave extra tail PNGs; only use frames recorded by this run.
        paths = sorted(p for p in shot(w, v, 'idle').parent.glob(clip + '_*.png') if p.stem in stamps)
        assert paths
        for i, path in enumerate(paths):
            duration = stamps[paths[i + 1].stem] - stamps[path.stem] if i + 1 < len(paths) else .12
            assert 0 < duration < 2, (run, path.name, duration)
            frames.append((path, duration))
        returned = {'standard_normal': 'returned_6', 'standard_empty': 'returned_8', 'drum_normal': 'returned_10', 'drum_empty': 'returned_12'}[clip]
        frames.append((shot(w, v, returned), .6))
        for j in [0, int((len(paths)-1)*.15), int((len(paths)-1)*.7), len(paths)-1]:
            review.append((f'{w.upper()} {v} · {clip} · {j}', paths[j]))
    board(f'{w}_{v}_ReloadReview.jpg', review, columns=4, width=440)
    concat = D / f'{w}_{v}.ffconcat'
    concat.write_text('ffconcat version 1.0\n' + ''.join(f"file '{p.as_posix()}'\nduration {duration:.6f}\n" for p, duration in frames) + f"file '{frames[-1][0].as_posix()}'\n", encoding='utf-8')
    subprocess.run([str(FFMPEG), '-v', 'error', '-y', '-safe', '0', '-i', str(concat), '-r', '30', '-c:v', 'libx264', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(D / f'{w}_{v}.mp4')], check=True)

geometry, thumb_gun = {}, {}
for w, v in FAMILIES:
    data = read(O / w / v / 'geometry.json')
    geometry[f'{w}/{v}'] = {'samples': len(data), 'finger_grip_intersection_samples': sum(bool(x['crossing_hand_triangles']) for x in data.values()), 'finger_self_intersection_samples': sum(bool(x['self']) for x in data.values())}
    assert not geometry[f'{w}/{v}']['finger_grip_intersection_samples']
    data = read(O / w / v / 'thumb_gun.json')
    entry = {'samples': len(data), 'intersection_sample_times': sum(bool(x) for x in data.values())}
    if w == 'akm':
        old = read(O / f'before_thumb_gun_{v}.json')
        new_only = {k: {p: n for p, n in h.items() if p not in old.get(k, {})} for k, h in data.items()}
        new_only = {k: h for k, h in new_only.items() if h}
        entry['new_only_parts_at_sample'] = new_only
        entry['before_contact_samples'] = sum(bool(x) for x in old.values())
        assert not new_only, (w, v, new_only)
        save(O / w / v / 'thumb_gun_comparison.json', entry)
    else:
        assert not entry['intersection_sample_times']
    thumb_gun[f'{w}/{v}'] = entry
source_contacts = read(O / 'preserved_source_contacts.json')
# Report finger self-contact separately from rigid grip penetration.
assets = read(O / 'asset_validation.json')
assert len(assets) == 18 and all(x['passed'] for x in assets.values())
acceptance = {
    'date': '2026-09-11',
    'scope': 'M4 and AKM vertical grip opposed-thumb refinement; 18 animations; small handstops deferred under user wrap-around preference',
    'native_build': {'module_suffix': '2026096304', 'result': 'Succeeded'},
    'runtime': runtime, 'geometry': geometry, 'thumb_gun': thumb_gun,
    'finger_contact_sample_times_also_present_in_source': sum(x['sampled_contact_times']-len(x['new_only_times']) for x in source_contacts.values()),
    'reported_new_finger_contact_samples': {k:x['new_only_times'] for k,x in source_contacts.items()},
    'self_contact_comparison_scope': 'Counts whether any source finger contact exists at the same time. Per-pair details are in preserved_source_contacts.json; not all same-time pairs are inherited.',
    'geometry_scope': 'Sampled skinned finger/grip and inter-finger surfaces. Extra thumb/gun check covers visible main gun and factory magazine, excludes separate SM_AKM drum mesh. Source reload contacts remain; this is not continuous collision certification.',
    'animation_assets_passed': len(assets),
    'compression_maxima': {k: max(x[k] for x in assets.values()) for k in ['compression_position_cm', 'compression_rotation_deg', 'preserved_nonleft_cm', 'preserved_reload_contact_cm']},
    'pose_quality': read(O / 'pose_quality.json'),
    'pose_metric_scope': 'Rig axis directions at idle, not anatomical clinical joint angles. Four non-thumb finger local rotations retained.',
    'formal_animation_paths': list(assets),
    'formal_new_static_paths': [],
    'editable_families': [f'{w}/{v}/{w.upper()}_{v}_Family_Editable.blend' for w, v in FAMILIES],
    'commandlet_environment': 'Import/readback scripts passed. Commandlet exit 1 includes preexisting GameFeatureData AssetManager configuration and HTTP 8000 contention. Fresh runtime processes exited 0.',
    'preview': 'Actual UE captures. Player-view comparison uses the player eye position and FOV 30, with aim focused on the moving hand/thumb. Videos use capture timestamps and are silent visual evidence.',
    'user_visual_acceptance': 'Previous forward-thumb iteration rejected. This opposed-thumb vertical-grip iteration awaits user review.'
}
save(O / 'opposed_acceptance.json', acceptance)
manifest = []
for w, v in FAMILIES:
    for p in sorted((O / w / v).iterdir()):
        if p.suffix in ['.blend', '.fbx'] and (p.name.startswith('A_') or p.name.endswith('Family_Editable.blend')):
            manifest.append({'path': str(p.relative_to(O)), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
save(O / 'opposed_delivery_manifest.json', manifest)
assert len(manifest) == 38
print('OPPOSED_DELIVERY_PASS', len(assets), sum(v['samples'] for v in geometry.values()), sum(v['samples'] for v in thumb_gun.values()), flush=True)
