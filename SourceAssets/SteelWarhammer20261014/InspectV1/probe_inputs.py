"""Read the actual hammer idle grip, shaft centreline and head envelope for the inspect."""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
W=idle['WPN_root'];inv=rest['WPN_root'].inverted()
hammer=bpy.data.objects['SM_SteelWarhammer']
local=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
zs=[p.z for p in local]
slices=[]
for k in range(-30,131):
    z0=k*.01;band=[p for p in local if z0<=p.z<z0+.01]
    if len(band)<8:continue
    c=sum(band,Vector())/len(band);c.z=0
    r=[math.hypot(p.x-c.x,p.y-c.y) for p in band]
    slices.append({'z':round(z0,3),'n':len(band),'cx':round(c.x,5),'cy':round(c.y,5),'rmax':round(max(r),4),'rmean':round(sum(r)/len(r),4),
        'xr':[round(min(p.x for p in band),4),round(max(p.x for p in band),4)],'yr':[round(min(p.y for p in band),4),round(max(p.y for p in band),4)]})
grips={s:W.inverted()@idle['hand_'+s] for s in ('l','r')}
objects=[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'verts':len(o.data.vertices) if o.type=='MESH' else 0,
    'modifiers':[m.type+':'+(getattr(m,'object',None).name if getattr(m,'object',None) else '') for m in getattr(o,'modifiers',[])]} for o in scene.objects]
report={'source':str(SOURCE),'rig_world':[list(r) for r in rig.matrix_world],'hammer_world':[list(r) for r in hammer.matrix_world],
 'hammer_parent':hammer.parent.name if hammer.parent else None,'hammer_parent_bone':hammer.parent_bone,
 'objects':objects,'bones':[[n,parents[n]] for n in rest],
 'idle':{n:{'t':list(idle[n].translation),'q':list(idle[n].to_quaternion())} for n in ('root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r')},
 'wpn_axis_rig':list(W.to_quaternion()@Vector((0,0,1))),'wpn_x_rig':list(W.to_quaternion()@Vector((1,0,0))),'wpn_y_rig':list(W.to_quaternion()@Vector((0,1,0))),
 'grip_local':{s:{'t':list(g.translation),'q':list(g.to_quaternion())} for s,g in grips.items()},
 'hammer_z_range':[min(zs),max(zs)],'slices':slices,
 'actions':sorted(a.name for a in bpy.data.actions),'fps':scene.render.fps}
(P/'probe.json').write_text(json.dumps(report,indent=1),encoding='utf-8')
print('WARHAMMER_INSPECT_PROBE_DONE')
