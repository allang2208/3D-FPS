"""Read-only: dump the two-handed sword's sprint-attack chop clips (Overhead, SprintOverhead) on the shared sword arms
rig, for laying out the kukri sprint attack (author_kukri_sprint.py).  Same packing as dump_sword_rig.py.
Writes Work/sprint/sword_overhead_dump.json.  Never saves packages."""
import json
from pathlib import Path
import unreal as u

P = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020")
MESH = "/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms"
# bone order of the shared rig, written from Work/ue_sword_dump.json (dump_sword_rig.py)
names = json.loads((P / 'Work' / 'sprint' / 'rig_names.json').read_text('utf-8'))
mesh = u.load_asset(MESH)


def pack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return [p.x, p.y, p.z, q.w, q.x, q.y, q.z, s.x, s.y, s.z]


base = "/Game/Weapons/AzureRunesword20260913/"
clips = {}
for name, path in [("Overhead", base + "A_RuneSword_Overhead"),
                   ("SprintOverhead", base + "TacticalSprint20260921/A_RuneSword_SprintOverhead")]:
    seq = u.load_asset(path)
    if not seq:
        clips[name] = None
        u.log_warning("KUKRI_DUMP missing %s" % path)
        continue
    dmi = seq.get_editor_property('data_model_interface')
    keys = dmi.get_number_of_keys()
    fr = dmi.get_frame_rate()
    frames = []
    for k in range(keys):
        poses = u.AnimationLibrary.get_bone_poses_for_frame(seq, names, k, False, mesh)
        frames.append([pack(t) for t in poses])
    clips[name] = dict(path=path, keys=keys, rate=fr.numerator / fr.denominator, length=seq.get_play_length(), frames=frames)
    u.log("KUKRI_DUMP clip %s keys=%d rate=%s len=%.3f" % (name, keys, fr.numerator / fr.denominator, seq.get_play_length()))
(P / 'Work' / 'sprint').mkdir(parents=True, exist_ok=True)
(P / 'Work' / 'sprint' / 'sword_overhead_dump.json').write_text(json.dumps(dict(mesh=MESH, names=names, clips=clips), separators=(',', ':')),
                                                               encoding='utf-8')
u.log("KUKRI_DUMP_COMPLETE")
