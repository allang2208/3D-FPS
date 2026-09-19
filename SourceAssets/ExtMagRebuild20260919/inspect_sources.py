import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent
SA=ROOT.parent
jobs={'M4':('M4HK416Replica20260910/SK_M4_FoldingSights_HK416.fbx','magazine'), 'AKM':('PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx','magazine'), 'QBZ':('PhantomRearGripIntegration20260913/QBZ191/SK_QBZ191_Manny.fbx','magazine')}
report={}
for gun,(path,match) in jobs.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(SA/path))
 report[gun]=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  indices=[i for i,m in enumerate(ob.data.materials) if m and match in m.name.lower()]
  if not indices:continue
  vids={v for p in ob.data.polygons if p.material_index in indices for v in p.vertices}
  pts=[ob.matrix_world@ob.data.vertices[i].co for i in vids]
  if not pts:continue
  report[gun].append({'object':ob.name,'slots':[m.name if m else '' for m in ob.data.materials], 'vertices':len(pts),'bounds':[[min(p[k] for p in pts) for k in range(3)],[max(p[k] for p in pts) for k in range(3)]], 'groups':[g.name for g in ob.vertex_groups], 'weights':sorted({(ob.vertex_groups[g.group].name,round(g.weight,3)) for i in vids for g in ob.data.vertices[i].groups})})
bpy.ops.wm.open_mainfile(filepath=str(SA/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima']; a=bpy.data.actions['M4_MAT_reload'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
report['M4_grip']={}
for f in [61,76,95,98]:
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
 inv=rig.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()
 rest=rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
 report['M4_grip'][f]={n:list(rig.matrix_world@rest@inv@rig.pose.bones[n].matrix.translation) for n in ['hand_l','thumb_03_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l']}
report['M4_scene']=[(o.name,o.type) for o in bpy.context.scene.objects]
(ROOT/'source_inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
