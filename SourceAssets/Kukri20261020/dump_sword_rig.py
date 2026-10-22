"""Read-only: dump the sword arms rig, reference pose and sword clips used as the kukri anchor."""
import json
from pathlib import Path
import unreal as u
P = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020")
HIER = json.loads(Path(r"D:\FPS3D\FPSGAME\SourceAssets\BareSkinV9Rollout_20261017\Work\mesh_hierarchy.json").read_text())
MESH = "/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms"
h = HIER[MESH]; names = h['names']; parents = h['parents']
mesh = u.load_asset(MESH)
out = dict(mesh=MESH, names=names, parents=parents)
skel = mesh.get_editor_property('skeleton')
out['skeleton'] = skel.get_path_name() if skel else None
out['materials'] = [str(m.get_editor_property('material_slot_name')) + '|' + (m.get_editor_property('material_interface').get_path_name() if m.get_editor_property('material_interface') else 'None') for m in mesh.get_editor_property('materials')]
def pack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return [p.x, p.y, p.z, q.w, q.x, q.y, q.z, s.x, s.y, s.z]
ref = u.AnimPoseExtensions.get_reference_pose(skel)
out['ref_local'] = {n: pack(u.AnimPoseExtensions.get_ref_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names}
out['ref_world'] = {n: pack(u.AnimPoseExtensions.get_ref_bone_pose(ref, n, u.AnimPoseSpaces.WORLD)) for n in names}
clips = {}
base = "/Game/Weapons/AzureRunesword20260913/"
for name, path in [("Idle", base+"A_RuneSword_Idle"), ("Walk", base+"A_RuneSword_Walk"), ("Equip", base+"A_RuneSword_Equip"),
                   ("Slash1", base+"A_RuneSword_Slash1"), ("Slash2", base+"A_RuneSword_Slash2"), ("Thrust", base+"A_RuneSword_Thrust"),
                   ("PommelStrike", base+"A_RuneSword_PommelStrike"), ("SprintLoop", base+"TacticalSprint20260921/A_RuneSword_SprintLoop"),
                   ("SprintEnter", base+"TacticalSprint20260921/A_RuneSword_SprintEnter")]:
    seq = u.load_asset(path)
    if not seq:
        clips[name] = None; continue
    dmi = seq.get_editor_property('data_model_interface')
    keys = dmi.get_number_of_keys(); fr = dmi.get_frame_rate()
    rate = fr.numerator / fr.denominator
    frames = []
    for k in range(keys):
        poses = u.AnimationLibrary.get_bone_poses_for_frame(seq, names, k, False, mesh)
        frames.append([pack(t) for t in poses])
    sk = seq.get_editor_property('skeleton')
    clips[name] = dict(path=path, keys=keys, rate=rate, length=seq.get_play_length(), skeleton=sk.get_path_name() if sk else None, frames=frames)
    u.log("KUKRI_DUMP clip %s keys=%d rate=%s len=%.3f" % (name, keys, rate, seq.get_play_length()))
out['clips'] = clips
(P/'Work'/'ue_sword_dump.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
u.log("KUKRI_DUMP_DONE skeleton=%s" % out['skeleton'])
