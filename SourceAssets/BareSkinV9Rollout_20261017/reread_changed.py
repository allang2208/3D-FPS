"""Read-only commandlet: re-read (data model, 15 fps, component space) the clips the arm axial fix wrote
(InstalledArm receipts) into ClipsSim2/ = ClipsSim with those clips replaced, for the pose examples."""
import json, sys, gc, shutil
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u
import ue_rawpose as rp

import os
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017'); OUT = R / 'ClipsSim2'; OUT.mkdir(exist_ok=True)
DIR = os.environ.get('V9R_REREAD_DIR', 'InstalledArm'); SRC = os.environ.get('V9R_REREAD_SRC', 'ClipsSim')
STAMP = R / 'Work' / ('reread_done_' + DIR + '.json')          # second rounds update ClipsSim2 in place
done = set(json.loads(STAMP.read_text())) if STAMP.exists() else set()
changed = {json.loads(f.read_text())['path'] for f in (R / DIR).glob('*.json') if not f.stem.endswith('.failed')}


def xform(t):
    q = t.rotation; p = t.translation
    return [round(p.x, 4), round(p.y, 4), round(p.z, 4), round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)]


for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text())
    for name, vm in plan['viewmodels'].items():
        src = R / SRC / (name + '.json'); dst = OUT / (name + '.json')
        if (SRC == 'ClipsSim' and dst.exists()) or (SRC != 'ClipsSim' and name in done) or not src.exists(): continue
        cd = json.loads(src.read_text()); bones = cd['bones']; todo = [p for p in cd['clips'] if p in changed and 'frames' in cd['clips'][p]]
        if todo:
            mesh = u.load_asset(vm + '.' + vm.split('/')[-1])
            for path in todo:
                seq = u.load_asset(path + '.' + path.split('/')[-1])
                n, fr = rp.frame_count(seq); rate = fr.numerator / fr.denominator; length = (n - 1) / rate
                m = max(2, int(round(length * 15)) + 1); frames = []
                for i in range(m):
                    k = min(n - 1, int(round(i / 15.0 * rate)))
                    comp = rp.component(seq, vm, k, mesh, bones); frames.append([xform(comp[x]) for x in bones])
                cd['clips'][path] = dict(length=length, fps=15, frames=frames, keys=n, rate=rate)
        dst.write_text(json.dumps(cd, separators=(',', ':')))
        if SRC != 'ClipsSim': done.add(name); STAMP.write_text(json.dumps(sorted(done)))
        print('V9R_REREAD', name, len(todo), flush=True); gc.collect()
print('V9R_REREAD_COMPLETE', flush=True)
