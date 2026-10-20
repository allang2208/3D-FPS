"""Read-only commandlet: every key of the clips in Work/armfix_jobs.json, local transforms (data model) of the arm
chains from the root to the hands and the forearm twist bones. -> Work/ArmDump/<hash>.json"""
import json, sys, hashlib, gc
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017'); OUT = R / 'Work/ArmDump'; OUT.mkdir(exist_ok=True)
HIER = json.loads((R / 'Work/mesh_hierarchy.json').read_text())
jobs = json.loads((R / 'Work/armfix_jobs.json').read_text())
meshes = {}; n_done = 0
for path, job in sorted(jobs.items()):
    f = OUT / (hashlib.sha256(path.encode()).hexdigest()[:12] + '.json')
    if f.exists(): continue
    vm = job['vm']; names_all = HIER[vm]['names']; par = dict(zip(names_all, HIER[vm]['parents']))
    want = set()
    for s in job['sides']:
        for b in ('hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s):
            x = b
            while x is not None and x in par: want.add(x); x = par[x]
    names = [x for x in names_all if x in want]
    seq = u.load_asset(path + '.' + path.split('/')[-1]); meshes.setdefault(vm, u.load_asset(vm + '.' + vm.split('/')[-1]))
    dmi = seq.get_editor_property('data_model_interface'); n = dmi.get_number_of_keys(); fr = dmi.get_frame_rate()
    keys = []
    for k in range(n):
        poses = u.AnimationLibrary.get_bone_poses_for_frame(seq, names, k, False, meshes[vm])
        keys.append([[round(t.translation.x, 5), round(t.translation.y, 5), round(t.translation.z, 5),
                      round(t.rotation.x, 7), round(t.rotation.y, 7), round(t.rotation.z, 7), round(t.rotation.w, 7)] for t in poses])
    f.write_text(json.dumps(dict(path=path, vm=vm, n=n, rate=fr.numerator / fr.denominator, names=names,
                                 parents=[par[x] for x in names], keys=keys), separators=(',', ':')))
    n_done += 1
    if n_done % 20 == 0: gc.collect(); u.SystemLibrary.collect_garbage()
    print('V9R_ARMDUMP', path, n, flush=True)
print('V9R_ARMDUMP_COMPLETE', n_done, flush=True)
