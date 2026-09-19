import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx'))
ob=bpy.data.objects['AKM_FactoryMagazine_Preview']
arm=next(x for x in bpy.context.scene.objects if x.type=='ARMATURE');arm.data.pose_position='REST';bpy.context.view_layer.update()
report={'matrix':list(map(list,ob.matrix_world)),'slots':{},'nearby':[]}
for i,m in enumerate(ob.data.materials):
 faces=[p for p in ob.data.polygons if p.material_index==i];vs={v for p in faces for v in p.vertices};pts=[ob.matrix_world@ob.data.vertices[v].co for v in vs]
 report['slots'][str(i)]={'name':m.name,'faces':len(faces),'bounds':[[min(p[j] for p in pts),max(p[j] for p in pts)] for j in range(3)] if pts else [],'textures':[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]}
for obj in bpy.context.scene.objects:
 if obj.type=='MESH' and any(s in obj.name.lower() for s in ['mag','bullet','round','ammo']):report['nearby'].append(obj.name)
(O/'source_geometry.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
