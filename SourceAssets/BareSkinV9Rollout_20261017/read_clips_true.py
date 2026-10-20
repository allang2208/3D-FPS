"""Read-only commandlet: arm bones (component space) of every batch clip from the sequence data model
(ue_rawpose), sampled at 15 fps on the data-model frame grid. Env: V9R_BATCH, V9R_CLIPS_DIR (default ClipsTrue).
Clip lists are taken from the earlier discovery files in Clips/ (same paths)."""
import json, os, sys, gc
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u
import ue_rawpose as rp

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
BATCH = os.environ.get('V9R_BATCH', 'batch1'); OUT = R / os.environ.get('V9R_CLIPS_DIR', 'ClipsTrue'); OUT.mkdir(exist_ok=True)
plan = json.loads((R / (BATCH + '.json')).read_text())


def xform(t):
    q = t.rotation; p = t.translation
    return [round(p.x, 4), round(p.y, 4), round(p.z, 4), round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)]


for name, vm in plan['viewmodels'].items():
    f = OUT / (name + '.json'); src = R / 'Clips' / (name + '.json')
    if f.exists() or not src.exists(): continue
    old = json.loads(src.read_text()); bones = old['bones']
    mesh = u.load_asset(vm + '.' + vm.split('/')[-1])
    out = dict(mesh=vm, skeleton=old.get('skeleton'), bones=bones, clips={}, reader='data_model')
    for path, c in old['clips'].items():
        if 'frames' not in c: out['clips'][path] = c; continue
        seq = u.load_asset(path + '.' + path.split('/')[-1])
        n, fr = rp.frame_count(seq); rate = fr.numerator / fr.denominator; length = (n - 1) / rate
        m = max(2, int(round(length * 15)) + 1); frames = []
        for i in range(m):
            k = min(n - 1, int(round(i / 15.0 * rate)))
            comp = rp.component(seq, vm, k, mesh, bones)
            frames.append([xform(comp[b]) for b in bones])
        out['clips'][path] = dict(length=length, fps=15, frames=frames, keys=n, rate=rate)
    f.write_text(json.dumps(out, separators=(',', ':')))
    print('V9R_TRUE', name, len(out['clips']), flush=True)
    gc.collect(); u.SystemLibrary.collect_garbage()
print('V9R_TRUE_COMPLETE', flush=True)
