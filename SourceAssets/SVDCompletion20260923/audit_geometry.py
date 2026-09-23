import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDDragunov20260922/Authored/SK_SVD_Viewmodel.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
report={'rig':r.name,'matrix':[list(x) for x in r.matrix_world],'bones':{b.name:{'parent':b.parent.name if b.parent else None,'rest':[list(x) for x in b.matrix_local]} for b in r.data.bones},'parts':{}}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 vs=[r.matrix_world.inverted()@o.matrix_world@v.co for v in o.data.vertices]
 report['parts'][o.name]={'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)],'materials':[m.name for m in o.data.materials],'weights':list({g.name for g in o.vertex_groups}),'verts':len(vs)}
with bpy.data.libraries.load(str(S/'AKMSoviet20260911/AKM_Soviet_Editable.blend'),link=False) as (a,b):
 b.actions=[x for x in a.actions if x in ['AKM_Native_idle','AKM_Native_aim','AKM_EquipCharge','AKM_Native_reload_empty']]
report['actions']={a.name:list(a.frame_range) for a in bpy.data.actions}
r.animation_data_create();a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
p={b.name:b.matrix.copy() for b in r.pose.bones};root=p['WPN_root'];inv=root.inverted();report['idle_root']=[list(x) for x in root];report['idle_bones']={n:list((inv@m).translation) for n,m in p.items() if n.startswith(('WPN_','hand_','index_','middle_'))}
dg=bpy.context.evaluated_depsgraph_get();report['idle_parts']={}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 e=o.evaluated_get(dg);vs=[inv@r.matrix_world.inverted()@e.matrix_world@v.co for v in e.data.vertices]
 report['idle_parts'][o.name]={'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)]}
(O/'initial_geometry.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['rig','actions','idle_bones','idle_parts']},indent=2))
