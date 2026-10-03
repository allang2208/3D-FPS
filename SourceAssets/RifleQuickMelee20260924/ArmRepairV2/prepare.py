"""Authoring inputs for skin-continuity repair and the current SVD rear grip."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;P=O.parent;S=P.parent
sources=json.loads((P/'sources.json').read_text())
report={}
for weapon in ['SVD','PKM']:
 d=sources[weapon+'/base']
 bpy.ops.wm.open_mainfile(filepath=str(P/f'{weapon}_base_QuickMelee.blend'),use_scripts=False)
 r=bpy.data.objects[d['rig']];a=bpy.data.actions[f'{weapon}_base_QuickMelee20260924'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(40);bpy.context.view_layer.update()
 report[weapon]={'modifiers':[],'relative_rolls':{}}
 for ob in bpy.context.scene.objects:
  for mod in ob.modifiers:
   if mod.type=='ARMATURE' and mod.object==r and 'Arms' in ob.name:
    report[weapon]['modifiers'].append({'mesh':ob.name,'preserve_volume':mod.use_deform_preserve_volume,'vertices':len(ob.data.vertices)})
 for side in 'rl':
  for part in ['upperarm','lowerarm']:
   main=part+'_'+side;D=r.pose.bones[main].matrix@r.data.bones[main].matrix_local.inverted()
   for suffix in ['01','02']:
    name=part+'_twist_'+suffix+'_'+side
    q=(D@r.data.bones[name].matrix_local).to_quaternion().rotation_difference(r.pose.bones[name].matrix.to_quaternion())
    report[weapon]['relative_rolls'][name]=q.angle*180/3.14159265
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDStockAdapter20260923/SVD_StockModular_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
arms=bpy.data.objects['SK_Manny_Arms_Export'];r.data.pose_position='REST';bpy.context.view_layer.update()
names=[b.name for b in r.data.bones if b.name=='hand_r' or (b.name.endswith('_r') and b.name.startswith(('thumb','index','middle','ring','pinky')))]
use=[v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if arms.vertex_groups[g.group].name in names)>.98];look={v:i for i,v in enumerate(use)}
X=r.matrix_world.inverted()@arms.matrix_world
skin={'names':names,'vertices':[list(X@arms.data.vertices[i].co) for i in use],
 'weights':[{arms.vertex_groups[g.group].name:g.weight for g in arms.data.vertices[i].groups if arms.vertex_groups[g.group].name in names} for i in use],
 'faces':[[look[i] for i in f.vertices] for f in arms.data.polygons if all(i in look for i in f.vertices)]}
target={}
for name in ['SM_SVD_RetainedGrip','SM_SVD_Body']:
 ob=bpy.data.objects[name];X=(r.matrix_world@rest['WPN_root']).inverted()@ob.matrix_world
 target[name]={'vertices':[list(X@v.co) for v in ob.data.vertices],'faces':[list(f.vertices) for f in ob.data.polygons]}
out={'rest':{n:list(map(list,m)) for n,m in rest.items()},'parents':parents,'skin':skin,'target':target,'idle':sources['SVD/base']['idle']}
(O/'grip_inputs.json').write_text(json.dumps(out));(O/'skin_diagnosis.json').write_text(json.dumps(report,indent=2))
print('ARM_REPAIR_INPUTS',json.dumps(report),flush=True)
print('SVD_REAR_GRIP_BOUNDS',{k:{'min':[min(v[i] for v in d['vertices']) for i in range(3)],'max':[max(v[i] for v in d['vertices']) for i in range(3)]} for k,d in target.items()},flush=True)
