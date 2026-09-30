"""Read the two saved authoring layers; no UE/game session is started."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path('D:/FPS3D/FPSGAME')
O = Path(__file__).parent
rows = {}
for family in ('base', 'angled', 'canted', 'prism', 'vertical'):
    for clip in ('reload', 'reload_empty'):
        src = P/'SourceAssets/SVDReloadLeftArm20260925/Blends'/f'SVD_{family}_{clip}_LeftArm.blend'
        bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
        rig = bpy.data.objects['SK_M4_Infima']
        name = 'A_SVD_'+('' if family == 'base' else family+'_')+clip
        rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        u, l, h = (rest[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
        plane = (l-u).cross(h-l).normalized()
        result = {}
        for action in (name, 'REFERENCE_'+name):
            act = bpy.data.actions[action]
            rig.animation_data.action = act
            rig.animation_data.action_slot = act.slots[0]
            samples = []
            for f in range(240, 381, 4):
                bpy.context.scene.frame_set(f)
                bpy.context.view_layer.update()
                pose = {n: rig.pose.bones[n].matrix.copy() for n in rest}
                u, l, h = (pose[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
                ud, ld = (l-u).normalized(), (h-l).normalized()
                pl = ud.cross(ld).normalized()
                old = (pose['upperarm_l'].to_quaternion() @ rest['upperarm_l'].to_quaternion().inverted()) @ plane
                roll = math.degrees(math.atan2(ud.dot(old.cross(pl)), old.dot(pl)))
                samples.append(dict(frame=f, roll=roll, flex=math.degrees(ud.angle(ld))))
            result[action] = samples
        rows[family+'/'+clip] = result
        print('SOURCE_PLANE', family, clip, [(k, max(v,key=lambda r:abs(r['roll'])), min(v,key=lambda r:r['flex'])) for k,v in result.items()],flush=True)
(O/'source-plane.json').write_text(json.dumps(rows,indent=2))
