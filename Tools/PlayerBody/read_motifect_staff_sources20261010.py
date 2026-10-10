"""Read actual local Motifect source takes before selecting arm motion.

Authoring input extraction only; does not change any Unreal assets or settings.
"""
import bpy
import json
from pathlib import Path

source = Path('D:/FPS3D/VaultCache/FabLibrary/Motifect_Fantasy___Magic_Motion_Pack-b775c780/fbx/motifect_fantasy_and_mag_extracted')
out = Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffMotifect20261010')
out.mkdir(parents=True, exist_ok=True)
selection = ['time_stop_pose', 'power_charge_buildup', 'cast_lightning_bolt',
             'cast_fireball', 'enchant_weapon', 'cast_shield_barrier']
results = {}
for name in selection:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source/'Animations'/f'{name}.fbx'), use_anim=True)
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    start, end = rig.animation_data.action.frame_range
    names = [b.name for b in rig.data.bones]
    parents = [names.index(b.parent.name) if b.parent else -1 for b in rig.data.bones]
    def pack(m):
        p,q,s=m.decompose()
        return [*p,q.x,q.y,q.z,q.w,*s]
    reference = [pack(rig.matrix_world@b.matrix_local) for b in rig.data.bones]
    frames = []
    for frame in range(round(start),round(end)+1):
        bpy.context.scene.frame_set(frame)
        frames.append([pack(rig.matrix_world@rig.pose.bones[n].matrix) for n in names])
    results[name] = dict(source=str(source/'Animations'/f'{name}.fbx'),
        fps=bpy.context.scene.render.fps, frame_range=[start,end],
        names=names, parents=parents, reference_world=reference, frames_world=frames)
    print('MOTIFECT_SOURCE', name, 'frames',len(frames),'fps',bpy.context.scene.render.fps,'bones',','.join(names),flush=True)
(out/'source-poses.json').write_text(json.dumps(results,separators=(',',':')),encoding='utf-8')
(out/'source-readme.txt').write_text((source/'Documentation/README.txt').read_text(),encoding='utf-8')
print('MOTIFECT_SOURCE_READ_COMPLETE',flush=True)
